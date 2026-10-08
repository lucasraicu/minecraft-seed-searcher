"""Repeat frozen external comparisons without changing either observation source."""
import hashlib
import json
import math
from pathlib import Path
from collections import Counter
from .backend import Backend, STRUCTURES, biome_name
from .preflight import save_json

# Empirical marker conventions from saved matching-version UI rows. Unknown
# variable offsets remain diagnostics; these bounds never determine border access.
CONVENTIONS = {
    'stronghold': ('exact',0), 'mineshaft': ('exact',0),
    'ancient_city': ('exact',0), 'village': ('exact',0),
    'shipwreck': ('exact',0), 'monument': ('exact',0),
    'outpost': ('chunk_center_vs_marker',12),
    'fortress': ('chunk_center_vs_marker',5),
    'trial_chamber': ('variable_room_marker',25),
    'ruined_portal': ('variable_portal_marker',21),
    'bastion': ('variable_rotated_piece_marker',48),
}

def correspond(name, marker, positions):
    convention,radius=CONVENTIONS[name]
    delta={'outpost':{(-8,-8)},'fortress':{(-3,-3)},'trial_chamber':{(-1,-1),(-1,17),(17,-1),(17,17)}}.get(name)
    matches=[p for p in positions if ((p[0]-marker[0],p[1]-marker[1]) in delta if delta is not None else math.dist(marker,p)<=radius)]
    return {'convention':convention,'diagnostic_radius':radius,
            'possible_starts':[list(p) for p in matches],
            'status':'unique' if len(matches)==1 else 'ambiguous' if matches else 'missing'}

def regression(output, fixture='fixtures/bedrock-26.52/chunkbase-accuracy-audit.json', baseline='fixtures/bedrock-26.52/local-regression-baseline.json'):
    f=Path(fixture); e=Path(baseline)
    data=json.loads(f.read_text()); expected=json.loads(e.read_text())
    er={(r['seed'],r['type'],tuple(r['chunkbase_xz'])):r for r in expected['structures']}
    ep={r['id']:r for r in expected['points']}
    rows=[]; points=[]; regressions=[]; reused=0
    for seed in data['seeds']:
        claimed={t:set() for t in STRUCTURES}
        with Backend(seed) as b:
            for q in data['structure_queries']:
                if q['seed']!=seed: continue
                for index,x,z in q['results']:
                    bounds=(x-160,z-160,x+160,z+160)
                    raw=b.structures(q['type'],bounds,False); viable=b.structures(q['type'],bounds)
                    nearest=lambda ps: list(min(ps,key=lambda p:(math.dist((x,z),p),p))) if ps else None
                    rp,vp=nearest(raw),nearest(viable)
                    key=(seed,q['type'],(x,z)); old=er[key]
                    changed=rp!=old['raw'] or vp!=old['viable']
                    if changed: regressions.append({'seed':seed,'type':q['type'],'marker':[x,z],'old':old,'raw':rp,'viable':vp})
                    match=correspond(q['type'],(x,z),viable)
                    if match['status']=='unique':
                        p=tuple(match['possible_starts'][0])
                        if p in claimed[q['type']]: match['status']='reused_start'; reused+=1
                        claimed[q['type']].add(p)
                    rows.append({'seed':seed,'type':q['type'],'marker':[x,z],'raw_nearest':rp,'viable_nearest':vp,
                                 'raw_rejected':rp is not None and tuple(rp) not in viable,
                                 'external_status':'chunkbase_checked','actual_minecraft':None,
                                 'changed_from_baseline':changed,**match})
            for p in data['points']:
                if p['seed']!=seed: continue
                if p['mode']=='surface':
                    h,ids=b.heights([[p['x'],p['z']]],1); height=int(h[0]); name=biome_name(ids[0])
                else:
                    height=None; name=biome_name(b.biome(p['x'],p['sample_y'],p['z'],p['dimension']))
                old=ep[p['id']]
                if name!=old['local_biome'] or (height is not None and height!=old['local_height']):
                    regressions.append({'point':p['id'],'old':old,'biome':name,'height':height})
                points.append({**p,'local_biome':name,'local_height':height,'biome_matches':name==p['chunkbase_comparison_biome'],
                               'height_delta':height-p['chunkbase_marker_y'] if height is not None else None})
    if len(rows)!=880 or len(points)!=159 or len(er)!=880 or len(ep)!=159:
        raise ValueError('Frozen audit must retain all 880 structure and 159 coordinate rows')
    known=[r for r in rows if r['status']!='unique']
    errors=[abs(p['height_delta']) for p in points if p['height_delta'] is not None]
    result={'source_kind':'frozen_actual_website_UI_predictions_not_in_game','target':'Bedrock 26.50 - 26.52',
            'fixture_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'baseline_sha256':hashlib.sha256(e.read_bytes()).hexdigest(),
            'passed':not regressions and reused==0,'unexplained_regressions':regressions,
            'summary':{'structure_rows':len(rows),'point_rows':len(points),'unique_type_correspondences':sum(r['status']=='unique' for r in rows),
                       'known_structure_disagreements':len(known),'reused_starts':reused,
                       'biome_matches':sum(p['biome_matches'] for p in points),'height_mae':sum(errors)/len(errors),'height_max_error':max(errors)},
            'known_disagreements':known,'structures':rows,'points':points,
            'limits':['Capped positive lists do not measure complete recall or false positives.',
                      'Empirical type offsets cannot certify structure footprints or change square-border eligibility.',
                      'Exact local baseline comparisons detect drift even inside diagnostic marker bounds.']}
    save_json(Path(output)/'regression.json',result)
    if not result['passed']: raise ValueError(f'External regression failed: {len(regressions)} changed rows, {reused} reused starts')
    return result
