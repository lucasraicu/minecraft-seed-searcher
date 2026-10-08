"""Recorded actual website review, kept separate from local and game evidence."""
import copy
import json
from pathlib import Path
from .seeds import parse_seed
from .structures import inside,required_types
from .preflight import save_json


def landscape_review_fields(kind):
    if kind=='ocean_island':return ('island_separated','ocean_setting','nearby_wood_abundant','buildability')
    if kind=='mountain_basin':return ('dry_flat_floor','mountain_setting','nearby_wood_abundant','buildability')
    if kind!='enclosed_island':raise ValueError('Unsupported reviewed landscape type')
    return ('island_separated','mountain_setting','external_wood_abundant','buildability')


def validate_review(r,cfg=None):
    if r.get('source_kind')!='fresh_chunkbase_browser_UI' or r.get('version')!='Bedrock 26.50 - 26.52':
        raise ValueError('Fresh reviews require actual matching-version Chunkbase browser UI provenance')
    if r.get('source_url')!='https://www.chunkbase.com/apps/seed-map' or not r.get('recorded_at') or not r.get('browser_evidence'):
        raise ValueError('Review requires date, source link and browser evidence references')
    parse_seed(r['seed'])
    if len(r['center'])!=2 or any(not isinstance(v,int) or isinstance(v,bool) or v%8 for v in r['center']):raise ValueError('Review requires exact eight-block center')
    if r.get('terrain_enabled') is not True or set(r.get('dimensions_checked',[]))!={'overworld','nether'}:
        raise ValueError('Review requires Terrain enabled and both dimensions checked')
    for name in landscape_review_fields(r.get('landscape_type','enclosed_island')):
        if r.get(name) is not None and not isinstance(r.get(name),bool):raise ValueError(f'Invalid review field {name}')
    needed=required_types(cfg) if cfg is not None else ('fortress','bastion') if 'landscape_type' not in r else ('fortress','stronghold')
    for t in needed:
        if t not in r.get('structures',{}):raise ValueError(f'Review must record required {t} markers')
    for t,markers in r.get('structures',{}).items():
        if t not in ('fortress','bastion','stronghold'):raise ValueError('Unsupported reviewed structure')
        for p in markers:
            if len(p)!=2 or any(not isinstance(v,int) or isinstance(v,bool) for v in p):raise ValueError('Website markers require exact integer X/Z')
    return r


def apply_review(c,reviews,cfg,config_hash):
    c=copy.deepcopy(c)
    found=[r for r in reviews if r['seed']==c['seed'] and r['center']==c['center'] and r['config_sha256']==config_hash and r.get('landscape_type','enclosed_island')==c.get('landscape_type','enclosed_island')]
    if not found:return c
    r=validate_review(found[-1],cfg);c['chunkbase_checked']=True;c['chunkbase_review']=r
    for t,markers in r['structures'].items():
        if t not in c['structures']:raise ValueError(f'Unsupported reviewed structure type {t}')
        row=c['structures'][t];row['chunkbase_checked']=True;row['chunkbase_markers']=markers
        row['chunkbase_markers_inside']=[p for p in markers if inside(p,row['bounds'])]
        row['confirmed_required_eligible']=bool(row['chunkbase_markers_inside']) if t in required_types(cfg) else False
        row['confirmation_scope']='website_marker_only; accessible footprint remains unknown'
    requirements=[r.get(k) is True for k in landscape_review_fields(c.get('landscape_type','enclosed_island'))]
    required=all(c['structures'][t]['confirmed_required_eligible'] for t in required_types(cfg))
    c['selection_status']='chunkbase_supported_candidate' if all(requirements) and required else 'chunkbase_checked_near_miss_or_unresolved'
    c['remaining_review']=['Optional Minecraft check of thin bridges, actual trees, structure access/footprints and portal arrival'] if c['selection_status']=='chunkbase_supported_candidate' else ['Fresh Chunkbase review did not establish every selection requirement; see review notes']
    return c


def import_review(run,path,cfg=None):
    data=json.loads(Path(path).read_text()); data=data if isinstance(data,list) else [data]
    for r in data:validate_review(r,cfg)
    dest=Path(run)/'reviews.json';existing=json.loads(dest.read_text()) if dest.exists() else []
    for r in data:
        existing=[v for v in existing if (v['seed'],v['center'],v['config_sha256'],v.get('landscape_type','enclosed_island'))!=(r['seed'],r['center'],r['config_sha256'],r.get('landscape_type','enclosed_island'))]
        existing.append(r)
    save_json(dest,existing)
