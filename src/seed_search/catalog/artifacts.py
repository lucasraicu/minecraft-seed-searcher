"""Durable checksummed artifact storage with deterministic compression and strict validation."""
from pathlib import Path
import gzip
import hashlib
import json
import os
import re
import tempfile
import zlib

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_CONTENT_ADDR_RE = re.compile(r"^[0-9a-f]{2}/[0-9a-f]{64}(\.json)?\.gz$")
_EXPECTED_MANIFEST_FIELDS = {"sha256", "relative_key", "byte_length", "uncompressed_length", "codec"}


def _fsync_dir(path: Path) -> None:
    """Fsync a directory to ensure directory entry updates are durable."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _unique_pairs(pairs):
    res = {}
    for k, v in pairs:
        if k in res:
            raise ValueError(f"Duplicate JSON key: {k}")
        res[k] = v
    return res


def _reject_constant(val):
    raise ValueError(f"Nonfinite JSON constant: {val}")


class ArtifactStore:
    """Content-addressed durable artifact store for immutable JSON records."""

    def __init__(self, root: str | Path, max_bytes: int = 16 * 1024 * 1024):
        if not root:
            raise ValueError("Root path must be provided")
        self.raw_root = Path(root)
        if self.raw_root.is_symlink():
            raise ValueError(f"Root cannot be a symlink: {root}")
        self.root = self.raw_root.resolve()
        if self.raw_root.is_symlink() or self.root.is_symlink():
            raise ValueError(f"Root cannot be a symlink: {root}")
        self.root.mkdir(parents=True, exist_ok=True)
        if self.root.is_symlink() or self.raw_root.is_symlink():
            raise ValueError(f"Root cannot be a symlink: {root}")
        if not self.root.is_dir():
            raise ValueError(f"Root is not a directory: {root}")

        self.max_bytes = max_bytes
        if type(max_bytes) is not int or not 0 < max_bytes <= 16 * 1024 * 1024:
            raise ValueError("max_bytes must be positive")

        self._tmp_dir = self.root / ".tmp"
        if self._tmp_dir.is_symlink():
            raise ValueError('Symlink staging directory is not allowed')
        self._tmp_dir.mkdir(parents=True, exist_ok=True)
        # Do not remove another live writer's staging files on reader startup.

    def clean_temps(self) -> None:
        """Compatibility no-op; orphan cleanup requires an offline exclusive lease."""
        return None

    def _safe_resolve_key(self, relative_key: str, check_exists: bool = False) -> Path:
        if not isinstance(relative_key, str) or not relative_key:
            raise ValueError("relative_key must be a non-empty string")
        p = Path(relative_key)
        if p.is_absolute() or relative_key.startswith("/") or relative_key.startswith("\\"):
            raise ValueError(f"Absolute paths not permitted: {relative_key}")
        for part in p.parts:
            if part in ("..", ".", ""):
                raise ValueError(f"Path traversal not permitted: {relative_key}")

        if not _CONTENT_ADDR_RE.fullmatch(relative_key):
            raise ValueError(f"relative_key is not an opaque content-address key: {relative_key}")

        # Check no symlink components along the path
        curr = self.root
        for part in p.parts:
            curr = curr / part
            if curr.is_symlink():
                raise ValueError(f"Symlink component detected in path: {curr}")

        # Check resolution does not escape root
        resolved = curr.resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError:
            raise ValueError(f"Path escapes root directory: {relative_key}")

        if check_exists and not curr.is_file():
            raise FileNotFoundError(f"Artifact not found: {relative_key}")

        return curr

    def _validate_manifest(self, manifest: dict) -> None:
        if not isinstance(manifest, dict):
            raise ValueError("Manifest must be a dictionary")
        if set(manifest.keys()) != _EXPECTED_MANIFEST_FIELDS:
            raise ValueError(f"Invalid manifest fields: expected {_EXPECTED_MANIFEST_FIELDS}, got {set(manifest.keys())}")

        sha = manifest["sha256"]
        if not isinstance(sha, str) or not _HEX64_RE.fullmatch(sha):
            raise ValueError(f"Invalid sha256 in manifest: {sha}")

        codec = manifest["codec"]
        if codec not in ("gzip", "zlib"):
            raise ValueError(f"Unsupported codec in manifest: {codec}")

        byte_length = manifest["byte_length"]
        if type(byte_length) is not int or byte_length < 0 or byte_length > self.max_bytes:
            raise ValueError(f"Invalid byte_length in manifest: {byte_length}")

        uncompressed_length = manifest["uncompressed_length"]
        if type(uncompressed_length) is not int or uncompressed_length < 0 or uncompressed_length > self.max_bytes:
            raise ValueError(f"Invalid uncompressed_length in manifest: {uncompressed_length}")

        relative_key = manifest["relative_key"]
        if relative_key != f'{sha[:2]}/{sha}.json.gz':
            raise ValueError(f"relative_key does not match sha256: {relative_key}")

        # Validate that path is safe
        self._safe_resolve_key(relative_key)

    def put_json(self, payload: dict, codec: str = "gzip", *, compression_level: int = 9) -> dict:
        """Deterministically serialize, compress, and atomically publish a JSON dictionary."""
        if not isinstance(payload, dict):
            raise ValueError("Payload must be a JSON dictionary")

        try:
            uncompressed = json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False
            ).encode("utf-8")
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Non-JSON or nonfinite payload: {exc}") from exc

        uncompressed_len = len(uncompressed)
        if uncompressed_len > self.max_bytes:
            raise ValueError(f"Uncompressed payload size {uncompressed_len} exceeds max_bytes {self.max_bytes}")

        if type(compression_level) is not int or not 1 <= compression_level <= 9:
            raise ValueError("Compression level must be1..9")
        if codec == "gzip":
            compressed = gzip.compress(uncompressed, compresslevel=compression_level, mtime=0)
        elif codec == "zlib":
            compressed = zlib.compress(uncompressed, level=compression_level)
        else:
            raise ValueError(f"Unsupported codec: {codec}")

        compressed_len = len(compressed)
        if compressed_len > self.max_bytes:
            raise ValueError(f"Compressed payload size {compressed_len} exceeds max_bytes {self.max_bytes}")

        sha256_hex = hashlib.sha256(compressed).hexdigest()
        relative_key = f"{sha256_hex[:2]}/{sha256_hex}.json.gz"

        manifest = {
            "sha256": sha256_hex,
            "relative_key": relative_key,
            "byte_length": compressed_len,
            "uncompressed_length": uncompressed_len,
            "codec": codec,
        }

        target_path = self._safe_resolve_key(relative_key)
        if target_path.exists():
            # Reject existing corrupt object
            with open(target_path, "rb") as f:
                existing = f.read(self.max_bytes + 1)
            if len(existing) != compressed_len or hashlib.sha256(existing).hexdigest() != sha256_hex:
                raise ValueError(f"Existing artifact at {relative_key} is corrupt")
            return manifest

        target_path.parent.mkdir(parents=True, exist_ok=True)
        _fsync_dir(self.root)
        _fsync_dir(target_path.parent)

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(dir=self._tmp_dir, delete=False) as tf:
                temp_path = Path(tf.name)
                tf.write(compressed)
                tf.flush()
                os.fsync(tf.fileno())

            os.replace(temp_path, target_path)
            temp_path = None
            _fsync_dir(target_path.parent)
        finally:
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass

        return manifest

    def _read_verified_raw(self,manifest):
        """Check the immutable wire bytes without allocating the decoded JSON tree."""
        self._validate_manifest(manifest)
        target_path = self._safe_resolve_key(manifest["relative_key"], check_exists=True)

        with open(target_path, "rb") as f:
            data = f.read(self.max_bytes + 1)

        if len(data) > self.max_bytes:
            raise ValueError(f"Artifact byte length exceeds limit {self.max_bytes}")
        if len(data) != manifest["byte_length"]:
            raise ValueError(f"Artifact byte length mismatch: expected {manifest['byte_length']}, got {len(data)}")

        actual_sha = hashlib.sha256(data).hexdigest()
        if actual_sha != manifest["sha256"]:
            raise ValueError(f"Artifact sha256 mismatch: expected {manifest['sha256']}, got {actual_sha}")

        return data

    def get_json(self, manifest: dict) -> dict:
        """Validate manifest, read, decompress within bounds, and strictly parse JSON dictionary."""
        data=self._read_verified_raw(manifest)
        codec = manifest["codec"]
        if codec == "gzip":
            decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
        elif codec == "zlib":
            decompressor = zlib.decompressobj(zlib.MAX_WBITS)
        else:
            raise ValueError(f"Unsupported codec: {codec}")

        try:
            uncompressed = decompressor.decompress(data, self.max_bytes + 1)
        except Exception as exc:
            raise ValueError(f"Decompression failed: {exc}") from exc

        if decompressor.unconsumed_tail or len(uncompressed) > self.max_bytes:
            raise ValueError("Decompressed payload exceeds max_bytes limit")
        if not decompressor.eof or decompressor.unused_data:
            raise ValueError('Truncated or trailing compressed stream')
        if len(uncompressed) != manifest["uncompressed_length"]:
            raise ValueError(
                f"Decompressed length mismatch: expected {manifest['uncompressed_length']}, got {len(uncompressed)}"
            )

        try:
            payload = json.loads(
                uncompressed.decode("utf-8"),
                object_pairs_hook=_unique_pairs,
                parse_constant=_reject_constant
            )
        except Exception as exc:
            raise ValueError(f"Invalid or corrupt JSON: {exc}") from exc

        if not isinstance(payload, dict):
            raise ValueError("Decoded JSON root is not a dictionary")

        return payload

    def copy_raw_to(
        self,
        relative_key: str,
        dest_store: "ArtifactStore",
        expected_sha: str | None = None,
        expected_len: int | None = None
    ) -> None:
        """Safely copy a verified artifact from this store to a destination store."""
        src_path = self._safe_resolve_key(relative_key, check_exists=True)
        with open(src_path, "rb") as f:
            data = f.read(self.max_bytes + 1)

        if len(data) > self.max_bytes:
            raise ValueError("Artifact exceeds max_bytes")
        if expected_len is not None and len(data) != expected_len:
            raise ValueError(f"Artifact byte length mismatch: expected {expected_len}, got {len(data)}")
        actual_sha = hashlib.sha256(data).hexdigest()
        if expected_sha is not None and actual_sha != expected_sha:
            raise ValueError(f"Artifact sha256 mismatch: expected {expected_sha}, got {actual_sha}")

        dest_path = dest_store._safe_resolve_key(relative_key)
        if dest_path.exists():
            with open(dest_path, "rb") as f:
                existing = f.read(self.max_bytes + 1)
            if existing == data:
                return
            raise ValueError(f"Destination artifact {relative_key} exists but is corrupt")

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        _fsync_dir(dest_store.root)
        _fsync_dir(dest_path.parent)

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(dir=dest_store._tmp_dir, delete=False) as tf:
                temp_path = Path(tf.name)
                tf.write(data)
                tf.flush()
                os.fsync(tf.fileno())
            os.replace(temp_path, dest_path)
            temp_path = None
            _fsync_dir(dest_path.parent)
        finally:
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
