"""Experimental stored-data contract only.

Standalone strict decoder for Minecraft Bedrock 3D biome storage (Data3D).
Provides raw heightmap and decoded biome sections without numeric ID to
name mapping or native engine/world generation claims.
"""

from __future__ import annotations

from dataclasses import dataclass
import struct
from typing import Sequence

__all__ = [
    "BiomeSection",
    "Data3D",
    "decode_data3d",
    "resolve_repeated_sections",
    "sample_bedrock_runtime",
]

_SUPPORTED_BITS = (1, 2, 3, 4, 5, 6, 8, 16)
_MAX_BUFFER_SIZE = 1024 * 1024  # 1 MiB
_HEIGHTMAP_BYTES = 512
_HEIGHTMAP_ENTRIES = 256
_SUBCHUNK_BLOCK_COUNT = 4096


@dataclass(frozen=True)
class BiomeSection:
    """A decoded 16x16x16 subchunk biome section."""

    section_y: int
    kind: str
    palette: tuple[int, ...]
    indices: tuple[int, ...]

    def __post_init__(self) -> None:
        if isinstance(self.section_y, bool) or not isinstance(self.section_y, int):
            raise TypeError(f"section_y must be an integer, got {type(self.section_y).__name__}")
        if self.kind not in ("uniform", "packed", "unknown"):
            raise ValueError(f"invalid section kind: {self.kind!r}")

        # Coerce/validate palette
        if not isinstance(self.palette, tuple):
            if isinstance(self.palette, (list, Sequence)):
                object.__setattr__(self, "palette", tuple(self.palette))
            else:
                raise TypeError("palette must be a tuple of ints")
        for p in self.palette:
            if isinstance(p, bool) or not isinstance(p, int):
                raise TypeError(f"palette entry must be an integer, got {type(p).__name__}")
            if not (0 <= p <= 0xFFFFFFFF):
                raise ValueError(f"palette entry out of uint32 range: {p}")

        # Coerce/validate indices
        if not isinstance(self.indices, tuple):
            if isinstance(self.indices, (list, Sequence)):
                object.__setattr__(self, "indices", tuple(self.indices))
            else:
                raise TypeError("indices must be a tuple of ints")

        if self.kind == "uniform":
            if len(self.palette) != 1:
                raise ValueError(f"uniform section must have exactly 1 palette entry, got {len(self.palette)}")
            if len(self.indices) != 0:
                raise ValueError(f"uniform section must have empty indices, got {len(self.indices)}")
        elif self.kind == "unknown":
            if len(self.palette) != 0:
                raise ValueError(f"unknown section must have empty palette, got {len(self.palette)}")
            if len(self.indices) != 0:
                raise ValueError(f"unknown section must have empty indices, got {len(self.indices)}")
        elif self.kind == "packed":
            if not (1 <= len(self.palette) <= _SUBCHUNK_BLOCK_COUNT):
                raise ValueError(
                    f"packed section palette length must be in 1..{_SUBCHUNK_BLOCK_COUNT}, got {len(self.palette)}"
                )
            if len(self.indices) != _SUBCHUNK_BLOCK_COUNT:
                raise ValueError(
                    f"packed section indices must have length {_SUBCHUNK_BLOCK_COUNT}, got {len(self.indices)}"
                )
            pal_len = len(self.palette)
            for idx in self.indices:
                if isinstance(idx, bool) or not isinstance(idx, int):
                    raise TypeError(f"index must be an integer, got {type(idx).__name__}")
                if idx < 0 or idx >= pal_len:
                    raise ValueError(f"index {idx} out of range for palette length {pal_len}")


@dataclass(frozen=True)
class Data3D:
    """Decoded 3D biome data with heightmap header and subchunk sections."""

    heightmap: tuple[int, ...]
    sections: tuple[BiomeSection, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.heightmap, tuple):
            if isinstance(self.heightmap, (list, Sequence)):
                object.__setattr__(self, "heightmap", tuple(self.heightmap))
            else:
                raise TypeError("heightmap must be a tuple of 256 uint16 ints")
        if len(self.heightmap) != _HEIGHTMAP_ENTRIES:
            raise ValueError(f"heightmap must have exactly {_HEIGHTMAP_ENTRIES} entries, got {len(self.heightmap)}")
        for h in self.heightmap:
            if isinstance(h, bool) or not isinstance(h, int):
                raise TypeError(f"heightmap entry must be an integer, got {type(h).__name__}")
            if not (0 <= h <= 0xFFFF):
                raise ValueError(f"heightmap entry out of uint16 range (0..65535): {h}")

        if not isinstance(self.sections, tuple):
            if isinstance(self.sections, (list, Sequence)):
                object.__setattr__(self, "sections", tuple(self.sections))
            else:
                raise TypeError("sections must be a tuple of BiomeSection instances")
        for s in self.sections:
            if not isinstance(s, BiomeSection):
                raise TypeError(f"sections entry must be BiomeSection, got {type(s).__name__}")

    def sample(self, x: int, y: int, z: int) -> int | None:
        """Sample biome ID at local block coords (x, z) in 0..15 and world block y.

        Returns None if the section is absent or marked unknown. Never falls back.
        """
        if isinstance(x, bool) or not isinstance(x, int):
            raise TypeError(f"x must be an integer, got {type(x).__name__}")
        if isinstance(y, bool) or not isinstance(y, int):
            raise TypeError(f"y must be an integer, got {type(y).__name__}")
        if isinstance(z, bool) or not isinstance(z, int):
            raise TypeError(f"z must be an integer, got {type(z).__name__}")

        if not (0 <= x <= 15):
            raise ValueError(f"x out of bounds (0..15): {x}")
        if not (0 <= z <= 15):
            raise ValueError(f"z out of bounds (0..15): {z}")

        target_sec_y = y // 16
        local_y = y % 16

        # Fast lookup in sections
        sec: BiomeSection | None = None
        if self.sections:
            first_y = self.sections[0].section_y
            offset = target_sec_y - first_y
            if 0 <= offset < len(self.sections) and self.sections[offset].section_y == target_sec_y:
                sec = self.sections[offset]
            else:
                for s in self.sections:
                    if s.section_y == target_sec_y:
                        sec = s
                        break

        if sec is None or sec.kind == "unknown":
            return None

        if sec.kind == "uniform":
            return sec.palette[0]

        if sec.kind == "packed":
            idx = x * 256 + z * 16 + local_y
            return sec.palette[sec.indices[idx]]

        return None


def decode_data3d(
    data: bytes,
    *,
    floor_section: int = -4,
    max_sections: int = 25,
) -> Data3D:
    """Decode raw Bedrock 3D biome storage data into Data3D.

    Args:
        data: Raw bytes of the 3D biome storage payload.
        floor_section: section_y coordinate of the first section (default -4 for 1.18+).
        max_sections: Maximum number of sections permitted (1..25, default 25).

    Returns:
        A frozen Data3D instance.
    """
    if isinstance(data, bool) or not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError(f"data must be bytes-like, got {type(data).__name__}")
    size = data.nbytes if isinstance(data, memoryview) else len(data)
    if size > _MAX_BUFFER_SIZE:
        raise ValueError(f"data buffer exceeds 1 MiB limit: {size} bytes")
    raw = bytes(data)

    if len(raw) == 0:
        raise ValueError("empty data buffer")
    if len(raw) > _MAX_BUFFER_SIZE:
        raise ValueError(f"data buffer exceeds 1 MiB limit: {len(raw)} bytes")
    if len(raw) < _HEIGHTMAP_BYTES:
        raise ValueError(f"truncated data: expected at least {_HEIGHTMAP_BYTES}-byte heightmap header, got {len(raw)} bytes")

    if isinstance(floor_section, bool) or not isinstance(floor_section, int):
        raise TypeError(f"floor_section must be an integer, got {type(floor_section).__name__}")
    if isinstance(max_sections, bool) or not isinstance(max_sections, int):
        raise TypeError(f"max_sections must be an integer, got {type(max_sections).__name__}")
    if not (1 <= max_sections <= 25):
        raise ValueError(f"max_sections must be in 1..25, got {max_sections}")

    if len(raw) == _HEIGHTMAP_BYTES:
        raise ValueError("no sections found in data buffer")

    heightmap = struct.unpack(f"<{_HEIGHTMAP_ENTRIES}H", raw[:_HEIGHTMAP_BYTES])
    offset = _HEIGHTMAP_BYTES
    sections: list[BiomeSection] = []
    section_idx = 0

    while offset < len(raw):
        if section_idx >= max_sections:
            raise ValueError(f"data contains more sections than max_sections ({max_sections})")

        header = raw[offset]
        offset += 1

        if (header & 1) != 1:
            raise ValueError(f"invalid section header 0x{header:02x}: LSB must be 1")

        sec_y = floor_section + section_idx

        if header == 0x01:
            # Uniform section: 0x01 uniform followed by uint32 single ID
            if offset + 4 > len(raw):
                raise ValueError(f"truncated uniform section at offset {offset}: expected 4-byte uint32 ID")
            single_id = struct.unpack_from("<I", raw, offset)[0]
            offset += 4
            sec = BiomeSection(
                section_y=sec_y,
                kind="uniform",
                palette=(single_id,),
                indices=(),
            )
            sections.append(sec)
            section_idx += 1
        elif header == 0xFF:
            # Unknown section: 0xff unknown singlebyte NO inherited guess
            sec = BiomeSection(
                section_y=sec_y,
                kind="unknown",
                palette=(),
                indices=(),
            )
            sections.append(sec)
            section_idx += 1
        else:
            bits = header >> 1
            if bits not in _SUPPORTED_BITS:
                raise ValueError(f"invalid or unsupported section header 0x{header:02x} (bits={bits})")

            values_per_word = 32 // bits
            words_count = (_SUBCHUNK_BLOCK_COUNT + values_per_word - 1) // values_per_word

            words_bytes = words_count * 4
            if offset + words_bytes > len(raw):
                raise ValueError(
                    f"truncated packed section indices at offset {offset}: "
                    f"expected {words_bytes} bytes for {words_count} words ({bits} bits/value)"
                )

            words = struct.unpack_from(f"<{words_count}I", raw, offset)
            offset += words_bytes

            mask = (1 << bits) - 1
            indices_list: list[int] = []
            for w in words:
                curr = w
                for _ in range(values_per_word):
                    indices_list.append(curr & mask)
                    curr >>= bits
                    if len(indices_list) == _SUBCHUNK_BLOCK_COUNT:
                        break
                if len(indices_list) == _SUBCHUNK_BLOCK_COUNT:
                    break

            if offset + 4 > len(raw):
                raise ValueError(f"truncated palette length at offset {offset}")
            palette_len = struct.unpack_from("<I", raw, offset)[0]
            offset += 4

            max_palette_len = min(1 << bits, _SUBCHUNK_BLOCK_COUNT)
            if palette_len < 1 or palette_len > max_palette_len:
                raise ValueError(
                    f"invalid palette length {palette_len}: must be 1..{max_palette_len} for {bits} bits"
                )

            palette_bytes = palette_len * 4
            if offset + palette_bytes > len(raw):
                raise ValueError(
                    f"truncated palette entries at offset {offset}: "
                    f"expected {palette_bytes} bytes for {palette_len} entries"
                )

            palette = struct.unpack_from(f"<{palette_len}I", raw, offset)
            offset += palette_bytes

            # Validate indices against palette length
            for idx in indices_list:
                if idx >= palette_len:
                    raise ValueError(
                        f"palette index {idx} out of range for palette length {palette_len}"
                    )

            sec = BiomeSection(
                section_y=sec_y,
                kind="packed",
                palette=palette,
                indices=tuple(indices_list),
            )
            sections.append(sec)
            section_idx += 1

    return Data3D(heightmap=heightmap, sections=tuple(sections))


def resolve_repeated_sections(decoded: Data3D) -> Data3D:
    """Replay the historical whole-section inheritance experiment.

    ``decode_data3d`` deliberately retains the raw marker as ``unknown`` for
    historical diagnostics. This operation copies the *entire* previous 16³
    array. It does NOT reproduce Bedrock's runtime query above the stored
    ceiling; use ``sample_bedrock_runtime`` for that separately verified path.
    Missing records/sections are never synthesized. A leading repeat is invalid.
    See the pinned Dragonfly reference and BDS evidence in BIOME_STORAGE_VERIFICATION.
    """
    if not isinstance(decoded, Data3D):
        raise TypeError("Expected decoded Data3D")
    sections = []
    for section in decoded.sections:
        if section.kind == "unknown":
            if not sections or sections[-1].section_y != section.section_y - 1:
                raise ValueError("Repeat marker has no previous contiguous section")
            previous = sections[-1]
            section = BiomeSection(section.section_y, previous.kind,
                                   previous.palette, previous.indices)
        sections.append(section)
    return Data3D(decoded.heightmap, tuple(sections))


def sample_bedrock_runtime(decoded: Data3D, x: int, y: int, z: int) -> int | None:
    """Sample explicit storage, clamping encoded trailing markers to its top.

    Pinned BDS 1.26.52.3 queries above its stored biome-section count use the
    last explicit section's Y=15 plane. They do not repeat its whole volume.
    This models that runtime lookup, not a seed-only generation algorithm.
    Missing sections and unvalidated interior markers remain unknown.
    """
    if not isinstance(decoded, Data3D):
        raise TypeError("Expected decoded Data3D")
    # Reuse the strict sampler's coordinate/type validation even for empty data.
    direct = decoded.sample(x, y, z)
    if direct is not None:
        return direct
    sections = decoded.sections
    requested = y // 16
    if not sections or not sections[0].section_y <= requested <= sections[-1].section_y:
        return None
    if any(b.section_y != a.section_y + 1 for a, b in zip(sections, sections[1:])):
        return None
    last = next((i for i in range(len(sections) - 1, -1, -1)
                 if sections[i].kind != "unknown"), None)
    if last is None or requested <= sections[last].section_y:
        return None
    if any(section.kind == "unknown" for section in sections[:last + 1]):
        return None
    return decoded.sample(x, sections[last].section_y * 16 + 15, z)
