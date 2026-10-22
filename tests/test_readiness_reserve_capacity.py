"""Full production 100-capacity synthetic ranking/persistence acceptance."""
import json
import sqlite3
from test_personal_reserve import record,oracle
from seed_search.realm.top_tracker import Top50Tracker
from seed_search.realm.reserve import selection_policy


def test_full100_distinct_retained_candidates_durable_primary_reserve_and_cutoff(tmp_path):
 policy=selection_policy(50);tracker=Top50Tracker(capacity=100,winner_limit=50,reserve_policy=policy)
 rows=[record(i,(i*17)%83,i%4)for i in range(300)]+[record(3,999),record(3,998)]
 for i,row in enumerate(rows):
  tracker.observe(row)
  if i<99:assert tracker.cutoff_score()is None
 expected=oracle(rows)[:100];assert tracker.top_records()==expected
 assert tracker.cutoff_score()==expected[-1]['anchors'][0]['baseline_score_observed']
 tracker.save_to_json(str(tmp_path/'top50.json'))
 primary=json.loads((tmp_path/'top50.json').read_text());reserve=json.loads((tmp_path/'reserves.json').read_text())
 assert primary==expected[:50]and reserve==expected[50:]and len({r['seed']for r in primary+reserve})==100
 with sqlite3.connect(tmp_path/'capacity.sqlite')as db:
  tracker.flush(db);assert db.execute('select count(*)from top_candidates').fetchone()[0]==100
 # Simulate canonical checkpoint recovery by offering retained records in reverse.
 restored=Top50Tracker(capacity=100,winner_limit=50,reserve_policy=policy)
 for row in reversed(primary+reserve):restored.observe(row)
 assert restored.top_records()==expected and restored.cutoff_score()==tracker.cutoff_score()
 # Promotion selects the best retained reserve after a certified primary fails.
 remaining=primary[1:]+reserve
 promoted=Top50Tracker(capacity=100,winner_limit=50,reserve_policy=policy)
 for row in remaining:promoted.observe(row)
 assert promoted.top_records()[:50]==expected[1:51]
