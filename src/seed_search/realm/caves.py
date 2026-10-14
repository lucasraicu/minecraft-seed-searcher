"""Manually invoked cave inventory. Never affects baseline or terrain scores."""
from __future__ import annotations

import math
from ..seeds import parse_seed
from .bounds import square

FAMILIES = ('lush_caves', 'dripstone_caves', 'sulfur_caves', 'deep_dark')


def verify_caves(seed, stronghold, cfg, adapter=None, predictor=None):
    seed = str(parse_seed(seed))
    sx,sz = stronghold
    if any(isinstance(v,bool) or not isinstance(v,int) for v in stronghold):
        raise ValueError('Stronghold coordinates must be integers')
    options = cfg.get('manual_caves', cfg.get('caves', {}))
    spacing = options.get('spacing', options.get('spacing_blocks', 128))
    budget = options.get('sample_budget', options.get('maximum_samples', 4096))
    ys = (0,-16,-32,-48)
    limit = options.get('max_refinement_regions', 4)
    if (isinstance(spacing,bool) or not isinstance(spacing,int) or spacing<1 or
        isinstance(budget,bool) or not isinstance(budget,int) or budget<1 or
        isinstance(limit,bool) or not isinstance(limit,int) or limit<0):
        raise ValueError('Positive manual cave spacing and sample budget required')
    bounds = square((sx,sz), (cfg.get('deployment') or {}).get('overworld_side_blocks', 1536))
    count_x = len(range(bounds[0], bounds[2], spacing))
    count_z = len(range(bounds[1], bounds[3], spacing))
    requested_samples = count_x * count_z * len(ys)
    result = {'seed':seed, 'stronghold':list(stronghold), 'bounds':list(bounds), 'half_open':True,
              'manual_only':True, 'distance_reference_y':0, 'score_effect':None, 'initial_y_levels':list(ys), 'spacing':spacing,
              'sample_budget':budget, 'requested_samples':requested_samples, 'families':{}, 'errors':[], 'status':'UNSUPPORTED'}
    if requested_samples > budget:
        result['reason'] = 'Requested coarse grid exceeds explicit sample budget; increase spacing or budget'
        result['sampled_points'] = 0
        return result
    points = [(x,y,z) for z in range(bounds[1],bounds[3],spacing)
              for x in range(bounds[0],bounds[2],spacing) for y in ys]
    observations = []
    actual = False
    if adapter is not None and hasattr(adapter,'sample_caves'):
        try:
            raw = adapter.sample_caves(seed,bounds,spacing,ys)
        except Exception as error:
            raw = {'status':'FAILED', 'actual':False,
                   'reason':'Manual cave provider failed; no absence inferred'}
            result['errors'].append({'stage':'initial','type':type(error).__name__,'message':str(error)})
        actual = raw.get('actual') is True
        observations = raw.get('observations',[])
        result['source'] = raw.get('source')
        result['evidence'] = raw
        result['status'] = raw.get('status', 'PARTIAL')
    elif predictor is not None:
        from ..backend import biome_name
        if hasattr(predictor,'seed') and str(predictor.seed)!=seed:
            raise ValueError('Cave predictor seed differs')
        result['source'] = 'MC_26_50 predictor for target Bedrock 26.52'
        try:
            values = predictor.biome_points(points)
            if len(values)!=len(points):
                raise ValueError('Cave provider returned incomplete sample count')
            observations = [{'x':x,'y':y,'z':z,'biome':v if isinstance(v,str) else biome_name(int(v))}
                            for (x,y,z),v in zip(points,values)]
            result['status'] = 'PREDICTED'
        except Exception as error:
            result['status']='FAILED'
            result['errors'].append({'stage':'initial','type':type(error).__name__,'message':str(error)})
    else:
        result['reason'] = 'No supported underground biome provider supplied'
    requested = set(points)
    refinements = []
    remaining = budget-len(points)
    fine = max(1, spacing//2)
    positive = [row for row in observations if (row['x'],row['y'],row['z']) in requested
                and not row.get('error') and str(row.get('biome','')).removeprefix('minecraft:') in FAMILIES]
    observed_points = {(row['x'],row['y'],row['z']) for row in observations
                       if not row.get('error') and isinstance(row.get('biome'),str) and row['biome']}
    uncertain = [{'x':x,'y':y,'z':z} for x,y,z in points if (x,y,z) not in observed_points]
    triggers = [(row,'positive') for row in positive]+[(row,'uncertain') for row in uncertain]
    refined_centers = set()
    for row,trigger in triggers if (actual or predictor is not None) and result['status'] not in ('FAILED','UNSUPPORTED') else []:
        if len(refinements)>=limit or fine==spacing:
            break
        x,z = row['x'],row['z']
        if (x,z) in refined_centers:
            continue
        local = (max(bounds[0],x-fine),max(bounds[1],z-fine),min(bounds[2],x+fine+1),min(bounds[3],z+fine+1))
        extra = [(xx,y,zz) for zz in range(local[1],local[3],fine)
                 for xx in range(local[0],local[2],fine) for y in ys]
        fresh = [p for p in extra if p not in requested]
        if len(extra)>remaining or not fresh:
            continue
        requested.update(extra)
        remaining-=len(extra)
        refined_centers.add((x,z))
        region={'bounds':list(local),'spacing':fine,'samples':len(extra),'trigger':trigger}
        refinements.append(region)
        try:
            if actual:
                refined = adapter.sample_caves(seed,local,fine,ys)
                if not refined.get('actual') or refined.get('source')!=result.get('source'):
                    raise ValueError('Cave refinement lacks matching actual provenance')
                observations.extend(refined.get('observations',[]))
            elif predictor is not None:
                values = predictor.biome_points(extra)
                if len(values)!=len(extra):
                    raise ValueError('Cave refinement returned incomplete sample count')
                observations.extend({'x':xx,'y':y,'z':zz,'biome':v if isinstance(v,str) else biome_name(int(v))}
                                    for (xx,y,zz),v in zip(extra,values))
        except Exception as error:
            region['status']='FAILED'
            result['status']='PARTIAL'
            result['errors'].append({'stage':'refinement','bounds':list(local),'type':type(error).__name__,'message':str(error)})
    unique = {}
    for row in observations:
        point = (row['x'],row['y'],row['z'])
        previous = unique.get(point)
        # A missing overlap in a later refinement must not erase a previously
        # observed biome at the same coordinate.
        if previous and not previous.get('error') and isinstance(previous.get('biome'),str) and previous['biome']:
            if row.get('error') or not isinstance(row.get('biome'),str) or not row['biome']:
                continue
        unique[point] = row
    valid = [row for p,row in unique.items() if p in requested and not row.get('error')
             and isinstance(row.get('biome'),str) and row['biome']]
    valid_points = {(row['x'],row['y'],row['z']) for row in valid}
    result['sampled_points'] = len(valid)
    result['coverage'] = {'complete_volume':False, 'grid_complete':all(p in valid_points for p in points),
                          'sample_fraction':len(valid)/len(requested) if requested else 0}
    for family in FAMILIES:
        hits = []
        for row in valid:
            if str(row.get('biome','')).removeprefix('minecraft:')!=family:
                continue
            x,y,z = row['x'],row['y'],row['z']
            hits.append({**row, 'horizontal_distance':math.hypot(x-sx,z-sz),
                         'distance_3d':math.sqrt((x-sx)**2+y*y+(z-sz)**2),
                         'evidence_status':'VERIFIED' if actual else 'PREDICTED'})
        result['families'][family] = {'observations':hits, 'informational':family=='deep_dark',
                                      'status':('VERIFIED' if actual else 'PREDICTED') if hits else 'UNKNOWN'}
    result['refinement'] = {'performed':bool(refinements), 'regions':refinements, 'remaining_budget':remaining,
                            'reason':'Positive and uncertain neighborhoods refined under explicit budget; sparse negatives remain unknown'}
    return result
