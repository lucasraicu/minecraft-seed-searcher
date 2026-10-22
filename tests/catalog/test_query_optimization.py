"""Strict reader boundaries and accuracy response isolation on the faster path."""
import copy
import pytest
from seed_search.catalog import index, refined_witnesses
from seed_search.catalog.registry import BIOMES, digest
from seed_search.catalog.segments import SegmentedCatalog
from seed_search.catalog.service import CatalogService
from tests.catalog.test_accuracy_service import setup
from tests.catalog.test_integrated_pilot import sample, bind
from seed_search.catalog.evaluation import heldout_cases


@pytest.mark.parametrize('value,rows,expected', [
    ('',0,0),('00',1,0),('01',1,1),('ff',8,255),
    ('0f',4,15),('0'*63+'f',256,15),
])
def test_canonical_bitsets_keep_zero_padding_and_row_boundaries(value,rows,expected):
    assert index.decode_bitset(value,rows)==expected


@pytest.mark.parametrize('value,rows', [
    ('00',0),('',1),('1',1),('001',8),('02',1),('10',4),
    ('FF',8),('0A',8),(' f',8),('f ',8),('+1',8),('-1',8),
    ('0x',8),('0\n',8),('0\0',8),('０1',8),('é1',8),
    ('𝟘1',8),(b'01',8),(None,8),(1,8),
])
def test_noncanonical_or_reserved_bitsets_still_fail(value,rows):
    with pytest.raises(ValueError):index.decode_bitset(value,rows)


@pytest.mark.parametrize('corruption',['reserved_bits','payload_metadata','legacy_payload_metadata'])
def test_optimized_reader_validates_even_after_artifact_decoding(tmp_path,monkeypatch,corruption):
    # Inject malformed decoded content after the independent content-addressed
    # artifact check, so the reader's own validation must still reject it.
    obs,rows=sample(7)
    with SegmentedCatalog(tmp_path)as store:
        sid=store.publish([obs],rows);req=bind(heldout_cases()['cases'][0]['template'],store.info(sid))
        original=store.artifacts.get_json
        def decoded(manifest):
            value=original(manifest)
            if corruption=='reserved_bits'and value.get('revision')==index.INDEX_REVISION:
                value=copy.deepcopy(value);n=value['num_rows']
                value['bitsets']['origin']=f'{1<<n:0{((n+7)//8)*2}x}'
                value['index_digest']=digest({k:v for k,v in value.items()if k!='index_digest'})
            if corruption in ('payload_metadata','legacy_payload_metadata')and value.get('kind')=='leaf':
                value=copy.deepcopy(value);value['layouts'][0]['layout_id']='f'*64
                if corruption=='legacy_payload_metadata':value.pop('index_manifest')
            return value
        monkeypatch.setattr(store.artifacts,'get_json',decoded)
        with pytest.raises(ValueError):list(store.iter_segments(sid,request=req))


def test_public_filter_stays_strict_and_legacy_no_index_requests_are_validated(tmp_path,monkeypatch):
    obs,rows=sample(7)
    with SegmentedCatalog(tmp_path)as store:
        sid=store.publish([obs],rows);req=bind(heldout_cases()['cases'][0]['template'],store.info(sid))
        idx=index.build_index(rows);bad=copy.deepcopy(idx);bad['index_digest']='f'*64
        with pytest.raises(ValueError):index.filter_index(bad,req)
        invalid=dict(req,border_side=9999)
        for bad_request in (invalid, [], 7, b'{}', True):
            with pytest.raises(ValueError):index.filter_index(idx,bad_request)
        original=store.artifacts.get_json
        def old_leaf(manifest):
            value=original(manifest)
            if value.get('kind')=='leaf':value={k:v for k,v in value.items()if k!='index_manifest'}
            return value
        monkeypatch.setattr(store.artifacts,'get_json',old_leaf)
        assert sum(len(s['layouts'])for s in store.iter_segments(sid,request=req))==len(rows)
        for bad_request in (invalid, [], 7, b'{}', True):
            with pytest.raises(ValueError):list(store.iter_segments(sid,request=bad_request))


@pytest.mark.parametrize('mode',['origin','recommended','world_spawn_estimated'])
def test_empty_witness_path_matches_copying_and_keeps_pages_isolated(tmp_path,monkeypatch,mode):
    bundle,req=setup(tmp_path);req=dict(req,anchor_mode=mode)
    service=CatalogService(tmp_path);first=service.query({'request':req})
    original=copy.deepcopy(first['results'])
    # A real inventory with a witness outside every layout forces the unchanged
    # copying path while producing no refined result. Both paths must agree.
    points={b['id']:[]for b in BIOMES};points[BIOMES[0]['id']]=[[1000000,63,1000000,'a'*64]]
    monkeypatch.setattr(refined_witnesses,'model_witnesses',lambda *args:points)
    copying=CatalogService(tmp_path).query({'request':req})
    assert copying['results']==original and copying['unresolved_candidates']==first['unresolved_candidates']
    first['results'][0]['counts'][0][0]=999
    first['results'][0]['contributions'].clear()
    cached=service.query({'request':req});assert cached['results']==original
    assert CatalogService(tmp_path,cache_bytes=0).query({'request':req})['results']==original
