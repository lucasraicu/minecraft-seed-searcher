from seed_search.catalog.harvest import HarvestQueue,AutomationLedger
from seed_search.catalog.retention import automation_objectives_v3
from seed_search.catalog.reserve_policy import contract_id
from test_automation_ledger import make_receipt


def test_actual_v3_two_k_ledger_fullsort_replay_and_partition_order(tmp_path):
    objectives=['v3.near:biome.exact.forest:2048:origin','v3.near:biome.exact.desert:4096:recommended']
    expected={oid:[] for oid in objectives}
    stream=[]
    for i in range(103):
        receipt=make_receipt(i);wid=receipt['world_id'];offers=[]
        for j,oid in enumerate(objectives):
            rank=[(i*(17+2*j))%47,wid,i%3]
            offers.append(dict(objective_id=oid,rank=rank,member=dict(world_id=wid)))
            expected[oid].append((rank,wid))
        stream.append((receipt,offers))
    for partition,rows in enumerate((stream,list(reversed(stream)))):
        with HarvestQueue(tmp_path/str(partition)) as queue:
            ledger=AutomationLedger(queue,policy_revision='a'*64,objectives=automation_objectives_v3(),policy_contract=contract_id())
            for receipt,offers in rows[:51]:ledger.offer(receipt,offers)
            ledger=AutomationLedger(queue,policy_revision='a'*64,objectives=automation_objectives_v3(),policy_contract=contract_id())
            for receipt,offers in rows[51:]+rows[:9]:ledger.offer(receipt,offers)
            for oid in objectives:
                actual=[(row['rank'],row['world_id']) for row in ledger.members() if row['objective_id']==oid]
                assert actual==sorted(expected[oid],key=lambda r:tuple(r[0]))[:40]
                assert len(actual[:20])==len(actual[20:])==20
