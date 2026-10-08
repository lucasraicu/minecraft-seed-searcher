"""Prove a full unchanged report refresh performs no terrain query or redraw."""
import argparse
import hashlib
import json
import time
from pathlib import Path
from unittest.mock import patch
from seed_search.backend import Backend
from seed_search.reports import export_search
from seed_search.storage import Store


def maps(run):
    return {str(p.relative_to(run/'shortlist')):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (run/'shortlist').rglob('*.png')}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();run=Path(a.run)
    store=Store(run,resume=True)
    try:
        before=maps(run);assert before
        def forbidden(*args,**kwargs):raise AssertionError('Unnecessary native map query or redraw')
        started=time.perf_counter()
        with patch.object(Backend,'heights',forbidden),patch.object(Backend,'biome',forbidden),patch('matplotlib.pyplot.subplots',forbidden):
            summary=export_search(run,store.results(),store.identity['config'],store.identity['config_sha256'],store.identity)
        elapsed=time.perf_counter()-started
        after=maps(run);assert after==before
        assert len(after)==2*sum(summary['list_counts'].values())
        result={'passed':True,'map_count':len(after),'map_hashes_unchanged':True,
                'native_height_queries':0,'native_biome_queries':0,'plot_redraws':0,
                'wall_seconds':elapsed,'map_generation_seconds':summary['map_generation_seconds'],
                'limits':'Unchanged candidates/configuration/predictor/renderer only; changed reviews or corrupt artifacts invalidate reuse.'}
        Path(a.output).write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
    finally:store.close()
