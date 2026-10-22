"""Unit tests for standalone Bedrock 3D biome storage decoder (Data3D).

Tests strict decoding, bit packing/padding across all supported bit widths,
asymmetric coordinate indexing, negative Y handling, unknown/absent section handling,
and comprehensive rejection of invalid or malformed data.
"""

from __future__ import annotations

import math
from pathlib import Path
import struct
import sys
import unittest

_src = str(Path(__file__).resolve().parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from seed_search.realm.bedrock_biome_storage import (
    BiomeSection,
    Data3D,
    decode_data3d,
)


def make_heightmap(default_val: int = 64) -> bytes:
    """Helper to generate a valid 512-byte heightmap header."""
    return struct.pack("<256H", *([default_val] * 256))


def encode_uniform_section(biome_id: int) -> bytes:
    """Helper to encode a uniform section (0x01 header + uint32 ID)."""
    return b"\x01" + struct.pack("<I", biome_id)


def encode_unknown_section() -> bytes:
    """Helper to encode an unknown section (0xFF header)."""
    return b"\xff"


def encode_packed_section(
    bits: int,
    indices: list[int],
    palette: list[int],
    *,
    pad_bits: int = 0,
) -> bytes:
    """Helper to encode a packed section with explicit bit width and optional high padding bits."""
    if len(indices) != 4096:
        raise ValueError(f"indices must have length 4096, got {len(indices)}")
    header = ((bits << 1) | 1).to_bytes(1, "little")
    values_per_word = 32 // bits
    words_count = math.ceil(4096 / values_per_word)

    words = []
    idx_cursor = 0
    mask = (1 << bits) - 1

    for _ in range(words_count):
        word_val = 0
        for slot in range(values_per_word):
            if idx_cursor < 4096:
                val = indices[idx_cursor] & mask
                word_val |= val << (slot * bits)
                idx_cursor += 1
            else:
                # High unused slot padding in the final word
                if pad_bits:
                    word_val |= (pad_bits & mask) << (slot * bits)
        # High-word unused bit padding
        used_bits = values_per_word * bits
        if used_bits < 32 and pad_bits:
            pad_mask = ((1 << (32 - used_bits)) - 1) << used_bits
            word_val |= (pad_bits << used_bits) & pad_mask
        words.append(word_val & 0xFFFFFFFF)

    words_bytes = struct.pack(f"<{len(words)}I", *words)
    pal_len_bytes = struct.pack("<I", len(palette))
    pal_entries_bytes = struct.pack(f"<{len(palette)}I", *palette)

    return header + words_bytes + pal_len_bytes + pal_entries_bytes


class TestBedrockBiomeStorage(unittest.TestCase):
    """Test suite for bedrock_biome_storage pure decoder."""

    def test_uniform_section(self) -> None:
        """Test uniform sections with various uint32 biome IDs."""
        test_ids = [0, 1, 42, 183, 190, 0xFFFFFFFF]
        for b_id in test_ids:
            with self.subTest(biome_id=b_id):
                payload = make_heightmap(100) + encode_uniform_section(b_id)
                data3d = decode_data3d(payload, floor_section=-4)
                self.assertEqual(len(data3d.sections), 1)
                sec = data3d.sections[0]
                self.assertEqual(sec.section_y, -4)
                self.assertEqual(sec.kind, "uniform")
                self.assertEqual(sec.palette, (b_id,))
                self.assertEqual(sec.indices, ())
                # Uniform section should return b_id across all coords
                self.assertEqual(data3d.sample(0, -64, 0), b_id)
                self.assertEqual(data3d.sample(15, -49, 15), b_id)
                self.assertEqual(data3d.sample(7, -55, 7), b_id)

    def test_unknown_section(self) -> None:
        """Test 0xFF unknown single-byte section without inherited guess."""
        payload = (
            make_heightmap()
            + encode_uniform_section(10)
            + encode_unknown_section()
            + encode_uniform_section(20)
        )
        data3d = decode_data3d(payload, floor_section=-4)
        self.assertEqual(len(data3d.sections), 3)

        # Section -4: uniform 10
        self.assertEqual(data3d.sections[0].kind, "uniform")
        self.assertEqual(data3d.sample(0, -64, 0), 10)

        # Section -3: unknown
        sec_unknown = data3d.sections[1]
        self.assertEqual(sec_unknown.section_y, -3)
        self.assertEqual(sec_unknown.kind, "unknown")
        self.assertEqual(sec_unknown.palette, ())
        self.assertEqual(sec_unknown.indices, ())
        # Sampling unknown section MUST return None, never fallback to adjacent 10 or 20
        self.assertIsNone(data3d.sample(0, -48, 0))
        self.assertIsNone(data3d.sample(8, -40, 8))
        self.assertIsNone(data3d.sample(15, -33, 15))

        # Section -2: uniform 20
        self.assertEqual(data3d.sections[2].kind, "uniform")
        self.assertEqual(data3d.sample(0, -32, 0), 20)

    def test_missing_absent_section(self) -> None:
        """Test that querying outside decoded sections returns None without fallback."""
        payload = make_heightmap() + encode_uniform_section(50)
        data3d = decode_data3d(payload, floor_section=-4)
        self.assertEqual(len(data3d.sections), 1)

        # In bounds section -4 (-64..-49)
        self.assertEqual(data3d.sample(0, -64, 0), 50)
        self.assertEqual(data3d.sample(15, -49, 15), 50)

        # Below floor_section: section -5 (-80..-65) -> absent -> None
        self.assertIsNone(data3d.sample(0, -65, 0))
        self.assertIsNone(data3d.sample(0, -100, 0))

        # Above populated sections: section -3 (-48..-33) -> absent -> None
        self.assertIsNone(data3d.sample(0, -48, 0))
        self.assertIsNone(data3d.sample(0, 0, 0))
        self.assertIsNone(data3d.sample(0, 319, 0))

    def test_negative_y_floordiv(self) -> None:
        """Verify negative Y coordinates and section_y floor division behavior."""
        # 4 sections: -4, -3, -2, -1
        payload = (
            make_heightmap()
            + encode_uniform_section(100)  # -4: Y=-64..-49
            + encode_uniform_section(101)  # -3: Y=-48..-33
            + encode_uniform_section(102)  # -2: Y=-32..-17
            + encode_uniform_section(103)  # -1: Y=-16..-1
        )
        data3d = decode_data3d(payload, floor_section=-4)
        self.assertEqual(len(data3d.sections), 4)

        # Boundaries of section -4
        self.assertEqual(data3d.sample(0, -64, 0), 100)  # -64 // 16 == -4, % 16 == 0
        self.assertEqual(data3d.sample(0, -49, 0), 100)  # -49 // 16 == -4, % 16 == 15

        # Boundaries of section -3
        self.assertEqual(data3d.sample(0, -48, 0), 101)  # -48 // 16 == -3, % 16 == 0
        self.assertEqual(data3d.sample(0, -33, 0), 101)  # -33 // 16 == -3, % 16 == 15

        # Boundaries of section -2
        self.assertEqual(data3d.sample(0, -32, 0), 102)  # -32 // 16 == -2, % 16 == 0
        self.assertEqual(data3d.sample(0, -17, 0), 102)  # -17 // 16 == -2, % 16 == 15

        # Boundaries of section -1
        self.assertEqual(data3d.sample(0, -16, 0), 103)  # -16 // 16 == -1, % 16 == 0
        self.assertEqual(data3d.sample(0, -1, 0), 103)   # -1 // 16 == -1, % 16 == 15

        # Y=0 is section 0 -> absent -> None
        self.assertIsNone(data3d.sample(0, 0, 0))

    def test_all_supported_bit_widths_and_padding(self) -> None:
        """Test packed sections across all supported bit widths: 1, 2, 3, 4, 5, 6, 8, 16.

        Verifies that non-zero high padding bits in words are skipped and do not corrupt data.
        """
        widths = (1, 2, 3, 4, 5, 6, 8, 16)
        for bits in widths:
            with self.subTest(bits=bits):
                pal_len = min(1 << bits, 16 if bits >= 4 else 1 << bits)
                palette = [1000 + i for i in range(pal_len)]
                # Generate deterministic pattern for 4096 blocks
                indices = [(i * 3 + 7) % pal_len for i in range(4096)]

                # Pack with all high padding bits set to 1 (0xFFFFFFFF)
                section_bytes = encode_packed_section(
                    bits=bits,
                    indices=indices,
                    palette=palette,
                    pad_bits=0xFFFFFFFF,
                )
                payload = make_heightmap() + section_bytes
                data3d = decode_data3d(payload, floor_section=0)
                sec = data3d.sections[0]

                self.assertEqual(sec.section_y, 0)
                self.assertEqual(sec.kind, "packed")
                self.assertEqual(sec.palette, tuple(palette))
                self.assertEqual(sec.indices, tuple(indices))

                # Sample spot checks
                for idx in [0, 1, 15, 255, 256, 1000, 4095]:
                    x = idx // 256
                    rem = idx % 256
                    z = rem // 16
                    y = rem % 16
                    expected_id = palette[indices[idx]]
                    self.assertEqual(data3d.sample(x, y, z), expected_id)

    def test_asymmetric_xyz_known_word_fixture(self) -> None:
        """Test asymmetric XYZ coordinates with an independently indexed known-word fixture.

        Confirms index = x*256 + z*16 + y (YZX order: y fastest, z middle, x slowest).
        """
        # We construct a 4-bit packed section (palette length 16)
        # Word 0 contains indices 0..7 (all x=0, z=0, y=0..7)
        # Values 0..7: [1, 2, 3, 4, 5, 6, 7, 8]
        # In little endian uint32, word 0 is exactly 0x87654321
        indices = [0] * 4096

        # Set specific asymmetric probe points
        # Target coords: (x, z, y) -> index = x*256 + z*16 + y
        # Point A: x=1, z=2, y=3 -> index = 1*256 + 2*16 + 3 = 291
        # Point B: x=3, z=2, y=1 -> index = 3*256 + 2*16 + 1 = 801
        # Point C: x=2, z=1, y=3 -> index = 2*256 + 1*16 + 3 = 531
        # Point D: x=1, z=3, y=2 -> index = 1*256 + 3*16 + 2 = 306
        indices[291] = 5
        indices[801] = 7
        indices[531] = 9
        indices[306] = 11

        palette = [200 + i for i in range(16)]

        section_bytes = encode_packed_section(bits=4, indices=indices, palette=palette)
        payload = make_heightmap() + section_bytes
        data3d = decode_data3d(payload, floor_section=0)

        # Coordinate A: x=1, world y=3, z=2 -> index 291 -> palette[5] == 205
        self.assertEqual(data3d.sample(1, 3, 2), 205)
        # Coordinate B: x=3, world y=1, z=2 -> index 801 -> palette[7] == 207
        self.assertEqual(data3d.sample(3, 1, 2), 207)
        # Coordinate C: x=2, world y=3, z=1 -> index 531 -> palette[9] == 209
        self.assertEqual(data3d.sample(2, 3, 1), 209)
        # Coordinate D: x=1, world y=2, z=3 -> index 306 -> palette[11] == 211
        self.assertEqual(data3d.sample(1, 2, 3), 211)

        # Any permutation mismatch fails
        self.assertNotEqual(data3d.sample(1, 3, 2), data3d.sample(3, 1, 2))
        self.assertNotEqual(data3d.sample(1, 3, 2), data3d.sample(1, 2, 3))

    def test_known_word_0_fixture(self) -> None:
        """Directly verify low-level word bit-packing with known 32-bit constant."""
        # Word 0 = 0x87654321 for 4-bit values: [1, 2, 3, 4, 5, 6, 7, 8]
        palette = [1000 + i for i in range(16)]
        indices = [1, 2, 3, 4, 5, 6, 7, 8] + [0] * 4088
        section_bytes = encode_packed_section(bits=4, indices=indices, palette=palette)

        # Verify that word 0 in the serialized stream starts with 0x87654321
        header_len = 1
        word0_bytes = section_bytes[header_len : header_len + 4]
        word0_val = struct.unpack("<I", word0_bytes)[0]
        self.assertEqual(word0_val, 0x87654321)

        payload = make_heightmap() + section_bytes
        data3d = decode_data3d(payload, floor_section=0)

        # Indices 0..7 correspond to x=0, z=0, y=0..7
        for y_coord in range(8):
            expected_idx = y_coord + 1
            self.assertEqual(data3d.sample(0, y_coord, 0), palette[expected_idx])

    def test_full_resolution_distinct_blocks(self) -> None:
        """Verify full block-level resolution: neighboring blocks independently addressable."""
        # Every adjacent block in a 4x4x4 cube has a distinct ID
        palette = [i for i in range(16)]
        indices = [0] * 4096
        for x in range(4):
            for z in range(4):
                for y in range(4):
                    idx = x * 256 + z * 16 + y
                    indices[idx] = (x * 4 + z * 2 + y) % 16

        section_bytes = encode_packed_section(bits=4, indices=indices, palette=palette)
        payload = make_heightmap() + section_bytes
        data3d = decode_data3d(payload, floor_section=0)

        # Check neighbor distinction
        val_000 = data3d.sample(0, 0, 0)
        val_100 = data3d.sample(1, 0, 0)
        val_010 = data3d.sample(0, 1, 0)
        val_001 = data3d.sample(0, 0, 1)

        self.assertNotEqual(val_000, val_100)
        self.assertNotEqual(val_000, val_010)
        self.assertNotEqual(val_000, val_001)

    def test_multi_section_stream_up_to_max_sections(self) -> None:
        """Test stream parsing up to 24 and 25 sections."""
        # 24 sections (-4 to 19)
        sec_bytes = [encode_uniform_section(i) for i in range(24)]
        payload_24 = make_heightmap() + b"".join(sec_bytes)
        data_24 = decode_data3d(payload_24, floor_section=-4, max_sections=25)
        self.assertEqual(len(data_24.sections), 24)
        self.assertEqual(data_24.sections[0].section_y, -4)
        self.assertEqual(data_24.sections[-1].section_y, 19)
        self.assertEqual(data_24.sample(0, -64, 0), 0)
        self.assertEqual(data_24.sample(0, 319, 0), 23)

        # 25 sections (-4 to 20)
        sec_bytes_25 = [encode_uniform_section(i) for i in range(25)]
        payload_25 = make_heightmap() + b"".join(sec_bytes_25)
        data_25 = decode_data3d(payload_25, floor_section=-4, max_sections=25)
        self.assertEqual(len(data_25.sections), 25)
        self.assertEqual(data_25.sections[-1].section_y, 20)

    def test_heightmap_header_parsing(self) -> None:
        """Test raw 512-byte heightmap parsing without assuming heightdatum/terrain."""
        raw_heights = [i * 200 for i in range(256)]
        hm_bytes = struct.pack("<256H", *raw_heights)
        payload = hm_bytes + encode_uniform_section(1)
        data3d = decode_data3d(payload)
        self.assertEqual(len(data3d.heightmap), 256)
        self.assertEqual(data3d.heightmap, tuple(raw_heights))

    def test_invalid_data_rejections(self) -> None:
        """Test rejection of empty, truncated, invalid header, out-of-bounds indices, and oversized data."""
        valid_sec = encode_uniform_section(1)

        # Empty data
        with self.assertRaises(ValueError):
            decode_data3d(b"")

        # Truncated header (< 512 bytes)
        with self.assertRaises(ValueError):
            decode_data3d(b"\x00" * 511)

        # Heightmap only, 0 sections
        with self.assertRaises(ValueError):
            decode_data3d(make_heightmap())

        # Exceeds 1 MiB limit
        with self.assertRaises(ValueError):
            decode_data3d(b"\x00" * (1024 * 1024 + 1))

        # Invalid section header: LSB != 1
        with self.assertRaises(ValueError):
            decode_data3d(make_heightmap() + b"\x00\x00\x00\x00\x00")
        with self.assertRaises(ValueError):
            decode_data3d(make_heightmap() + b"\x02\x00\x00\x00\x00")
        with self.assertRaises(ValueError):
            decode_data3d(make_heightmap() + b"\xfe")

        # Unsupported section header bits (bits=7 -> 0x0F, bits=9 -> 0x13)
        with self.assertRaises(ValueError):
            decode_data3d(make_heightmap() + b"\x0f" + b"\x00" * 100)
        with self.assertRaises(ValueError):
            decode_data3d(make_heightmap() + b"\x13" + b"\x00" * 100)

        # Truncated uniform section (< 4 bytes for uint32 ID)
        with self.assertRaises(ValueError):
            decode_data3d(make_heightmap() + b"\x01\x00\x00")

        # Truncated packed section (header 0x03 is 1-bit packed, needs 128 words = 512 bytes)
        with self.assertRaises(ValueError):
            decode_data3d(make_heightmap() + b"\x03" + b"\x00" * 100)

        # Truncated palette length
        with self.assertRaises(ValueError):
            # 128 words for 1-bit, then only 2 bytes of palette len
            decode_data3d(make_heightmap() + b"\x03" + b"\x00" * 512 + b"\x01\x00")

        # Invalid palette length (0)
        with self.assertRaises(ValueError):
            decode_data3d(make_heightmap() + b"\x03" + b"\x00" * 512 + struct.pack("<I", 0))

        # Invalid palette length (> 2**bits for bits=1: max is 2)
        with self.assertRaises(ValueError):
            decode_data3d(make_heightmap() + b"\x03" + b"\x00" * 512 + struct.pack("<I", 3))

        # Truncated palette entries
        with self.assertRaises(ValueError):
            decode_data3d(make_heightmap() + b"\x03" + b"\x00" * 512 + struct.pack("<I", 2) + b"\x01\x00\x00\x00")

        # Palette index >= palette_len
        # For bits=1, palette_len=1 (only index 0 valid), but index has 1
        bad_idx_sec = encode_packed_section(bits=1, indices=[1] + [0] * 4095, palette=[99])
        with self.assertRaises(ValueError):
            decode_data3d(make_heightmap() + bad_idx_sec)

        # More sections than max_sections
        payload_3_sections = make_heightmap() + (valid_sec * 3)
        with self.assertRaises(ValueError):
            decode_data3d(payload_3_sections, max_sections=2)

    def test_type_and_argument_validation(self) -> None:
        """Test strict rejection of non-int/bool for floor_section, max_sections, coords, data."""
        valid_payload = make_heightmap() + encode_uniform_section(1)

        # Invalid data type
        with self.assertRaises(TypeError):
            decode_data3d(None)  # type: ignore
        with self.assertRaises(TypeError):
            decode_data3d("not bytes")  # type: ignore
        with self.assertRaises(TypeError):
            decode_data3d(True)  # type: ignore

        # Invalid floor_section (bool or non-int)
        with self.assertRaises(TypeError):
            decode_data3d(valid_payload, floor_section=True)  # type: ignore
        with self.assertRaises(TypeError):
            decode_data3d(valid_payload, floor_section="0")  # type: ignore
        with self.assertRaises(TypeError):
            decode_data3d(valid_payload, floor_section=1.5)  # type: ignore

        # Invalid max_sections (bool, non-int, out of bounds 1..25)
        with self.assertRaises(TypeError):
            decode_data3d(valid_payload, max_sections=False)  # type: ignore
        with self.assertRaises(TypeError):
            decode_data3d(valid_payload, max_sections=2.5)  # type: ignore
        with self.assertRaises(ValueError):
            decode_data3d(valid_payload, max_sections=0)
        with self.assertRaises(ValueError):
            decode_data3d(valid_payload, max_sections=26)

        # Coordinate validations in sample()
        data3d = decode_data3d(valid_payload)

        # Bool coords rejected
        with self.assertRaises(TypeError):
            data3d.sample(True, 0, 0)
        with self.assertRaises(TypeError):
            data3d.sample(0, False, 0)
        with self.assertRaises(TypeError):
            data3d.sample(0, 0, True)

        # Non-int coords rejected
        with self.assertRaises(TypeError):
            data3d.sample("0", 0, 0)  # type: ignore
        with self.assertRaises(TypeError):
            data3d.sample(0, 1.0, 0)  # type: ignore
        with self.assertRaises(TypeError):
            data3d.sample(0, 0, None)  # type: ignore

        # Out-of-bounds x/z (local block coords must be 0..15)
        with self.assertRaises(ValueError):
            data3d.sample(-1, 0, 0)
        with self.assertRaises(ValueError):
            data3d.sample(16, 0, 0)
        with self.assertRaises(ValueError):
            data3d.sample(0, 0, -1)
        with self.assertRaises(ValueError):
            data3d.sample(0, 0, 16)

    def test_frozen_immutability(self) -> None:
        """Test that Data3D and BiomeSection are immutable frozen dataclasses."""
        payload = make_heightmap() + encode_uniform_section(42)
        data3d = decode_data3d(payload)
        sec = data3d.sections[0]

        with self.assertRaises(AttributeError):
            data3d.heightmap = ()  # type: ignore
        with self.assertRaises(AttributeError):
            sec.section_y = 10  # type: ignore
        with self.assertRaises(AttributeError):
            sec.kind = "packed"  # type: ignore


if __name__ == "__main__":
    unittest.main()
