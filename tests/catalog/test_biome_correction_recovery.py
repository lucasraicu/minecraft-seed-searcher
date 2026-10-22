from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.reindex_catalog_biomes import merge_offers
from seed_search.catalog.harvest import HarvestQueue,AutomationLedger,_validate_rank
from seed_search.catalog.models import identity,world_id
from seed_search.catalog.registry import digest
from seed_search.catalog.artifacts import ArtifactStore


def test_deferred_merge_matches_real_ledger_and_independent_full_sort(tmp_path):
    capacities={'a':8,'b':4};pending=[];all_offers=[]
    with HarvestQueue(tmp_path/'queue') as queue:
        ledger=AutomationLedger(queue,policy_revision='a'*64,objectives=capacities)
        for n in range(103):
            ident=identity(str(n+1),model_id='MC_26_50',native_sha256='a'*64,source_sha256='b'*64);wid=world_id(ident)
            receipt=dict(world_id=wid,identity=ident,observation_id=digest(ident),artifact={},evaluations=[],replay={})
            member=dict(world_id=wid,source_observation_id=receipt['observation_id'])
            offers=[dict(objective_id='a',rank=[{'decimal':str(n%13)},wid],member=member),dict(objective_id='b',rank=[{'numerator':102-n,'denominator':3},wid],member=member)]
            # Duplicate world offers with a worse rank must not create another slot.
            offers.append(dict(objective_id='a',rank=[999,wid],member=member))
            all_offers.extend(dict(off,world_id=wid) for off in offers)
            if n==3:existing=ledger.members()
            ledger.offer(receipt,offers)
            if n>=3:pending.append((wid,offers))
        expected=ledger.members();actual=merge_offers(existing,pending,capacities)
        assert actual==expected
        # Reapplying the durable batches is idempotent.
        assert merge_offers(actual,pending,capacities)==expected
        independent=[]
        for oid,capacity in sorted(capacities.items()):
            best={}
            for off in all_offers:
                if off['objective_id']!=oid:continue
                wid=off['world_id'];old=best.get(wid)
                if old is None or _validate_rank(off['rank'])<_validate_rank(old['rank']):best[wid]=off
            independent.extend(sorted(best.values(),key=lambda m:(_validate_rank(m['rank']),m['world_id']))[:capacity])
        assert actual==independent
        artifacts=ArtifactStore(tmp_path/'cas')
        ref=artifacts.put_json(dict(revision='catalog-correction-offers-v1',offers=pending[-1][1]),compression_level=1)
        assert artifacts.get_json(ref)['offers']==pending[-1][1]


def test_legacy_grid_eligibility_matches_existing_policy():
    from scripts.reindex_catalog_biomes import legacy_grid_rows
    from test_expansion_storage import observation
    from seed_search.catalog.summaries import summarize_v2
    from seed_search.catalog.retention import retain
    o=observation();rows=summarize_v2(o)
    eligible=[r['legacy'] for r in rows if 'recommended' in r['anchor_modes'] and r['legacy'].get('revision')=='catalog-summary-v1']
    extra=[dict(anchor_modes=['recommended'],legacy={'revision':'catalog-summary-v2'}),dict(anchor_modes=['world_spawn_estimated'],legacy={'revision':'catalog-summary-v1'})]
    assert legacy_grid_rows(rows+extra)==eligible
    assert retain(legacy_grid_rows(rows+extra),[o['identity']])==retain(eligible,[o['identity']])
