"""Verification of physical manifest paging, index schemas, binding reuse, and fail-closed GC."""
from pathlib import Path
import copy
import pytest
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.models import identity, empty_observation_v2, world_id
from seed_search.catalog.registry import digest, canonical_json
from seed_search.catalog.summaries import summarize_v2
from seed_search.catalog.harvest import HarvestQueue, AutomationLedger
from seed_search.catalog.ingestion import atomic_json


def obs(seed='123'):
    return empty_observation_v2(identity(seed, model_id='MC_26_50', native_sha256='a'*64, source_sha256='b'*64))


def offer(store, ledger, observation, rank=0, *, winner=True, resumable=False):
    wid = world_id(observation['identity'])
    oid = digest(observation)
    artifact = store.stage(observation, [])
    receipt = dict(
        world_id=wid,
        identity=observation['identity'],
        observation_id=oid,
        artifact=artifact,
        evaluations=[],
        replay={'resumable': resumable}
    )
    ledger.offer(
        receipt,
        [dict(objective_id='test', rank=[rank], member=dict(world_id=wid, source_observation_id=oid))] if winner else []
    )
    return receipt


@pytest.fixture
def setup(tmp_path):
    with HarvestQueue(tmp_path) as queue:
        yield AutomationStore(tmp_path), AutomationLedger(queue, policy_revision='c'*64, objectives={'test': 10})


def test_flat_and_paged_logical_digest_and_api_identity(tmp_path):
    """Paged physical storage produces identical logical snapshot SHA, schema, and API access."""
    with HarvestQueue(tmp_path / 'q1') as q1, HarvestQueue(tmp_path / 'q2') as q2:
        store_flat = AutomationStore(tmp_path / 's1')
        ledger_flat = AutomationLedger(q1, policy_revision='c'*64, objectives={'test': 10})
        store_paged = AutomationStore(tmp_path / 's2')
        ledger_paged = AutomationLedger(q2, policy_revision='c'*64, objectives={'test': 10})

        # Inject tiny thresholds to force paging with small fixtures
        store_paged._PAGE_THRESHOLD_BYTES = 256
        store_paged._PAGE_ITEM_LIMIT = 2
        store_paged._PAGE_BYTE_LIMIT = 4096

        receipts_flat = [offer(store_flat, ledger_flat, obs(str(i)), rank=i) for i in range(5)]
        receipts_paged = [offer(store_paged, ledger_paged, obs(str(i)), rank=i) for i in range(5)]

        sid_flat = store_flat.publish(ledger_flat)
        sid_paged = store_paged.publish(ledger_paged)

        # 1. Exact snapshot identity parity
        assert sid_flat == sid_paged

        # 2. Flat is catalog-snapshot-v2, paged is catalog-snapshot-index-v2
        flat_binding = store_flat._binding(sid_flat)
        paged_binding = store_paged._binding(sid_paged)
        flat_payload = store_flat.artifacts.get_json(flat_binding['artifact'])
        paged_index = store_paged.artifacts.get_json(paged_binding['artifact'])

        assert flat_payload['revision'] == 'catalog-snapshot-v2'
        assert paged_index['revision'] == 'catalog-snapshot-index-v2'
        assert set(paged_index.keys()) == {'revision', 'policy_revision', 'generation', 'population_worlds', 'pages', 'product_status'}
        assert paged_index['product_status']==flat_payload['product_status']
        assert len(paged_index['pages']) > 1

        # Check page schemas
        for page_ref in paged_index['pages']:
            assert set(page_ref.keys()) == {'kind', 'count', 'artifact'}
            assert page_ref['kind'] in ('worlds', 'memberships')
            page_data = store_paged.artifacts.get_json(page_ref['artifact'])
            assert set(page_data.keys()) == {'revision', 'kind', 'count', 'items'}
            assert page_data['revision'] == 'catalog-snapshot-page-v2'
            assert page_data['kind'] == page_ref['kind']
            assert page_data['count'] == page_ref['count'] == len(page_data['items'])

        # 3. Logical snapshot manifest is 100% identical
        manifest_flat = store_flat.snapshot(sid_flat)
        manifest_paged = store_paged.snapshot(sid_paged)
        assert manifest_flat == manifest_paged
        assert canonical_json(manifest_flat) == canonical_json(manifest_paged)

        # 4. API access parity: world(), iter_worlds(), snapshots()
        for r in receipts_flat:
            w_flat = store_flat.world(sid_flat, r['world_id'])
            w_paged = store_paged.world(sid_paged, r['world_id'])
            assert w_flat == w_paged

        worlds_flat = list(store_flat.iter_worlds(sid_flat))
        worlds_paged = list(store_paged.iter_worlds(sid_paged))
        assert worlds_flat == worlds_paged

        assert store_paged.snapshots() == store_flat.snapshots()


def test_immutable_legacy_binding_reuse_after_threshold_change(setup):
    """Publishing must never overwrite existing bindings: same SID reuses existing artifact representation."""
    store, ledger = setup
    offer(store, ledger, obs('1'), rank=0)
    offer(store, ledger, obs('2'), rank=1)

    # Initially publish flat
    sid = store.publish(ledger)
    binding_initial = store._binding(sid)
    raw_initial = store.artifacts.get_json(binding_initial['artifact'])
    assert raw_initial['revision'] == 'catalog-snapshot-v2'

    # Lower threshold to force paging on subsequent writes
    store._PAGE_THRESHOLD_BYTES = 100
    store._PAGE_ITEM_LIMIT = 1

    # Re-publish same ledger/SID -> MUST reuse legacy flat binding
    sid_repub = store.publish(ledger)
    assert sid_repub == sid
    binding_after = store._binding(sid)
    assert binding_after == binding_initial
    assert store.artifacts.get_json(binding_after['artifact'])['revision'] == 'catalog-snapshot-v2'

    # Conversely: publish paged snapshot in gen 3, then raise threshold
    offer(store, ledger, obs('3'), rank=-1)
    sid_gen3 = store.publish(ledger)
    binding_gen3 = store._binding(sid_gen3)
    assert store.artifacts.get_json(binding_gen3['artifact'])['revision'] == 'catalog-snapshot-index-v2'

    # Raise threshold back up
    store._PAGE_THRESHOLD_BYTES = 8 * 1024 * 1024
    sid_gen3_repub = store.publish(ledger)
    assert sid_gen3_repub == sid_gen3
    assert store._binding(sid_gen3) == binding_gen3


@pytest.mark.parametrize('point', ['after_generation', 'after_manifest', 'after_pointer'])
def test_paged_three_crash_fault_windows_and_recovery(setup, point):
    """Crash injection across all three fault windows with paged physical manifests."""
    store, ledger = setup
    store._PAGE_THRESHOLD_BYTES = 200
    store._PAGE_ITEM_LIMIT = 1
    receipt = offer(store, ledger, obs('1'))

    def fault(stage):
        if stage == point:
            raise OSError('injected ' + stage)

    with pytest.raises(OSError):
        store.publish(ledger, fault=fault)

    if point == 'after_generation':
        assert not store.current_path.exists() and store.snapshots() == []
        # Pending generation is protected in cleanup
        assert store.cleanup(ledger)['candidates'] == []

    sid = store.publish(ledger)
    binding_before = store.current_path.read_bytes()
    assert store.publish(ledger) == sid and store.current_path.read_bytes() == binding_before
    assert store.world(sid, receipt['world_id'])['observation'] == obs('1')
    assert len(store.snapshots()) == 1


def test_gc_page_protection_and_orphan_page_quarantine(setup):
    """GC protects all page artifacts of historical/pending generations and quarantines orphans."""
    store, ledger = setup
    store._PAGE_THRESHOLD_BYTES = 200
    store._PAGE_ITEM_LIMIT = 1

    first = offer(store, ledger, obs('1'), rank=5)
    sid1 = store.publish(ledger)

    second = offer(store, ledger, obs('2'), rank=0)
    sid2 = store.publish(ledger)

    # Create an orphan page directly in CAS
    orphan_page = dict(revision='catalog-snapshot-page-v2', kind='worlds', count=1, items=[{'world_id': 'x'*64}])
    orphan_art = store.artifacts.put_json(orphan_page)

    # Dry run cleanup must identify only the orphan page (and unreferenced bundles)
    dry = store.cleanup(ledger)
    assert orphan_art['relative_key'] in dry['candidates']

    # Ensure all page artifacts for sid1 and sid2 are protected
    idx1 = store.artifacts.get_json(store._binding(sid1)['artifact'])
    idx2 = store.artifacts.get_json(store._binding(sid2)['artifact'])
    page_keys = {ref['artifact']['relative_key'] for ref in idx1['pages'] + idx2['pages']}
    for pk in page_keys:
        assert pk not in dry['candidates']

    # Quarantine mode
    store.cleanup(ledger, mode='quarantine')
    assert (store.quarantine_dir / orphan_art['relative_key']).is_file()
    for pk in page_keys:
        assert (store.objects_dir / pk).is_file()

    # Delete mode
    store.cleanup(ledger, mode='delete')
    assert not (store.quarantine_dir / orphan_art['relative_key']).exists()
    for pk in page_keys:
        assert (store.objects_dir / pk).is_file()


def test_corrupt_or_missing_page_fails_closed_without_moves(setup):
    """Corrupt or missing page CAS fails closed before any orphan moves in cleanup."""
    store, ledger = setup
    store._PAGE_THRESHOLD_BYTES = 200
    store._PAGE_ITEM_LIMIT = 1
    offer(store, ledger, obs('1'))
    sid = store.publish(ledger)

    orphan_page = dict(revision='catalog-snapshot-page-v2', kind='worlds', count=1, items=[{'world_id': 'y'*64}])
    orphan_art = store.artifacts.put_json(orphan_page)
    orphan_path = store.objects_dir / orphan_art['relative_key']
    assert orphan_path.is_file()

    idx = store.artifacts.get_json(store._binding(sid)['artifact'])
    page_key = idx['pages'][0]['artifact']['relative_key']
    page_file = store.objects_dir / page_key
    saved_bytes = page_file.read_bytes()

    # Corrupt page file
    page_file.write_bytes(b'corrupt_content')
    with pytest.raises(ValueError):
        store.cleanup(ledger, mode='quarantine')
    # No move must have occurred!
    assert orphan_path.is_file()
    assert not (store.quarantine_dir / orphan_art['relative_key']).exists()

    with pytest.raises(ValueError):
        store.snapshot(sid)

    # Missing page file
    page_file.unlink()
    with pytest.raises(FileNotFoundError):
        store.cleanup(ledger, mode='quarantine')
    assert orphan_path.is_file()

    with pytest.raises(FileNotFoundError):
        store.snapshot(sid)

    # Restore page file -> cleanup succeeds and quarantines orphan
    page_file.write_bytes(saved_bytes)
    res = store.cleanup(ledger, mode='quarantine')
    assert orphan_art['relative_key'] in res['candidates']
    assert (store.quarantine_dir / orphan_art['relative_key']).is_file()


def test_nested_index_in_page_fails_closed(setup):
    """Nested index or recursive reference as page payload must fail closed."""
    store, ledger = setup
    store._PAGE_THRESHOLD_BYTES = 200
    store._PAGE_ITEM_LIMIT = 1
    offer(store, ledger, obs('1'))
    sid = store.publish(ledger)

    idx_binding = store._binding(sid)
    idx = store.artifacts.get_json(idx_binding['artifact'])

    # Create nested index artifact
    nested_idx_art = store.artifacts.put_json(idx)

    # Replace page ref artifact with nested index artifact
    bad_idx = copy.deepcopy(idx)
    bad_idx['pages'][0]['artifact'] = nested_idx_art
    bad_idx_art = store.artifacts.put_json(bad_idx)

    with pytest.raises(ValueError, match='Invalid snapshot page'):
        store._resolve_manifest(bad_idx_art)


def test_invalid_counts_and_unknown_fields_fail_closed(setup):
    """Strict validation on index schema, page schema, counts, and kind ordering."""
    store, ledger = setup
    store._PAGE_THRESHOLD_BYTES = 200
    store._PAGE_ITEM_LIMIT = 2
    offer(store, ledger, obs('1'), rank=0)
    offer(store, ledger, obs('2'), rank=1)
    sid = store.publish(ledger)

    idx = store.artifacts.get_json(store._binding(sid)['artifact'])

    # 1. Unknown field in index schema
    bad = copy.deepcopy(idx)
    bad['unknown_field'] = 'prohibited'
    art = store.artifacts.put_json(bad)
    with pytest.raises(ValueError, match='Invalid snapshot index schema'):
        store._resolve_manifest(art)

    # 2. Unknown field in page reference
    bad = copy.deepcopy(idx)
    bad['pages'][0]['unknown_ref_field'] = 123
    art = store.artifacts.put_json(bad)
    with pytest.raises(ValueError, match='Invalid page reference'):
        store._resolve_manifest(art)

    # 3. Invalid page ref count (0 or negative)
    bad = copy.deepcopy(idx)
    bad['pages'][0]['count'] = 0
    art = store.artifacts.put_json(bad)
    with pytest.raises(ValueError, match='Invalid page reference count'):
        store._resolve_manifest(art)

    bad = copy.deepcopy(idx)
    bad['pages'][0]['count'] = 99999
    art = store.artifacts.put_json(bad)
    with pytest.raises(ValueError, match='Invalid page reference count'):
        store._resolve_manifest(art)

    # 4. Count mismatch between index ref and page payload
    real_page = store.artifacts.get_json(idx['pages'][0]['artifact'])
    tampered_page = copy.deepcopy(real_page)
    tampered_page['count'] = tampered_page['count'] + 1
    tampered_page_art = store.artifacts.put_json(tampered_page)

    bad = copy.deepcopy(idx)
    bad['pages'][0]['artifact'] = tampered_page_art
    art = store.artifacts.put_json(bad)
    with pytest.raises(ValueError, match='Invalid snapshot page count'):
        store._resolve_manifest(art)

    # 5. Unknown field in page schema
    tampered_page = copy.deepcopy(real_page)
    tampered_page['extra'] = 'bad'
    tampered_page_art = store.artifacts.put_json(tampered_page)
    bad = copy.deepcopy(idx)
    bad['pages'][0]['artifact'] = tampered_page_art
    art = store.artifacts.put_json(bad)
    with pytest.raises(ValueError, match='Invalid snapshot page schema'):
        store._resolve_manifest(art)

    # 6. Disordered page kinds (memberships before worlds)
    world_pages = [p for p in idx['pages'] if p['kind'] == 'worlds']
    member_pages = [p for p in idx['pages'] if p['kind'] == 'memberships']
    if world_pages and member_pages:
        bad = copy.deepcopy(idx)
        bad['pages'] = member_pages + world_pages
        art = store.artifacts.put_json(bad)
        with pytest.raises(ValueError, match='Disordered page kinds'):
            store._resolve_manifest(art)


def test_page_byte_limit_splitting(setup):
    """Splitting triggered by canonical byte limit even when item limit is large."""
    store, ledger = setup
    store._PAGE_THRESHOLD_BYTES = 100
    store._PAGE_ITEM_LIMIT = 1000  # Large item limit
    store._PAGE_BYTE_LIMIT = 2400   # Includes optional projection refs; still forces byte-based splitting

    for i in range(4):
        offer(store, ledger, obs(str(i)), rank=i)

    sid = store.publish(ledger)
    idx = store.artifacts.get_json(store._binding(sid)['artifact'])

    # Should have multiple pages of worlds and memberships due to byte limit
    assert len(idx['pages']) > 2
    for page_ref in idx['pages']:
        page_dict = store.artifacts.get_json(page_ref['artifact'])
        assert len(canonical_json(page_dict)) <= store._PAGE_BYTE_LIMIT

    # Manifest resolution succeeds and matches expected world count
    manifest = store.snapshot(sid)
    assert len(manifest['worlds']) == 4
    assert len(manifest['memberships']) == 4


def test_page_boundary_accounts_for_exact_json_header(setup):
    store,ledger=setup
    offer(store,ledger,obs('1'));offer(store,ledger,obs('2'),rank=1)
    logical=store.snapshot(store.publish(ledger))
    exact=dict(revision='catalog-snapshot-page-v2',kind='worlds',count=2,items=logical['worlds'])
    store._PAGE_THRESHOLD_BYTES=1
    store._PAGE_BYTE_LIMIT=len(canonical_json(exact))-1
    physical=store._write_manifest(logical)
    index=store.artifacts.get_json(physical)
    assert len([p for p in index['pages'] if p['kind']=='worlds'])==2
    assert digest(store._resolve_manifest(physical))==digest(logical)


@pytest.mark.parametrize('fault',['binding_schema','binding_content'])
def test_reused_pending_generation_is_validated_before_pointer(setup,fault):
    store,ledger=setup;offer(store,ledger,obs('1'))
    def stop(phase):
        if phase=='after_generation':raise RuntimeError('owned fault')
    with pytest.raises(RuntimeError):store.publish(ledger,fault=stop)
    path=next(store.generations_dir.glob('*.json'));binding=store._read(path)
    if fault=='binding_schema':binding['revision']='invalid'
    else:
        logical=store._resolve_manifest(binding['artifact']);logical['population_worlds']+=1
        binding['artifact']=store._write_manifest(logical)
    atomic_json(path,binding)
    with pytest.raises(ValueError,match='reused|Reused'):store.publish(ledger)
    assert not store.current_path.exists() and not list(store.snapshots_dir.glob('*.json'))


def test_reader_enforces_page_byte_cap_and_integer_count(setup):
    store,ledger=setup;store._PAGE_THRESHOLD_BYTES=1;store._PAGE_ITEM_LIMIT=1
    offer(store,ledger,obs('1'));sid=store.publish(ledger)
    index=store.artifacts.get_json(store._binding(sid)['artifact'])
    page=store.artifacts.get_json(index['pages'][0]['artifact']);page['count']=True
    index['pages'][0]['artifact']=store.artifacts.put_json(page)
    with pytest.raises(ValueError,match='Invalid snapshot page count'):
        store._resolve_manifest(store.artifacts.put_json(index))
    store._PAGE_BYTE_LIMIT=20
    with pytest.raises(ValueError,match='Page byte cap'):store.snapshot(sid)


def test_pins_and_resumable_shares_preserved_with_paged_snapshots(setup):
    """Pins and resumable receipts are safely preserved across paged publication generations."""
    store, ledger = setup
    store._PAGE_THRESHOLD_BYTES = 200
    store._PAGE_ITEM_LIMIT = 1

    first = offer(store, ledger, obs('1'), rank=5)
    sid1 = store.publish(ledger)
    store.pin(sid1, first['world_id'])

    second = offer(store, ledger, obs('2'), rank=0)
    sid2 = store.publish(ledger)

    pending = offer(store, ledger, obs('3'), winner=False, resumable=True)
    orphan = offer(store, ledger, obs('4'), winner=False, resumable=False)

    dry = store.cleanup(ledger)
    assert dry['candidates'] == [orphan['artifact']['relative_key']]

    store.cleanup(ledger, mode='quarantine')
    assert (store.quarantine_dir / orphan['artifact']['relative_key']).is_file()
    assert store.world(sid1, first['world_id'])['observation']['identity']['seed'] == '1'
    assert store.world(sid2, second['world_id'])['observation']['identity']['seed'] == '2'
    assert store.artifacts.get_json(pending['artifact'])['observation']['identity']['seed'] == '3'
