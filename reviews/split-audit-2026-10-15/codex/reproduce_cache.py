import contextlib,io,json,runpy,tempfile
from pathlib import Path
root=Path.cwd();out=root/'reviews/split-audit-2026-10-15/codex'
p=root/'reviews/split-audit-2026-10-15/gemini/probes/store/probe_candidate_cache_invalidation.py'
stream=io.StringIO()
with contextlib.redirect_stdout(stream),tempfile.TemporaryDirectory() as td:
 f=runpy.run_path(str(p));result=f['test_stale_candidate_cache_on_in_place_update'](Path(td))
assert result
file=out/'reproductions.json';rows=json.loads(file.read_text());rows.append(dict(id='G-STORE-01',status='completed',result=result,stdout=stream.getvalue()));file.write_text(json.dumps(rows,indent=2)+'\n')
print(stream.getvalue())
