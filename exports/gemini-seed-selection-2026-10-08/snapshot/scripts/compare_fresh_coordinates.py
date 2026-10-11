"""Repeat captured fresh website point comparisons; never generate website rows locally."""
import json
from pathlib import Path
from seed_search.backend import Backend,biome_name
from seed_search.preflight import save_json
from seed_search.storage import backend_identity


def compare():
    source=json.loads(Path('fixtures/bedrock-26.52/fresh-coordinate-points.json').read_text());out=[]
    for p in source['points']:
        text=Path(p['evidence']).read_text()
        assert f"Y: {p['website_y']}" in text
        with Backend(p['seed']) as b:h,ids=b.heights([[p['x'],p['z']]],1)
        out.append({**p,'local_y':int(h[0]),'local_biome':biome_name(ids[0]),'height_delta':int(h[0])-p['website_y'],'biome_matches':biome_name(ids[0])==p['website_biome']})
    r={'source':source,'backend_identity':backend_identity(),'points':out,'height_mae':sum(abs(p['height_delta']) for p in out)/len(out),'height_max_error':max(abs(p['height_delta']) for p in out),'biome_matches':sum(p['biome_matches'] for p in out)}
    save_json('runs/sweep-readiness/fresh-coordinate-comparison.json',r)
    return r


if __name__=='__main__':
    r=compare();print(json.dumps({k:r[k] for k in ('height_mae','height_max_error','biome_matches')},indent=2))
