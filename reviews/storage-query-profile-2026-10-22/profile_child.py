from pathlib import Path
import cProfile,json,sys,time
ROOT=Path('/Users/lucasraicu/Downloads/minecraft-seed-searcher');sys.path.insert(0,str(ROOT/'src'))
from seed_search.catalog.harvest_native import _child
from instrument import Probe,stats_json
checkpoint=Path(sys.argv[1]);out=Path(sys.argv[2]);probe=Probe().start();profile=cProfile.Profile();wall=time.monotonic();cpu=time.process_time();code=1
try:
 profile.enable();code=_child(checkpoint)
finally:
 profile.disable();counters=probe.stop();profile.dump_stats(out);out.with_suffix('.json').write_text(json.dumps(dict(exit_code=code,wall_seconds=time.monotonic()-wall,cpu_seconds=time.process_time()-cpu,counters=counters,profile=stats_json(out)),indent=2)+'\n')
raise SystemExit(code)
