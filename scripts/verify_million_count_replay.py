"""Independently replay retained extrema and positive example starts with full64."""
from __future__ import annotations
import json
from pathlib import Path
import sqlite3
from seed_search.backend import Backend
from seed_search.realm.bounds import square, nether_square, native_bounds, contains
from reanalyze_million_count_feasibility import distinct_count

ROOT=Path('runs/count-bits-2026-10-11')

def main():
    report=json.loads((ROOT/'million-count-feasibility.json').read_text())
    db=sqlite3.connect(Path(report['source_database']).as_uri()+'?mode=ro',uri=True)
    cases={}
    for name,item in report['retained_positive_maxima'].items():
        e=item['example']; key=(e['seed'],tuple(e['stronghold']))
        cases.setdefault(key,set()).add(name)
    for profile in report['profile_results'].values():
        for e in profile['examples'].values():
            key=(e['seed'],tuple(e['stronghold']))
            cases.setdefault(key,set()).update(n for n,v in e['counts'].items() if v>0)
    checks=[];biome_checks=[]
    try:
        for (seed,center),names in cases.items():
            cid=f'{seed}:{center[0]}:{center[1]}'
            r=json.loads(db.execute('SELECT result FROM candidates WHERE id=?',(cid,)).fetchone()[0])
            ow=square(center,1536);ne=nether_square(center,896)
            assert r['bounds']['overworld']==list(square(center,2688))
            assert r['bounds']['final_nether']==[float(v) for v in nether_square(center,1024)]
            with Backend(seed) as native:
                for name in sorted(names):
                    section='required_nether_structures' if name in ('fortress','bastion') else 'required_structures' if name in ('village','trial_chamber','ancient_city','mineshaft') else 'optional_structures'
                    bounds=ne if name in ('fortress','bastion') else ow
                    old=distinct_count(r[section][name]['predicted_viable'],bounds)
                    fresh=len({p for p in native.structures(name,native_bounds(bounds),True) if contains(p,bounds)})
                    checks.append({'seed':seed,'center':center,'name':name,'retained_count':old,'fresh_full_count':fresh,'equal':old==fresh})
                biomes=r.get('biomes')
                if biomes:
                    for bid,detection in biomes['raw_detections'].items():
                        p=detection['coordinate']
                        if contains((p[0],p[2]),ow):
                            fresh=native.biome(*p)
                            biome_checks.append({'seed':seed,'point':p,'stored_id':int(bid),'fresh_id':fresh,'equal':int(bid)==fresh})
    finally:db.close()
    result={'unique_example_borders':len(cases),'full64_structure_queries':len(checks),
            'biome_witness_queries':len(biome_checks),'structure_checks':checks,'biome_checks':biome_checks,
            'mismatches':[x for x in checks+biome_checks if not x['equal']],
            'scope':'Fresh full64 native prediction, not actual-game certification.'}
    (ROOT/'million-count-replay-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    assert not result['mismatches'],result['mismatches']
    caps={'trial_chamber':16,'village':16,'ancient_city':25,'mineshaft':9216,'ruined_portal':9,'shipwreck':25,'monument':16,'outpost':4}
    for name,cap in caps.items():assert report['retained_positive_maxima'][name]['count']<=cap
    for profile in report['profile_results'].values():
        for scope,seeds in profile['distinct_seeds'].items():assert seeds<=profile['anchors'][scope]
    for histogram in report['retained_count_histograms'].values():assert sum(histogram.values())==report['retained_anchors_in_current_discovery']
    print(json.dumps({k:v for k,v in result.items() if not k.endswith('_checks')},indent=2))

if __name__=='__main__':main()
