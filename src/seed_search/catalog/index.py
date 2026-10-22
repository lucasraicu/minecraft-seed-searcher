"""Pure deterministic exact bitmap index over catalog layout summaries.

Independent pure artifact module implementing frozen interfaces:
- build_index(layouts) -> dict
- candidate_indices(layouts, request, *, index=None, trusted=False) -> list[int]
- index_identity(layouts) -> str
- validate_index(index, *, layouts=None, trusted=False) -> bool
"""
import hashlib
import re
from .registry import (
    STRUCTURES, BIOMES, SIDES, RADII, FEATURE_IDS,
    REGISTRY_REVISION, POLICY, digest, canonical_json
)
from .models import GEOMETRY_REVISION
from .codec import summary_metadata, pack_summary, validate_summary, MISSING
from .request import validate_request, load_request

INDEX_REVISION = 'catalog-bitmap-index-v1'
_LOWER_HEX_RE = re.compile(r'[0-9a-f]*')
POLICY_REVISION = digest(POLICY)
RADII_MAP = {r: i for i, r in enumerate(RADII)}
RADII_SQUARED = tuple(r * r for r in RADII)

STRUCTURE_SLOTS = {f['id']: f['slot'] for f in STRUCTURES}
BIOME_SLOTS = {f['id']: f['slot'] for f in BIOMES}
FEATURE_SLOTS = {f['id']: i for i, f in enumerate(STRUCTURES + BIOMES)}

__all__ = [
    'INDEX_REVISION',
    'build_index',
    'candidate_indices',
    'index_identity',
    'validate_index',
    'encode_bitset',
    'decode_bitset',
]


def encode_bitset(val, num_rows):
    """Serialize a bitset integer of length num_rows into canonical lowercase hex."""
    if not isinstance(val, int) or val < 0:
        raise ValueError('Invalid bitset integer')
    if num_rows == 0:
        if val != 0:
            raise ValueError('Bitset for 0 rows must be 0')
        return ""
    if val >= (1 << num_rows):
        raise ValueError('Bitset value exceeds declared row capacity')
    byte_len = (num_rows + 7) // 8
    hex_len = byte_len * 2
    return f"{val:0{hex_len}x}"


def decode_bitset(hex_str, num_rows):
    """Deserialize and validate a bitset hex string with strict length and reserved bit checks."""
    if not isinstance(hex_str, str):
        raise ValueError('Bitset must be a string')
    byte_len = (num_rows + 7) // 8
    expected_hex_len = byte_len * 2
    if len(hex_str) != expected_hex_len:
        raise ValueError(f'Bitset length mismatch: expected {expected_hex_len}, got {len(hex_str)}')
    if _LOWER_HEX_RE.fullmatch(hex_str) is None:
        raise ValueError('Bitset must be lowercase hex')
    val = int(hex_str, 16) if hex_str else 0
    if num_rows == 0:
        if val != 0:
            raise ValueError('Bitset for 0 rows must be 0')
    else:
        if val >= (1 << num_rows):
            raise ValueError(f'Reserved bits set: value exceeds {num_rows} bits')
    return val


def layout_descriptor(summary):
    """Derive deterministic metadata and 364-byte payload SHA for one layout."""
    meta = summary_metadata(summary)
    payload = pack_summary(summary)
    payload_sha256 = hashlib.sha256(payload).hexdigest()
    return {
        'metadata': meta,
        'payload_sha256': payload_sha256,
    }


def index_identity(layouts):
    """Derive canonical reusable content binding across layouts and revisions."""
    if not isinstance(layouts, (list, tuple)):
        layouts = list(layouts)
    if len(layouts) > 256:
        raise ValueError('At most 256 layouts')
    entries = [layout_descriptor(l) for l in layouts]
    binding = {
        'geometry_revision': GEOMETRY_REVISION,
        'index_revision': INDEX_REVISION,
        'layouts': entries,
        'policy_revision': POLICY_REVISION,
        'registry_revision': REGISTRY_REVISION,
    }
    return digest(binding)


def build_index(layouts):
    """Build canonical JSON-serializable bitmap index for up to 256 layouts."""
    if not isinstance(layouts, (list, tuple)):
        layouts = list(layouts)
    N = len(layouts)
    if N > 256:
        raise ValueError('At most 256 layouts')

    for l in layouts:
        validate_summary(l)

    # 1. Sides bitset (one bitset per supported side)
    sides_dict = {}
    for side in SIDES:
        s_val = sum(1 << i for i, l in enumerate(layouts) if l['border_side'] == side)
        sides_dict[str(side)] = encode_bitset(s_val, N)

    # 2. Origin bitset (layouts centered at (0, 0))
    origin_val = sum(1 << i for i, l in enumerate(layouts) if tuple(l['anchor']) == (0, 0))
    origin_hex = encode_bitset(origin_val, N)

    # 3. Coverage bitsets (all 23 features x 4 scopes)
    cov_dict = {}
    for feat_id in FEATURE_IDS:
        slot = FEATURE_SLOTS[feat_id]
        cov_dict[feat_id] = [
            encode_bitset(sum(1 << i for i, l in enumerate(layouts) if l['complete'][slot][scope]), N)
            for scope in range(4)
        ]

    # 4. Structure thresholds (14 structures x 4 scopes x 16 thresholds)
    st_dict = {}
    for f in STRUCTURES:
        feat_id = f['id']
        slot = f['slot']
        scopes_list = []
        for scope in range(4):
            thresh_list = []
            for threshold in range(1, 17):
                val = sum(
                    1 << i for i, l in enumerate(layouts)
                    if l['complete'][slot][scope] and l['counts'][slot][scope] >= threshold
                )
                thresh_list.append(encode_bitset(val, N))
            scopes_list.append(thresh_list)
        st_dict[feat_id] = scopes_list

    # 5. Biome witnesses (9 biomes x 4 scopes)
    bw_dict = {}
    for b in BIOMES:
        feat_id = b['id']
        slot = b['slot']
        comp_slot = 14 + slot
        scopes_list = []
        for scope in range(4):
            if scope < 3:
                r2 = RADII_SQUARED[scope]
                val = sum(
                    1 << i for i, l in enumerate(layouts)
                    if l['complete'][comp_slot][scope]
                    and l['biome_nearest_d2'][slot] != MISSING
                    and l['biome_nearest_d2'][slot] <= r2
                )
            else:
                val = sum(
                    1 << i for i, l in enumerate(layouts)
                    if l['biome_nearest_d2'][slot] != MISSING
                )
            scopes_list.append(encode_bitset(val, N))
        bw_dict[feat_id] = scopes_list

    bitsets = {
        'biome_witnesses': bw_dict,
        'coverage': cov_dict,
        'origin': origin_hex,
        'sides': sides_dict,
        'structure_thresholds': st_dict,
    }

    content_id = index_identity(layouts)
    body = {
        'bitsets': bitsets,
        'content_digest': content_id,
        'num_rows': N,
        'revision': INDEX_REVISION,
    }
    idx_digest = digest(body)

    return {
        'bitsets': bitsets,
        'content_digest': content_id,
        'index_digest': idx_digest,
        'num_rows': N,
        'revision': INDEX_REVISION,
    }


def validate_index(index, *, layouts=None, trusted=False):
    """Validate index schema, bitlength, reserved bits, digests, and layout bindings."""
    if not isinstance(index, dict):
        raise ValueError('Index must be a dict')
    expected_keys = {'revision', 'num_rows', 'content_digest', 'index_digest', 'bitsets'}
    if set(index) != expected_keys:
        raise ValueError('Invalid index schema')
    if index['revision'] != INDEX_REVISION:
        raise ValueError('Invalid index revision')
    num_rows = index['num_rows']
    if type(num_rows) is not int or not 0 <= num_rows <= 256:
        raise ValueError('Invalid num_rows')
    for d_field in ('content_digest', 'index_digest'):
        val = index[d_field]
        if not isinstance(val, str) or len(val) != 64 or any(c not in '0123456789abcdef' for c in val):
            raise ValueError(f'Invalid {d_field}')

    # Independently verify index_digest
    body = {
        'bitsets': index['bitsets'],
        'content_digest': index['content_digest'],
        'num_rows': index['num_rows'],
        'revision': index['revision'],
    }
    if digest(body) != index['index_digest']:
        raise ValueError('Corrupt index: index_digest mismatch')

    # Validate bitsets container
    bitsets = index['bitsets']
    if not isinstance(bitsets, dict) or set(bitsets) != {'sides', 'origin', 'coverage', 'structure_thresholds', 'biome_witnesses'}:
        raise ValueError('Invalid bitsets container')

    # Sides
    sides = bitsets['sides']
    if not isinstance(sides, dict) or set(sides) != {str(s) for s in SIDES}:
        raise ValueError('Invalid sides in bitset')
    for s_str in sides:
        decode_bitset(sides[s_str], num_rows)

    # Origin
    decode_bitset(bitsets['origin'], num_rows)

    # Coverage
    cov = bitsets['coverage']
    if not isinstance(cov, dict) or set(cov) != set(FEATURE_IDS):
        raise ValueError('Invalid coverage in bitset')
    for feat_id in FEATURE_IDS:
        scopes = cov[feat_id]
        if not isinstance(scopes, list) or len(scopes) != 4:
            raise ValueError('Invalid coverage scopes in bitset')
        for h in scopes:
            decode_bitset(h, num_rows)

    # Structure thresholds
    st = bitsets['structure_thresholds']
    expected_struct_ids = {f['id'] for f in STRUCTURES}
    if not isinstance(st, dict) or set(st) != expected_struct_ids:
        raise ValueError('Invalid structure_thresholds in bitset')
    for feat_id in expected_struct_ids:
        scopes = st[feat_id]
        if not isinstance(scopes, list) or len(scopes) != 4:
            raise ValueError('Invalid structure scopes in bitset')
        for thresh_list in scopes:
            if not isinstance(thresh_list, list) or len(thresh_list) != 16:
                raise ValueError('Invalid structure thresholds list')
            for h in thresh_list:
                decode_bitset(h, num_rows)

    # Biome witnesses
    bw = bitsets['biome_witnesses']
    expected_biome_ids = {b['id'] for b in BIOMES}
    if not isinstance(bw, dict) or set(bw) != expected_biome_ids:
        raise ValueError('Invalid biome_witnesses in bitset')
    for feat_id in expected_biome_ids:
        scopes = bw[feat_id]
        if not isinstance(scopes, list) or len(scopes) != 4:
            raise ValueError('Invalid biome scopes in bitset')
        for h in scopes:
            decode_bitset(h, num_rows)

    if layouts is not None:
        if len(layouts) != num_rows:
            raise ValueError('Row count mismatch between layouts and index')
        expected_content_digest = index_identity(layouts)
        if index['content_digest'] != expected_content_digest:
            raise ValueError('Index content_digest mismatch with layouts')
        if not trusted:
            expected_index = build_index(layouts)
            if index['bitsets'] != expected_index['bitsets']:
                raise ValueError('Tampered bitset in index')

    return True


def candidate_indices(layouts, request, *, index=None, trusted=False):
    """Filter layout candidates passing all Required rows, border side and mode."""
    if not isinstance(layouts, (list, tuple)):
        layouts = list(layouts)
    N = len(layouts)
    if N > 256:
        raise ValueError('At most 256 layouts')

    if isinstance(request, str):
        req = load_request(request)
    else:
        req = validate_request(request)

    if index is None:
        idx = build_index(layouts)
    else:
        idx = index
        validate_index(idx, layouts=layouts, trusted=trusted)

    return _select_index(idx,req)


def filter_index(index,request):
    """Filter an immutable manifest-bound index BEFORE unpacking summary rows.

    Integrity and content provenance are verified by the segment reader. This
    entry point validates index schema/digest/bit lengths but has no raw layouts
    to independently rederive semantics; untrusted callers use candidate_indices.
    """
    req=load_request(request) if isinstance(request,str) else validate_request(request)
    validate_index(index)
    return _select_index(index,req)


def _select_index(idx,req):
    N=idx['num_rows']
    if N == 0:
        return []

    mask = (1 << N) - 1

    # 1. Border side filtering
    req_side = req['border_side']
    side_hex = idx['bitsets']['sides'][str(req_side)]
    side_val = decode_bitset(side_hex, N)
    mask &= side_val
    if mask == 0:
        return []

    # 2. Anchor mode filtering
    if req['anchor_mode'] == 'origin':
        origin_hex = idx['bitsets']['origin']
        origin_val = decode_bitset(origin_hex, N)
        mask &= origin_val
        if mask == 0:
            return []

    # 3. Required rows filtering (Preferred rows do not filter)
    for r in req['rows']:
        if r['rule'] != 'required':
            continue
        scope_kind = r['scope']['kind']
        scope_idx = 3 if scope_kind == 'inside_border' else RADII_MAP[r['scope']['radius']]

        if r['kind'] == 'structure_count':
            feat_id = r['feature']
            at_least = r['at_least']
            thresh_hex = idx['bitsets']['structure_thresholds'][feat_id][scope_idx][at_least - 1]
            thresh_val = decode_bitset(thresh_hex, N)
            mask &= thresh_val
        elif r['kind'] == 'biome_witness':
            any_of = r['any_of']
            # All alternatives in any_of must have coverage complete at scope_idx
            for bid in any_of:
                cov_hex = idx['bitsets']['coverage'][bid][scope_idx]
                cov_val = decode_bitset(cov_hex, N)
                mask &= cov_val
            # At least one alternative in any_of must have positive witness at scope_idx
            witness_or = 0
            for bid in any_of:
                wit_hex = idx['bitsets']['biome_witnesses'][bid][scope_idx]
                wit_val = decode_bitset(wit_hex, N)
                witness_or |= wit_val
            mask &= witness_or

        if mask == 0:
            return []

    return [i for i in range(N) if (mask & (1 << i))]
