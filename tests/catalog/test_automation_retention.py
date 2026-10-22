"""Resumable observations must not lose membership because a content hash changes."""
import copy
from seed_search.catalog.models import empty_observation_v2,identity,world_id
from seed_search.catalog.registry import digest
from seed_search.catalog.summaries import summarize_v2
from seed_search.catalog.retention import automation_offers,automation_objectives
from seed_search.catalog.harvest import HarvestQueue,AutomationLedger


def test_same_facts_new_checkpoint_hash_refreshes_all_winners(tmp_path):
    obs=empty_observation_v2(identity('123',model_id='MC_26_50',native_sha256='a'*64,source_sha256='b'*64))
    obs['structures']={'structure.village':[[0,0]]}
    obs['coverage']['structure.village']=dict(status='complete',bounds=obs['bounds']['overworld'],method_id='predictor_viable_starts_v1')
    with HarvestQueue(tmp_path) as q:
        ledger=AutomationLedger(q,policy_revision='c'*64,objectives=automation_objectives())
        previous=None
        for phase in (1,2):
            obs['metrics']['phase']=phase;oid=digest(obs);wid=world_id(obs['identity'])
            offers=automation_offers(obs,summarize_v2(obs),[])
            ranks={o['objective_id']:o['rank'] for o in offers}
            if previous is not None:assert ranks==previous
            previous=ranks
            ledger.offer(dict(world_id=wid,identity=obs['identity'],observation_id=oid,artifact={},evaluations=[],replay={}),offers)
            assert all(m['member']['source_observation_id']==oid for m in ledger.members())
        assert ledger.population()==1 and ledger.generation()==2
