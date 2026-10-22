"""Stage D frozen evidence overlay interfaces and persistence.

Implements build_evidence, validate_evidence, write_evidence, read_evidence,
and summarize_structure per Stage D specifications.
"""
from __future__ import annotations

from pathlib import Path
import copy
import json
import os
import uuid
import stat

from .models import (
    validate_identity,
    validate_observation,
    world_id as compute_world_id,
    observation_id as compute_observation_id,
)
from .registry import (
    canonical_json,
    digest,
)

EVIDENCE_REVISION = "catalog-evidence-v1"
SUMMARY_REVISION = "catalog-structure-evidence-summary-v1"

MAX_CHECKS_PER_TYPE = 10000
MAX_ENVELOPE_BYTES = 16 * 1024 * 1024
COORD_LIMIT = 1 << 30

FEATURE_TO_COMMAND = {
    "structure.village": "village",
    "structure.trial_chamber": "trial_chambers",
    "structure.ancient_city": "ancient_city",
    "structure.mansion": "mansion",
    "structure.monument": "monument",
    "structure.outpost": "pillager_outpost",
    "structure.desert_pyramid": "temple",
    "structure.jungle_temple": "temple",
    "structure.swamp_hut": "temple",
    "structure.igloo": "temple",
    "structure.trail_ruins": "trail_ruins",
    "structure.ruined_portal": "ruined_portal",
    "structure.shipwreck": "shipwreck",
    "structure.mineshaft": "mineshaft",
}

TEMPLE_FEATURE_IDS = frozenset({
    "structure.desert_pyramid",
    "structure.jungle_temple",
    "structure.swamp_hut",
    "structure.igloo",
})

STRUCTURE_FEATURE_IDS = frozenset(FEATURE_TO_COMMAND.keys())

STRUCTURE_OUTCOMES = frozenset({
    "located_exact",
    "coordinate_difference",
    "no_location",
    "error",
})

BIOME_OUTCOMES = frozenset({
    "observed",
    "error",
})

HEX64_CHARS = frozenset("0123456789abcdef")


def _is_hex64(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in HEX64_CHARS for c in value)
    )


def _is_coord(value: object) -> bool:
    return (
        type(value) is int
        and not isinstance(value, bool)
        and -COORD_LIMIT < value < COORD_LIMIT
    )


def _check_no_symlinks(target_file: Path, root: Path) -> None:
    # Inspect lexical ancestors before resolve(), including ancestors above root.
    for component in (target_file.absolute(), *target_file.absolute().parents):
        if component.is_symlink():
            raise ValueError(f"Symlink component rejected: {component}")


def _fsync_dir(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _no_duplicate_keys(pairs):
    res = {}
    for k, v in pairs:
        if k in res:
            raise ValueError(f"Duplicate JSON key: {k!r}")
        res[k] = v
    return res


def _reject_constant(c):
    raise ValueError(f"Nonfinite number or constant: {c!r}")


def _parse_strict_json(data: bytes) -> dict:
    if len(data) > MAX_ENVELOPE_BYTES:
        raise ValueError("Serialized envelope exceeds 16MiB limit")
    try:
        text = data.decode("utf-8")
        parsed = json.loads(
            text,
            object_pairs_hook=_no_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except Exception as exc:
        raise ValueError(f"Malformed JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Envelope must be a JSON object")
    return parsed


def validate_evidence(payload: dict, *, observation: dict | None = None) -> dict:
    """Validate evidence payload per Stage D schema and provenance rules.

    Returns the same payload if valid; raises ValueError on any violation.
    """
    if not isinstance(payload, dict):
        raise ValueError("Evidence payload must be a dict")

    exact_payload_keys = {
        "revision",
        "snapshot_id",
        "world_id",
        "observation_id",
        "source_identity",
        "verifier",
        "structure_checks",
        "biome_checks",
    }
    if set(payload) != exact_payload_keys:
        raise ValueError("Invalid evidence payload keys")

    if payload["revision"] != EVIDENCE_REVISION:
        raise ValueError(f"Unsupported revision: {payload['revision']!r}")

    snapshot_id = payload["snapshot_id"]
    if not _is_hex64(snapshot_id):
        raise ValueError("snapshot_id must be lowercase 64-hex string")

    world_id = payload["world_id"]
    if not _is_hex64(world_id):
        raise ValueError("world_id must be lowercase 64-hex string")

    observation_id = payload["observation_id"]
    if not _is_hex64(observation_id):
        raise ValueError("observation_id must be lowercase 64-hex string")

    source_identity = payload["source_identity"]
    validate_identity(source_identity)
    if compute_world_id(source_identity) != world_id:
        raise ValueError("source_identity and world_id do not agree")

    verifier = payload["verifier"]
    if not isinstance(verifier, dict):
        raise ValueError("verifier must be a dict")
    exact_verifier_keys = {
        "edition",
        "game_build_id",
        "image_sha256",
        "script_api",
        "settings_sha256",
        "report_sha256s",
    }
    if set(verifier) != exact_verifier_keys:
        raise ValueError("Invalid verifier keys")

    if verifier["edition"] != "bedrock":
        raise ValueError("verifier edition must be 'bedrock'")

    game_build_id = verifier["game_build_id"]
    if (
        not isinstance(game_build_id, str)
        or not game_build_id
        or len(game_build_id) > 256
        or game_build_id.startswith("research:")
    ):
        raise ValueError("verifier game_build_id must be nonempty exact BDS build, never research:*")

    if not _is_hex64(verifier["image_sha256"]):
        raise ValueError("verifier image_sha256 must be lowercase 64-hex without prefix")

    script_api = verifier["script_api"]
    if not isinstance(script_api, str) or not script_api or len(script_api) > 256:
        raise ValueError("verifier script_api must be bounded nonempty string")

    if not _is_hex64(verifier["settings_sha256"]):
        raise ValueError("verifier settings_sha256 must be lowercase 64-hex")

    reports = verifier["report_sha256s"]
    if (
        not isinstance(reports, list)
        or not (1 <= len(reports) <= 32)
        or not all(_is_hex64(r) for r in reports)
        or len(set(reports)) != len(reports)
    ):
        raise ValueError("verifier report_sha256s must be 1..32 unique lowercase 64-hex digests")

    structure_checks = payload["structure_checks"]
    if not isinstance(structure_checks, list) or len(structure_checks) > MAX_CHECKS_PER_TYPE:
        raise ValueError(f"structure_checks must be list with <= {MAX_CHECKS_PER_TYPE} items")

    seen_structures = set()
    exact_structure_keys = {"feature_id", "command_id", "predicted", "reported", "outcome"}
    for check in structure_checks:
        if not isinstance(check, dict) or set(check) != exact_structure_keys:
            raise ValueError("Invalid structure check keys")

        feature_id = check["feature_id"]
        if not isinstance(feature_id, str) or feature_id not in STRUCTURE_FEATURE_IDS:
            raise ValueError(f"Unregistered structure feature: {feature_id}")

        expected_command = FEATURE_TO_COMMAND[feature_id]
        if check["command_id"] != expected_command:
            raise ValueError(
                f"command_id mismatch for {feature_id}: expected {expected_command}, got {check['command_id']}"
            )

        predicted = check["predicted"]
        if (
            not isinstance(predicted, list)
            or len(predicted) != 2
            or not _is_coord(predicted[0])
            or not _is_coord(predicted[1])
        ):
            raise ValueError("predicted must be [intX, intZ] within bounds without booleans")

        struct_key = (feature_id, predicted[0], predicted[1])
        if struct_key in seen_structures:
            raise ValueError(f"Duplicate (feature_id, predicted) check: {struct_key}")
        seen_structures.add(struct_key)

        reported = check["reported"]
        if reported is not None:
            if (
                not isinstance(reported, list)
                or len(reported) != 2
                or not _is_coord(reported[0])
                or not _is_coord(reported[1])
            ):
                raise ValueError("reported must be [intX, intZ] within bounds without booleans or null")

        outcome = check["outcome"]
        if not isinstance(outcome, str) or outcome not in STRUCTURE_OUTCOMES:
            raise ValueError(f"Invalid structure outcome: {outcome}")

        if outcome == "located_exact":
            if reported is None or reported != predicted:
                raise ValueError("located_exact requires reported == predicted")
        elif outcome == "coordinate_difference":
            if reported is None or reported == predicted:
                raise ValueError("coordinate_difference requires non-null reported != predicted")
        elif outcome == "no_location":
            if reported is not None:
                raise ValueError("no_location requires null reported")
        elif outcome == "error":
            if reported is not None:
                raise ValueError("error requires null reported")

    biome_checks = payload["biome_checks"]
    if not isinstance(biome_checks, list) or len(biome_checks) > MAX_CHECKS_PER_TYPE:
        raise ValueError(f"biome_checks must be list with <= {MAX_CHECKS_PER_TYPE} items")

    seen_biomes = set()
    exact_biome_keys = {"position", "observed_name", "outcome"}
    for bcheck in biome_checks:
        if not isinstance(bcheck, dict) or set(bcheck) != exact_biome_keys:
            raise ValueError("Invalid biome check keys")

        pos = bcheck["position"]
        if (
            not isinstance(pos, list)
            or len(pos) != 3
            or not _is_coord(pos[0])
            or not _is_coord(pos[1])
            or not _is_coord(pos[2])
        ):
            raise ValueError("position must be [intX, intY, intZ] within bounds without booleans")

        pos_key = (pos[0], pos[1], pos[2])
        if pos_key in seen_biomes:
            raise ValueError(f"Duplicate biome position check: {pos_key}")
        seen_biomes.add(pos_key)

        b_outcome = bcheck["outcome"]
        if not isinstance(b_outcome, str) or b_outcome not in BIOME_OUTCOMES:
            raise ValueError(f"Invalid biome outcome: {b_outcome}")

        obs_name = bcheck["observed_name"]
        if b_outcome == "observed":
            if not isinstance(obs_name, str) or not obs_name or len(obs_name) > 256:
                raise ValueError("observed outcome requires non-empty bounded observed_name string")
        elif b_outcome == "error":
            if obs_name is not None:
                raise ValueError("error outcome requires null observed_name")

    if observation is not None:
        validate_observation(observation)
        if payload["source_identity"] != observation["identity"]:
            raise ValueError("payload source_identity does not match observation identity")
        if payload["world_id"] != compute_world_id(observation["identity"]):
            raise ValueError("payload world_id does not match observation world_id")
        if payload["observation_id"] != compute_observation_id(observation):
            raise ValueError("payload observation_id does not match observation observation_id")

        source_starts = {fid: {tuple(point) for point in points}
                         for fid, points in observation['structures'].items()}
        for check in structure_checks:
            if tuple(check["predicted"]) not in source_starts.get(check["feature_id"], set()):
                raise ValueError(
                    f"Predicted point {check['predicted']} for {check['feature_id']} not in source observation"
                )

        obs_biome_positions = {(p[0], p[1], p[2]) for p in observation["biomes"]}
        for bcheck in biome_checks:
            if tuple(bcheck["position"]) not in obs_biome_positions:
                raise ValueError(f"Biome position {bcheck['position']} not in source observation")

    envelope = {
        "sha256": digest(payload),
        "payload": payload,
    }
    encoded = canonical_json(envelope)
    if len(encoded) > MAX_ENVELOPE_BYTES:
        raise ValueError("Serialized envelope exceeds 16MiB limit")

    return payload


def build_evidence(
    observation: dict,
    snapshot_id: str,
    verifier: dict,
    structure_checks: list,
    biome_checks: list | None = None,
) -> dict:
    """Build and validate an evidence payload from observation and verification checks."""
    validate_observation(observation)
    if biome_checks is None:
        biome_checks = []

    payload = {
        "revision": EVIDENCE_REVISION,
        "snapshot_id": snapshot_id,
        "world_id": compute_world_id(observation["identity"]),
        "observation_id": compute_observation_id(observation),
        "source_identity": copy.deepcopy(observation["identity"]),
        "verifier": copy.deepcopy(verifier),
        "structure_checks": copy.deepcopy(structure_checks),
        "biome_checks": copy.deepcopy(biome_checks),
    }
    validate_evidence(payload, observation=observation)
    return payload


def _read_file_payload(
    target_file: Path,
    snapshot_id: str,
    world_id: str,
    observation_id: str,
) -> dict:
    info = target_file.stat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('Evidence must be a regular file')
    if info.st_size > MAX_ENVELOPE_BYTES:
        raise ValueError("Evidence file exceeds 16MiB limit")

    with target_file.open("rb") as stream:
        data = stream.read(MAX_ENVELOPE_BYTES + 1)
    envelope = _parse_strict_json(data)
    exact_envelope_keys = {"sha256", "payload"}
    if set(envelope) != exact_envelope_keys:
        raise ValueError("Invalid evidence envelope keys")

    sha256_digest = envelope["sha256"]
    payload = envelope["payload"]
    if not isinstance(payload, dict):
        raise ValueError("Envelope payload must be a JSON object")

    calculated_digest = digest(payload)
    if calculated_digest != sha256_digest:
        raise ValueError("Envelope checksum mismatch")

    if payload.get("snapshot_id") != snapshot_id:
        raise ValueError("snapshot_id mismatch")
    if payload.get("world_id") != world_id:
        raise ValueError("world_id mismatch")
    if payload.get("observation_id") != observation_id:
        raise ValueError("observation_id mismatch")

    validate_evidence(payload)
    return payload


def write_evidence(root: object, payload: dict) -> Path:
    """Durably write evidence payload to root/evidence/<snapshot_id>/<world_id>.json.

    Immutable no-clobber publication; returns target Path.
    """
    validate_evidence(payload)

    root_path = Path(root)
    snapshot_id = payload["snapshot_id"]
    world_id = payload["world_id"]
    observation_id = payload["observation_id"]

    evidence_dir = root_path / "evidence" / snapshot_id
    target_file = evidence_dir / f"{world_id}.json"

    _check_no_symlinks(target_file, root_path)

    envelope = {
        "sha256": digest(payload),
        "payload": payload,
    }
    content = canonical_json(envelope)
    if len(content) > MAX_ENVELOPE_BYTES:
        raise ValueError("Serialized envelope exceeds 16MiB limit")

    if target_file.exists():
        existing_payload = _read_file_payload(target_file, snapshot_id, world_id, observation_id)
        if existing_payload == payload:
            _fsync_dir(evidence_dir)
            return target_file
        raise ValueError("Cannot clobber existing evidence with different payload")

    missing = []
    parent = evidence_dir
    while not parent.exists():
        missing.append(parent)
        parent = parent.parent
    for directory in reversed(missing):
        directory.mkdir(exist_ok=True)
        _fsync_dir(directory.parent)
    _check_no_symlinks(target_file, root_path)

    temp_name = f".tmp_{world_id}_{os.getpid()}_{uuid.uuid4().hex}"
    temp_file = evidence_dir / temp_name
    try:
        fd = os.open(temp_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())

        try:
            os.link(str(temp_file), str(target_file))
        except FileExistsError:
            existing_payload = _read_file_payload(target_file, snapshot_id, world_id, observation_id)
            if existing_payload == payload:
                _fsync_dir(evidence_dir)
                return target_file
            raise ValueError("Concurrent publication collision with different payload")

        _fsync_dir(evidence_dir)
    finally:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass

    return target_file


def read_evidence(
    root: object,
    snapshot_id: str,
    world_id: str,
    observation_id: str,
) -> dict | None:
    """Read evidence payload, binding snapshot_id, world_id, observation_id, and checksum.

    Returns payload, or None if missing. Raises ValueError on corruption or provenance mismatch.
    """
    if not _is_hex64(snapshot_id):
        raise ValueError("Invalid snapshot_id")
    if not _is_hex64(world_id):
        raise ValueError("Invalid world_id")
    if not _is_hex64(observation_id):
        raise ValueError("Invalid observation_id")

    root_path = Path(root)
    evidence_dir = root_path / "evidence" / snapshot_id
    target_file = evidence_dir / f"{world_id}.json"

    _check_no_symlinks(target_file, root_path)

    if not target_file.exists():
        return None

    if not target_file.is_file():
        raise ValueError(f"Evidence path is not a regular file: {target_file}")

    return _read_file_payload(target_file, snapshot_id, world_id, observation_id)


def summarize_structure(
    payload_or_none: dict | None,
    feature_id: str,
    predictions: object,
    *,
    total_count: int | None = None,
) -> dict:
    """Produce structure evidence summary for a given feature and scoped predictions."""
    if not isinstance(feature_id, str) or feature_id not in STRUCTURE_FEATURE_IDS:
        raise ValueError(f"Unregistered structure feature: {feature_id}")

    try:
        pred_iter = iter(predictions)
    except TypeError as exc:
        raise ValueError("predictions must be iterable") from exc

    unique_preds = set()
    for p in pred_iter:
        if (
            not isinstance(p, (list, tuple))
            or len(p) != 2
            or not _is_coord(p[0])
            or not _is_coord(p[1])
        ):
            raise ValueError("Prediction coordinates must be [intX, intZ] within bounds without booleans")
        unique_preds.add((p[0], p[1]))
        if len(unique_preds) > 200000:
            raise ValueError('Too many scoped prediction coordinates')

    num_unique = len(unique_preds)

    if total_count is not None:
        if type(total_count) is not int or not 0 <= total_count <= 200000:
            raise ValueError("total_count must be a non-negative integer")
        if total_count < num_unique:
            raise ValueError("total_count cannot be smaller than supplied unique predictions")
        predicted_count = total_count
    else:
        predicted_count = num_unique

    grouped_command = feature_id in TEMPLE_FEATURE_IDS

    if payload_or_none is None:
        return {
            "revision": SUMMARY_REVISION,
            "feature_id": feature_id,
            "predicted_count": predicted_count,
            "tested_count": 0,
            "located_exact": 0,
            "coordinate_difference": 0,
            "no_location": 0,
            "errors": 0,
            "untested_count": predicted_count,
            "grouped_command": grouped_command,
            "verifier_game_build_id": None,
            "generated_count": None,
            "exhaustive_count": None,
        }

    validate_evidence(payload_or_none)
    verifier_game_build_id = payload_or_none["verifier"]["game_build_id"]

    located_exact = 0
    coordinate_difference = 0
    no_location = 0
    errors = 0

    for check in payload_or_none["structure_checks"]:
        if check["feature_id"] == feature_id:
            pred_tuple = (check["predicted"][0], check["predicted"][1])
            if pred_tuple in unique_preds:
                outcome = check["outcome"]
                if outcome == "located_exact":
                    located_exact += 1
                elif outcome == "coordinate_difference":
                    coordinate_difference += 1
                elif outcome == "no_location":
                    no_location += 1
                elif outcome == "error":
                    errors += 1

    tested_count = located_exact + coordinate_difference + no_location + errors
    untested_count = predicted_count - tested_count

    return {
        "revision": SUMMARY_REVISION,
        "feature_id": feature_id,
        "predicted_count": predicted_count,
        "tested_count": tested_count,
        "located_exact": located_exact,
        "coordinate_difference": coordinate_difference,
        "no_location": no_location,
        "errors": errors,
        "untested_count": untested_count,
        "grouped_command": grouped_command,
        "verifier_game_build_id": verifier_game_build_id,
        "generated_count": None,
        "exhaustive_count": None,
    }
