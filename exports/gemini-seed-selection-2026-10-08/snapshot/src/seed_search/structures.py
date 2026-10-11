"""Prediction statuses and square eligibility; rejection is never proof of absence."""
import math
from .backend import STRUCTURES

NETHER=('fortress','bastion')
DISPUTED_FAMILIES={'bastion','ancient_city','stronghold'}

def required_types(cfg):
    return tuple(cfg['structures'].get('required_overworld_types',()))+tuple(
        t for t in NETHER if cfg['nether'][t+'_required'])

def required_status(records,cfg):
    required=required_types(cfg)
    if all(records[t]['viable'] for t in required):
        return 'predicted_both_required' if set(required)==set(NETHER) else 'predicted_required_structures'
    # Missing Strongholds are unresolved because this enumerator is incomplete.
    if all(records[t]['raw'] or t=='stronghold' for t in required):return 'disputed_required_review'
    return 'missing_required_local_prediction'

def square(center, side):
    h=side//2
    return (center[0]-h,center[1]-h,center[0]+h,center[1]+h)

def inside(p, bounds):
    return bounds[0]<=p[0]<=bounds[2] and bounds[1]<=p[1]<=bounds[3]

def nether_center(center):
    if any(v%8 for v in center): raise ValueError('Overworld center must lie on eight-block grid')
    return (center[0]//8,center[1]//8)

def envelope_bounds(cfg):
    lo,hi=cfg['search']['center_axis_bounds_blocks']; h=1504
    ob=(lo-h,lo-h,hi+h,hi+h)
    nb=(math.floor(lo/8)-496,math.floor(lo/8)-496,math.ceil(hi/8)+496,math.ceil(hi/8)+496)
    return ob,nb

def scan_type(backend,cfg,name):
    ob,nb=envelope_bounds(cfg);bounds=nb if name in NETHER else ob
    if cfg.get('optimization',{}).get('combined_structure_scan',False):
        raw,viable=backend.structure_pair(name,bounds)
    else:raw=backend.structures(name,bounds,False);viable=backend.structures(name,bounds)
    return {'raw':raw,'viable':viable,'query_bounds':list(bounds)}

def scan_envelope(backend, cfg, initial=None):
    result=dict(initial or {})
    for name in STRUCTURES:
        if name not in result:result[name]=scan_type(backend,cfg,name)
    return result

def possible_required_centers(scans,cfg,center_box):
    """Intersection of axis-aligned center windows, with exact eight-block snapping.

    False means no *predicted* joint placement, never proof of absent Stronghold.
    Fortress center limits are converted to Overworld units exactly once.
    """
    required=required_types(cfg);boxes=[center_box]
    for typ in required:
        scale,half=(8,496) if typ in NETHER else (1,1504)
        windows=[((p[0]-half)*scale,(p[1]-half)*scale,(p[0]+half)*scale,(p[1]+half)*scale)
                 for p in scans[typ]['raw']]
        next_boxes=[]
        for a in boxes:
            for b in windows:
                x0=max(a[0],b[0]);z0=max(a[1],b[1]);x1=min(a[2],b[2]);z1=min(a[3],b[3])
                if math.ceil(x0/8)*8<=x1 and math.ceil(z0/8)*8<=z1:
                    next_boxes.append((x0,z0,x1,z1))
        boxes=next_boxes
        if not boxes:return False
    return True

def at_center(scans,center,cfg):
    nc=nether_center(center); result={}
    for name in STRUCTURES:
        reference=nc if name in NETHER else center
        bounds=square(reference,992 if name in NETHER else 3008)
        raw=[p for p in scans[name]['raw'] if inside(p,bounds)]
        viable=[p for p in scans[name]['viable'] if inside(p,bounds)]
        rejected=[p for p in raw if p not in viable]
        nearest=min(viable,key=lambda p:(math.dist(reference,p),p)) if viable else None
        required=name in required_types(cfg)
        radius={'bastion':48,'fortress':5,'trial_chamber':25,'ruined_portal':21,'outpost':12}.get(name,0)
        near_border=[list(p) for p in raw if min(p[0]-bounds[0],bounds[2]-p[0],p[1]-bounds[1],bounds[3]-p[1])<=radius+32]
        result[name]={'dimension':'nether' if name in NETHER else 'overworld','bounds':list(bounds),
                      'raw':[list(p) for p in raw],'viable':[list(p) for p in viable],
                      'rejected_raw_review':[list(p) for p in rejected],
                      'nearest_viable':list(nearest) if nearest else None,
                      'distance':math.dist(reference,nearest) if nearest else None,
                      'status':'predicted_viable' if viable else 'disputed_raw' if rejected else 'no_local_start_found',
                      'completeness':'unknown' if name=='stronghold' else 'bounded_local_model_scan',
                      'chunkbase_checked':False,'chunkbase_markers':[], 'actual_minecraft':None,
                      'accessible_footprint':'unknown','starts_near_border':near_border,
                      'review_required':required or bool(rejected) or bool(near_border) or name=='stronghold',
                      'required':required,'confirmed_required_eligible':False}
    return result,required_status(result,cfg)
