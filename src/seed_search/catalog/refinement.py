"""Bounded exact-scope biome tiles. Unknown blocks never become absence proofs.

Tiles are absolute/world-aligned and provider-specific. This brute-force reference
path deliberately makes no unproved noise/Voronoi pruning assumptions.
"""
import base64
import struct
import zlib
from .accuracy import validate_context, integer
from .registry import digest

REVISION = 'catalog-biome-tile-v1'
UNKNOWN = 0xffffffff
MAX_BLOCKS = 4096
PROVIDERS = ('procedural_model_v1','bds_saved_runtime_v3','bds_script_api_v1')


def provider_id(context):
    ctx = validate_context(context)
    if ctx['provider'] not in PROVIDERS:
        raise ValueError('Expected a biome provider')
    # Native raw IDs are fixed by the source/model identity. Game exports/API
    # tables can have observation-specific ID namespaces; do not join separate
    # runs merely because seed/build match. A combined oracle needs an explicit
    # newly bound context and a checked common namespace.
    return digest({k:v for k,v in ctx.items() if k!='evidence_sha256'} if ctx['provider']=='procedural_model_v1' else ctx)


def _bounds(bounds, *, cap=MAX_BLOCKS):
    if not isinstance(bounds,list) or len(bounds)!=4:
        raise ValueError('Expected half-open [loX,loZ,hiX,hiZ] bounds')
    x,z,hx,hz = [integer(v,-30_000_000,30_000_001) for v in bounds]
    if hx<=x or hz<=z or (hx-x)*(hz-z)>cap:
        raise ValueError('Invalid or over-budget tile/scope')
    return x,z,hx,hz


def _height(context,y):
    return integer(y,*((-64,319) if context['dimension']=='overworld' else (0,127)))


def _names(names):
    if not isinstance(names,dict) or len(names)>256:raise ValueError('Invalid tile ID namespace')
    for key,value in names.items():
        if not isinstance(key,str) or not key.isascii() or not key.isdigit() or key!=str(int(key)):
            raise ValueError('Expected canonical raw-ID strings')
        integer(int(key),0,UNKNOWN-1)
        if not isinstance(value,str) or not value or len(value)>128:raise ValueError('Invalid tile biome name')
    return dict(names)


def make_tile(context, bounds, y, values, *, biome_names=None):
    ctx=validate_context(context);provider_id(ctx);x,z,hx,hz=_bounds(bounds);_height(ctx,y)
    if not isinstance(values,list) or len(values)!=(hx-x)*(hz-z):
        raise ValueError('Tile must contain every logical block, row-major Z then X')
    numbers=[UNKNOWN if v is None else integer(v,0,UNKNOWN-1) for v in values]
    raw=struct.pack('<'+'I'*len(numbers),*numbers)
    names=_names({} if biome_names is None else biome_names)
    body=dict(revision=REVISION,context=ctx,bounds=list(bounds),y=y,biome_names=names,
              codec='zlib-base64-u32le-zx-v1',data=base64.b64encode(zlib.compress(raw)).decode())
    return dict(body,tile_id=digest(body))


def decode_tile(tile):
    fields={'revision','context','bounds','y','biome_names','codec','data','tile_id'}
    if not isinstance(tile,dict) or set(tile)!=fields or tile['revision']!=REVISION:
        raise ValueError('Invalid tile schema')
    ctx=validate_context(tile['context']);provider_id(ctx);x,z,hx,hz=_bounds(tile['bounds']);_height(ctx,tile['y'])
    if tile['codec']!='zlib-base64-u32le-zx-v1' or not isinstance(tile['data'],str) or len(tile['data'])>32768:
        raise ValueError('Invalid tile codec/payload')
    if tile['tile_id']!=digest({k:v for k,v in tile.items() if k!='tile_id'}):
        raise ValueError('Tile checksum mismatch')
    _names(tile['biome_names'])
    expected=(hx-x)*(hz-z)*4
    try:
        compressed=base64.b64decode(tile['data'],validate=True);d=zlib.decompressobj()
        raw=d.decompress(compressed,expected+1)
        if len(raw)!=expected or d.unconsumed_tail or d.unused_data or not d.eof:
            raise ValueError('Tile compressed length/trailing data mismatch')
    except (ValueError,zlib.error) as exc:
        raise ValueError('Corrupt biome tile') from exc
    values=struct.unpack('<'+'I'*(expected//4),raw)
    return tuple(None if v==UNKNOWN else v for v in values)


def sample_tile(context,bounds,y,sampler,*,max_blocks=MAX_BLOCKS):
    """Offline explicit bounded work only; caller owns provider and cancellation."""
    x,z,hx,hz=_bounds(bounds,cap=min(integer(max_blocks,1,MAX_BLOCKS),MAX_BLOCKS))
    ctx=validate_context(context);provider_id(ctx);_height(ctx,y)
    return make_tile(ctx,bounds,y,[sampler(px,y,pz) for pz in range(z,hz) for px in range(x,hx)])


def evaluate_scope(tiles,context,bounds,y,any_ids,*,anchor=None,radius=None,max_blocks=65536):
    """Three-valued presence for precisely a box or box/closed-circle intersection.

    Positive observations suffice for presence. Absence requires all requested
    blocks known under the SAME provider identity/Y. Conflicting overlap is an
    integrity failure, never last-writer-wins. This cannot certify another provider.
    """
    ctx=validate_context(context);pid=provider_id(ctx);_height(ctx,y)
    x,z,hx,hz=_bounds(bounds,cap=integer(max_blocks,1,65536))
    if not isinstance(any_ids,list) or not 1<=len(any_ids)<=256:
        raise ValueError('Expected nonempty bounded raw-ID alternatives')
    ids=frozenset(integer(v,0,UNKNOWN-1) for v in any_ids)
    if (anchor is None)!=(radius is None):raise ValueError('Circle requires anchor and radius')
    if anchor is not None:
        if not isinstance(anchor,list) or len(anchor)!=2:raise ValueError('Invalid circle anchor')
        ax,az=[integer(v,-30_000_000,30_000_000) for v in anchor];integer(radius,0,8192)
    else:ax=az=0
    if not isinstance(tiles,list) or len(tiles)>256:raise ValueError('Tile count cap')
    known={};proof_tiles=[]
    for tile in tiles:
        values=decode_tile(tile)
        if provider_id(tile['context'])!=pid or tile['y']!=y:
            raise ValueError('Mismatched provider/identity/height')
        tx,tz,thx,thz=tile['bounds'];proof_tiles.append(tile['tile_id'])
        for pz in range(max(z,tz),min(hz,thz)):
            for px in range(max(x,tx),min(hx,thx)):
                v=values[(pz-tz)*(thx-tx)+(px-tx)]
                if v is None:continue
                old=known.get((px,pz))
                if old is not None and old!=v:raise ValueError('Conflicting tile evidence')
                known[px,pz]=v
    total=covered=0;witness=None
    for pz in range(z,hz):
        for px in range(x,hx):
            if radius is not None and (px-ax)**2+(pz-az)**2>radius**2:continue
            total+=1;v=known.get((px,pz))
            if v is not None:
                covered+=1
                if v in ids and witness is None:witness=[px,y,pz,v]
    if total==0:raise ValueError('Requested scope has no logical blocks')
    status='present' if witness else ('absent' if covered==total else 'unknown')
    proof=dict(revision='catalog-biome-proof-v1',provider_id=pid,bounds=list(bounds),y=y,
        anchor=anchor,radius=radius,any_ids=sorted(ids),tile_ids=sorted(set(proof_tiles)),
        status=status,covered_blocks=covered,total_blocks=total,witness=witness)
    return dict(proof,proof_id=digest(proof))
