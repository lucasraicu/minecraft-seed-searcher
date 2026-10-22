"""Tests for public catalog v2 automation membership ledger."""
from decimal import Decimal
from fractions import Fraction
import pytest

from seed_search.catalog.harvest import AutomationLedger, HarvestQueue
from seed_search.catalog.models import identity, world_id


POLICY_A = 'a' * 64
POLICY_B = 'b' * 64


def make_receipt(seed: int, *, model_id: str = 'test', artifact: dict = None, evaluations: list = None, replay: dict = None):
    ident = identity(seed, model_id=model_id, native_sha256='0' * 64, source_sha256='1' * 64)
    wid = world_id(ident)
    return {
        'world_id': wid,
        'identity': ident,
        'observation_id': 'f' * 64,
        'artifact': artifact or {'path': f'obs_{seed}.json'},
        'evaluations': evaluations if evaluations is not None else [{'score': seed}],
        'replay': replay or {'seed': str(seed), 'step': 1}
    }


def test_ledger_initialization_and_immutable_reopen(tmp_path):
    root = tmp_path / 'queue'
    objectives = {'obj_fast': 10, 'obj_rare': 5}
    with HarvestQueue(root) as queue:
        ledger = AutomationLedger(queue, policy_revision=POLICY_A, objectives=objectives)
        assert ledger.generation() == 0
        assert ledger.population() == 0
        assert ledger.retained_worlds() == []
        assert ledger.members() == []

        # Reopening with identical policy and objectives succeeds
        reopened = AutomationLedger(queue, policy_revision=POLICY_A, objectives=objectives)
        assert reopened.generation() == 0

        # Incompatible policy revision rejected
        with pytest.raises(ValueError, match='Incompatible policy revision'):
            AutomationLedger(queue, policy_revision=POLICY_B, objectives=objectives)

        # Incompatible objectives definition rejected
        with pytest.raises(ValueError, match='Incompatible objectives definition'):
            AutomationLedger(queue, policy_revision=POLICY_A, objectives={'obj_fast': 20, 'obj_rare': 5})

        with pytest.raises(ValueError, match='Incompatible objectives definition'):
            AutomationLedger(queue, policy_revision=POLICY_A, objectives={'other': 10})


def test_ledger_policy_and_capacity_limits(tmp_path):
    root = tmp_path / 'queue'
    with HarvestQueue(root) as queue:
        # Invalid policy hash
        with pytest.raises(ValueError, match='Invalid policy_revision'):
            AutomationLedger(queue, policy_revision='short', objectives={'obj': 1})
        with pytest.raises(ValueError, match='Invalid policy_revision'):
            AutomationLedger(queue, policy_revision='G' * 64, objectives={'obj': 1})

        # Invalid capacity bounds
        with pytest.raises(ValueError, match='Invalid capacity'):
            AutomationLedger(queue, policy_revision=POLICY_A, objectives={'obj': 0})
        with pytest.raises(ValueError, match='Invalid capacity'):
            AutomationLedger(queue, policy_revision=POLICY_A, objectives={'obj': -5})
        with pytest.raises(ValueError, match='Invalid capacity'):
            AutomationLedger(queue, policy_revision=POLICY_A, objectives={'obj': 10001})
        with pytest.raises(ValueError, match='Invalid capacity'):
            AutomationLedger(queue, policy_revision=POLICY_A, objectives={'obj': True})

        # Exceeded aggregate capacity limit (105644)
        with pytest.raises(ValueError, match='Aggregate capacity'):
            AutomationLedger(queue, policy_revision=POLICY_A, objectives={f'o{i}': 10000 for i in range(11)})

        # Exceeded max 7027 objectives
        with pytest.raises(ValueError, match='objectives count'):
            AutomationLedger(queue, policy_revision=POLICY_A, objectives={f'o{i}': 1 for i in range(7028)})


def test_independent_full_sort_and_numerical_rank_comparison(tmp_path):
    root = tmp_path / 'queue'
    with HarvestQueue(root) as queue:
        ledger = AutomationLedger(queue, policy_revision=POLICY_A, objectives={'perf': 20})

        # Diverse rank representations
        items = [
            (100, [10], 'int 10'),
            (101, [-5], 'negative int -5'),
            (102, [0], 'zero 0'),
            (103, [{'decimal': '2.0'}], 'decimal 2.0'),
            (104, [{'decimal': '10.0'}], 'decimal 10.0 (must sort AFTER 2.0, not string order!)'),
            (105, [{'decimal': '-1.5'}], 'decimal -1.5'),
            (106, [{'numerator': 1, 'denominator': 2}], 'rational 1/2'),
            (107, [{'decimal': '0.5'}], 'decimal 0.5 (equals rational 1/2)'),
            (108, [{'numerator': 3, 'denominator': 4}], 'rational 3/4'),
            (109, [{'decimal': '0.75'}], 'decimal 0.75 (equals 3/4)'),
            (110, ['alpha'], 'string alpha'),
            (111, ['beta'], 'string beta'),
        ]

        def python_sort_key(rank, wid):
            tuple_keys = []
            for rk in rank:
                if type(rk) is int:
                    tuple_keys.append((0, Fraction(rk, 1)))
                elif isinstance(rk, dict) and 'numerator' in rk:
                    tuple_keys.append((0, Fraction(rk['numerator'], rk['denominator'])))
                elif isinstance(rk, dict) and 'decimal' in rk:
                    tuple_keys.append((0, Fraction(Decimal(rk['decimal']))))
                elif isinstance(rk, str):
                    tuple_keys.append((1, rk))
            return (tuple(tuple_keys), wid)

        receipts_and_offers = []
        for seed, rank, desc in items:
            rc = make_receipt(seed)
            off = [{'objective_id': 'perf', 'rank': rank, 'member': {'world_id': rc['world_id'], 'desc': desc}}]
            receipts_and_offers.append((rc, off, python_sort_key(rank, rc['world_id'])))
            ledger.offer(rc, off)

        members = ledger.members('perf')
        expected_sorted = sorted(receipts_and_offers, key=lambda x: x[2])
        assert len(members) == len(items)
        for idx, (rc, off, _) in enumerate(expected_sorted):
            assert members[idx]['world_id'] == rc['world_id']
            assert members[idx]['rank'] == off[0]['rank']

        # Ensure numerical decimal sorting: 2.0 comes before 10.0
        w_2 = next(m for m in members if m['member']['desc'].startswith('decimal 2.0'))
        w_10 = next(m for m in members if m['member']['desc'].startswith('decimal 10.0'))
        assert members.index(w_2) < members.index(w_10)

        # Ensure rational equals decimal: both 1/2 and 0.5 compare as equal rank
        w_half_rat = next(m for m in members if m['member']['desc'].startswith('rational 1/2'))
        w_half_dec = next(m for m in members if m['member']['desc'].startswith('decimal 0.5'))
        # Equal rank, so tie broken by world_id ascending
        if w_half_rat['world_id'] < w_half_dec['world_id']:
            assert members.index(w_half_rat) < members.index(w_half_dec)
        else:
            assert members.index(w_half_dec) < members.index(w_half_rat)


def test_ties_and_deterministic_ordering(tmp_path):
    root = tmp_path / 'queue'
    with HarvestQueue(root) as queue:
        # Capacity of 2
        ledger = AutomationLedger(queue, policy_revision=POLICY_A, objectives={'tie_test': 2})

        # 4 worlds with IDENTICAL ranks
        seeds = [201, 202, 203, 204]
        receipts = [make_receipt(s) for s in seeds]
        # Sort by world_id ascending to know expected order
        sorted_by_wid = sorted(receipts, key=lambda r: r['world_id'])

        # Submit in reverse order of world_id
        for rc in reversed(sorted_by_wid):
            ledger.offer(rc, [{'objective_id': 'tie_test', 'rank': [100], 'member': {'world_id': rc['world_id']}}])

        # Exactly 2 winners with lowest world_id
        members = ledger.members('tie_test')
        assert len(members) == 2
        assert members[0]['world_id'] == sorted_by_wid[0]['world_id']
        assert members[1]['world_id'] == sorted_by_wid[1]['world_id']
        assert ledger.retained_worlds() == [sorted_by_wid[0]['world_id'], sorted_by_wid[1]['world_id']]
        assert ledger.population() == 4


def test_replay_and_improve_only(tmp_path):
    root = tmp_path / 'queue'
    with HarvestQueue(root) as queue:
        ledger = AutomationLedger(queue, policy_revision=POLICY_A, objectives={'obj': 2})

        rc = make_receipt(301, artifact={'attempt': 1})
        ledger.offer(rc, [{'objective_id': 'obj', 'rank': [50], 'member': {'world_id': rc['world_id'], 'v': 1}}])
        assert ledger.population() == 1
        assert ledger.generation() == 1
        assert ledger.members('obj')[0]['rank'] == [50]
        assert ledger.receipt(rc['world_id'])['artifact'] == {'attempt': 1}

        # Replay: same world, same rank -> population unchanged, generation increments, receipt updated
        rc_replay = make_receipt(301, artifact={'attempt': 2})
        ledger.offer(rc_replay, [{'objective_id': 'obj', 'rank': [50], 'member': {'world_id': rc['world_id'], 'v': 2}}])
        assert ledger.population() == 1
        assert ledger.generation() == 2
        assert ledger.receipt(rc['world_id'])['artifact'] == {'attempt': 2}
        assert ledger.members('obj')[0]['rank'] == [50]

        # Worsening offer: rank [80] is worse than [50] (ascending best) -> improve-only keeps [50]
        rc_worse = make_receipt(301, artifact={'attempt': 3})
        ledger.offer(rc_worse, [{'objective_id': 'obj', 'rank': [80], 'member': {'world_id': rc['world_id'], 'v': 3}}])
        assert ledger.population() == 1
        assert ledger.generation() == 3
        assert ledger.members('obj')[0]['rank'] == [50]

        # Improving offer: rank [20] is better than [50] -> improves to [20]
        rc_better = make_receipt(301, artifact={'attempt': 4})
        ledger.offer(rc_better, [{'objective_id': 'obj', 'rank': [20], 'member': {'world_id': rc['world_id'], 'v': 4}}])
        assert ledger.population() == 1
        assert ledger.generation() == 4
        assert ledger.members('obj')[0]['rank'] == [20]
        assert ledger.members('obj')[0]['member']['v'] == 4


def test_multiobjective_losses_and_retained_worlds(tmp_path):
    root = tmp_path / 'queue'
    with HarvestQueue(root) as queue:
        # obj_a cap 1, obj_b cap 1
        ledger = AutomationLedger(queue, policy_revision=POLICY_A, objectives={'obj_a': 1, 'obj_b': 1})

        # World 1 wins both objectives
        rc1 = make_receipt(401)
        ledger.offer(rc1, [
            {'objective_id': 'obj_a', 'rank': [10], 'member': {'world_id': rc1['world_id']}},
            {'objective_id': 'obj_b', 'rank': [20], 'member': {'world_id': rc1['world_id']}},
        ])
        assert len(ledger.members('obj_a')) == 1
        assert len(ledger.members('obj_b')) == 1
        assert ledger.retained_worlds() == [rc1['world_id']]

        # World 2 beats World 1 in obj_a only
        rc2 = make_receipt(402)
        ledger.offer(rc2, [
            {'objective_id': 'obj_a', 'rank': [5], 'member': {'world_id': rc2['world_id']}},
        ])
        # World 1 lost obj_a, but STILL wins obj_b!
        assert ledger.members('obj_a')[0]['world_id'] == rc2['world_id']
        assert ledger.members('obj_b')[0]['world_id'] == rc1['world_id']
        assert ledger.retained_worlds() == sorted([rc1['world_id'], rc2['world_id']])
        assert ledger.population() == 2

        # World 3 beats World 1 in obj_b
        rc3 = make_receipt(403)
        ledger.offer(rc3, [
            {'objective_id': 'obj_b', 'rank': [2], 'member': {'world_id': rc3['world_id']}},
        ])
        # World 1 now has 0 winning spots
        assert ledger.members('obj_a')[0]['world_id'] == rc2['world_id']
        assert ledger.members('obj_b')[0]['world_id'] == rc3['world_id']
        assert ledger.retained_worlds() == sorted([rc2['world_id'], rc3['world_id']])
        assert rc1['world_id'] not in ledger.retained_worlds()

        # World 1's receipt is still retained for population and replay
        assert ledger.population() == 3
        saved = ledger.receipt(rc1['world_id'])
        assert saved is not None
        assert saved['world_id'] == rc1['world_id']


def test_invalid_inputs_and_rank_validation(tmp_path):
    root = tmp_path / 'queue'
    with HarvestQueue(root) as queue:
        ledger = AutomationLedger(queue, policy_revision=POLICY_A, objectives={'test': 5})
        rc = make_receipt(501)

        # Receipt schema validation
        with pytest.raises(ValueError):
            ledger.offer('not a dict', [])
        bad_rc = dict(rc)
        del bad_rc['replay']
        with pytest.raises(ValueError):
            ledger.offer(bad_rc, [])

        # Non-hex IDs
        bad_wid_rc = dict(rc, world_id='not-hex')
        with pytest.raises(ValueError):
            ledger.offer(bad_wid_rc, [])
        bad_obs_rc = dict(rc, observation_id='not-hex')
        with pytest.raises(ValueError):
            ledger.offer(bad_obs_rc, [])

        # World ID mismatch with identity
        other_rc = make_receipt(502)
        mismatch_rc = dict(rc, world_id=other_rc['world_id'])
        with pytest.raises(ValueError):
            ledger.offer(mismatch_rc, [])

        # Member world_id mismatch
        with pytest.raises(ValueError, match='Member must bind same world_id'):
            ledger.offer(rc, [{'objective_id': 'test', 'rank': [1], 'member': {'world_id': other_rc['world_id']}}])

        # Unregistered objective
        with pytest.raises(ValueError, match='Unregistered objective'):
            ledger.offer(rc, [{'objective_id': 'nonexistent', 'rank': [1], 'member': {'world_id': rc['world_id']}}])

        # Prohibited rank types
        for bad_rank in [
            [True],
            [False],
            [1.5],
            [float('nan')],
            [float('inf')],
            [{'decimal': 'NaN'}],
            [{'decimal': 'Infinity'}],
            [{'decimal': '1e5'}],
            [{'decimal': '+1.5'}],
            [{'decimal': '-0'}],
            [{'decimal': 123}],
            [{'numerator': 1, 'denominator': 0}],
            [{'numerator': 1, 'denominator': -1}],
            [{'numerator': True, 'denominator': 2}],
            [{'numerator': 1, 'denominator': True}],
            [{'arbitrary': 'dict'}],
            'not a list',
        ]:
            with pytest.raises(ValueError):
                ledger.offer(rc, [{'objective_id': 'test', 'rank': bad_rank, 'member': {'world_id': rc['world_id']}}])


def test_transaction_rollback_on_failed_offer(tmp_path):
    root = tmp_path / 'queue'
    with HarvestQueue(root) as queue:
        ledger = AutomationLedger(queue, policy_revision=POLICY_A, objectives={'test': 5})

        rc_valid = make_receipt(601)
        ledger.offer(rc_valid, [{'objective_id': 'test', 'rank': [10], 'member': {'world_id': rc_valid['world_id']}}])
        assert ledger.population() == 1
        assert ledger.generation() == 1

        # Attempt offer with first offer valid, second invalid (unregistered objective)
        rc_failing = make_receipt(602)
        with pytest.raises(ValueError, match='Unregistered objective'):
            ledger.offer(rc_failing, [
                {'objective_id': 'test', 'rank': [5], 'member': {'world_id': rc_failing['world_id']}},
                {'objective_id': 'unknown', 'rank': [1], 'member': {'world_id': rc_failing['world_id']}},
            ])

        # Transaction MUST have rolled back completely
        assert ledger.population() == 1
        assert ledger.generation() == 1
        assert ledger.receipt(rc_failing['world_id']) is None
        assert ledger.retained_worlds() == [rc_valid['world_id']]
        members = ledger.members('test')
        assert len(members) == 1
        assert members[0]['world_id'] == rc_valid['world_id']
        assert members[0]['rank'] == [10]


def test_members_deterministic_ordering_and_filtering(tmp_path):
    root = tmp_path / 'queue'
    with HarvestQueue(root) as queue:
        ledger = AutomationLedger(queue, policy_revision=POLICY_A, objectives={'alpha': 2, 'beta': 2})

        rc1 = make_receipt(701)
        rc2 = make_receipt(702)

        ledger.offer(rc1, [
            {'objective_id': 'beta', 'rank': [5], 'member': {'world_id': rc1['world_id']}},
            {'objective_id': 'alpha', 'rank': [10], 'member': {'world_id': rc1['world_id']}},
        ])
        ledger.offer(rc2, [
            {'objective_id': 'alpha', 'rank': [2], 'member': {'world_id': rc2['world_id']}},
        ])

        # Query all members: ordered by objective_id ascending, then rank ascending, then world_id ascending
        all_members = ledger.members()
        assert len(all_members) == 3
        assert [m['objective_id'] for m in all_members] == ['alpha', 'alpha', 'beta']
        assert all_members[0]['rank'] == [2]
        assert all_members[1]['rank'] == [10]
        assert all_members[2]['rank'] == [5]

        # Query specific objective
        alpha_members = ledger.members('alpha')
        assert len(alpha_members) == 2
        assert alpha_members[0]['world_id'] == rc2['world_id']

        # Query invalid objective raises ValueError
        with pytest.raises(ValueError, match='Unregistered objective'):
            ledger.members('nonexistent')


def test_offer_idempotent_generation_on_identical_replay(tmp_path):
    root = tmp_path / 'queue'
    with HarvestQueue(root) as queue:
        ledger = AutomationLedger(queue, policy_revision=POLICY_A, objectives={'obj_a': 2, 'obj_b': 2})
        assert ledger.generation() == 0
        assert ledger.population() == 0

        rc1 = make_receipt(801)
        offers1 = [
            {'objective_id': 'obj_a', 'rank': [10], 'member': {'world_id': rc1['world_id'], 'v': 1}},
            {'objective_id': 'obj_b', 'rank': [20], 'member': {'world_id': rc1['world_id'], 'v': 1}},
        ]
        ledger.offer(rc1, offers1)
        assert ledger.generation() == 1
        assert ledger.population() == 1
        assert len(ledger.members('obj_a')) == 1
        assert len(ledger.members('obj_b')) == 1

        # Identical replay: same receipt and offers leave generation stable
        ledger.offer(rc1, offers1)
        assert ledger.generation() == 1
        assert ledger.population() == 1
        assert ledger.members('obj_a')[0]['member']['v'] == 1

        # Offer another world that loses obj_a (rank 999 vs cap 2, let's fill cap first)
        rc2 = make_receipt(802)
        offers2 = [
            {'objective_id': 'obj_a', 'rank': [15], 'member': {'world_id': rc2['world_id']}},
        ]
        ledger.offer(rc2, offers2)
        assert ledger.generation() == 2
        assert ledger.population() == 2

        # rc3 offers worse rank than existing 2 winners for obj_a
        rc3 = make_receipt(803)
        offers3 = [
            {'objective_id': 'obj_a', 'rank': [999], 'member': {'world_id': rc3['world_id']}},
        ]
        ledger.offer(rc3, offers3)
        # New evaluated world increases population, bumps generation
        assert ledger.generation() == 3
        assert ledger.population() == 3
        assert rc3['world_id'] not in ledger.retained_worlds()

        # Identical replay of evaluated loser: generation and membership stay stable
        ledger.offer(rc3, offers3)
        assert ledger.generation() == 3
        assert ledger.population() == 3

        # Replay rc1 with changed receipt artifact but same offers: generation bumps
        rc1_artifact_changed = make_receipt(801, artifact={'updated': True})
        ledger.offer(rc1_artifact_changed, offers1)
        assert ledger.generation() == 4
        assert ledger.receipt(rc1['world_id'])['artifact'] == {'updated': True}

        # Replay that changed receipt identically again: generation stable
        ledger.offer(rc1_artifact_changed, offers1)
        assert ledger.generation() == 4


def test_new_source_equal_rank_refreshes_member(tmp_path):
    root = tmp_path / 'queue'
    with HarvestQueue(root) as queue:
        ledger = AutomationLedger(queue, policy_revision=POLICY_A, objectives={'obj': 2})
        obs1 = '1' * 64
        obs2 = '2' * 64

        rc = make_receipt(810)
        rc['observation_id'] = obs1
        offers1 = [{
            'objective_id': 'obj',
            'rank': [10],
            'member': {'world_id': rc['world_id'], 'source_observation_id': obs1, 'detail': 'initial'}
        }]
        ledger.offer(rc, offers1)
        assert ledger.generation() == 1
        assert ledger.receipt(rc['world_id'])['observation_id'] == obs1
        assert ledger.members('obj')[0]['member']['detail'] == 'initial'
        assert ledger.members('obj')[0]['member']['source_observation_id'] == obs1

        # New observation ID arrives with EQUAL rank: member must update to current receipt
        rc_new_obs = make_receipt(810)
        rc_new_obs['observation_id'] = obs2
        offers2 = [{
            'objective_id': 'obj',
            'rank': [10],
            'member': {'world_id': rc['world_id'], 'source_observation_id': obs2, 'detail': 'refreshed'}
        }]
        ledger.offer(rc_new_obs, offers2)
        assert ledger.generation() == 2
        assert ledger.receipt(rc['world_id'])['observation_id'] == obs2
        assert ledger.members('obj')[0]['rank'] == [10]
        assert ledger.members('obj')[0]['member']['detail'] == 'refreshed'
        assert ledger.members('obj')[0]['member']['source_observation_id'] == obs2

        # Legacy member payload without source_observation_id succeeds without injecting invented field
        obs3 = '3' * 64
        rc_legacy = make_receipt(810)
        rc_legacy['observation_id'] = obs3
        offers3 = [{
            'objective_id': 'obj',
            'rank': [10],
            'member': {'world_id': rc['world_id'], 'detail': 'legacy_refresh'}
        }]
        ledger.offer(rc_legacy, offers3)
        assert ledger.generation() == 3
        assert ledger.receipt(rc['world_id'])['observation_id'] == obs3
        assert ledger.members('obj')[0]['member'] == {'world_id': rc['world_id'], 'detail': 'legacy_refresh'}
        assert 'source_observation_id' not in ledger.members('obj')[0]['member']


def test_missing_or_worse_fresh_source_rolls_back_atomically(tmp_path):
    root = tmp_path / 'queue'
    with HarvestQueue(root) as queue:
        ledger = AutomationLedger(queue, policy_revision=POLICY_A, objectives={'obj_a': 1, 'obj_b': 1})
        obs1 = 'a' * 64
        rc1 = make_receipt(820)
        rc1['observation_id'] = obs1
        ledger.offer(rc1, [
            {'objective_id': 'obj_a', 'rank': [10], 'member': {'world_id': rc1['world_id'], 'source_observation_id': obs1}},
            {'objective_id': 'obj_b', 'rank': [20], 'member': {'world_id': rc1['world_id'], 'source_observation_id': obs1}},
        ])
        assert ledger.generation() == 1
        assert ledger.population() == 1
        assert ledger.retained_worlds() == [rc1['world_id']]

        # 1. Missing old winning objective on fresh source
        obs2 = 'b' * 64
        rc2_missing = make_receipt(820)
        rc2_missing['observation_id'] = obs2
        with pytest.raises(ValueError, match='missing required offers'):
            ledger.offer(rc2_missing, [
                {'objective_id': 'obj_a', 'rank': [10], 'member': {'world_id': rc1['world_id'], 'source_observation_id': obs2}},
            ])
        # Preserved atomically without mutation
        assert ledger.generation() == 1
        assert ledger.population() == 1
        assert ledger.receipt(rc1['world_id'])['observation_id'] == obs1
        assert len(ledger.members('obj_a')) == 1
        assert len(ledger.members('obj_b')) == 1

        # 2. Rank worsening on old winning objective on fresh source
        obs3 = 'c' * 64
        rc3_worse = make_receipt(820)
        rc3_worse['observation_id'] = obs3
        with pytest.raises(ValueError, match='worse rank'):
            ledger.offer(rc3_worse, [
                {'objective_id': 'obj_a', 'rank': [5], 'member': {'world_id': rc1['world_id'], 'source_observation_id': obs3}},
                {'objective_id': 'obj_b', 'rank': [25], 'member': {'world_id': rc1['world_id'], 'source_observation_id': obs3}},
            ])
        # Preserved atomically without mutation
        assert ledger.generation() == 1
        assert ledger.population() == 1
        assert ledger.receipt(rc1['world_id'])['observation_id'] == obs1
        assert ledger.members('obj_a')[0]['rank'] == [10]
        assert ledger.members('obj_b')[0]['rank'] == [20]

        # 3. Member source_observation_id mismatch on fresh source
        obs4 = 'd' * 64
        rc4_mismatch = make_receipt(820)
        rc4_mismatch['observation_id'] = obs4
        with pytest.raises(ValueError, match='does not match receipt observation_id'):
            ledger.offer(rc4_mismatch, [
                {'objective_id': 'obj_a', 'rank': [10], 'member': {'world_id': rc1['world_id'], 'source_observation_id': 'e' * 64}},
                {'objective_id': 'obj_b', 'rank': [20], 'member': {'world_id': rc1['world_id'], 'source_observation_id': obs4}},
            ])
        # Preserved atomically without mutation
        assert ledger.generation() == 1
        assert ledger.population() == 1
        assert ledger.receipt(rc1['world_id'])['observation_id'] == obs1

        # 4. Same observation ID with worse offer retains winning rank (does not fail, does not update rank)
        rc1_worse = make_receipt(820)
        rc1_worse['observation_id'] = obs1
        ledger.offer(rc1_worse, [
            {'objective_id': 'obj_a', 'rank': [50], 'member': {'world_id': rc1['world_id'], 'source_observation_id': obs1}},
        ])
        # Stable generation (receipt unchanged, member unchanged) and winning rank retained
        assert ledger.generation() == 1
        assert ledger.members('obj_a')[0]['rank'] == [10]
        assert ledger.members('obj_b')[0]['rank'] == [20]


def test_deterministic_receipts_for_gc(tmp_path):
    root = tmp_path / 'queue'
    with HarvestQueue(root) as queue:
        ledger = AutomationLedger(queue, policy_revision=POLICY_A, objectives={'test': 10})
        # Empty ledger returns empty list
        assert ledger.receipts() == []

        # Add multiple worlds in non-sorted seed order
        seeds = [905, 901, 904, 902, 903]
        for s in seeds:
            rc = make_receipt(s)
            ledger.offer(rc, [{'objective_id': 'test', 'rank': [s], 'member': {'world_id': rc['world_id']}}])

        all_receipts = ledger.receipts()
        assert len(all_receipts) == len(seeds)
        assert len(all_receipts) == ledger.population()

        # Deterministic sorting by world_id ascending
        world_ids = [r['world_id'] for r in all_receipts]
        assert world_ids == sorted(world_ids)

        # Each receipt matches individual ledger.receipt()
        for r in all_receipts:
            single = ledger.receipt(r['world_id'])
            assert r == single
            assert set(r.keys()) == {'world_id', 'identity', 'observation_id', 'artifact', 'evaluations', 'replay'}

