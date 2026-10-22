"""Evidence belongs to one immutable world and to the selected geometric scope."""

import pytest

from seed_search.catalog.evidence import build_evidence,write_evidence
from seed_search.catalog.models import world_id
from seed_search.catalog.product_views import derive_previews,write_previews
from seed_search.catalog.summaries import summarize
from seed_search.catalog.segments import SegmentedCatalog
from seed_search.catalog.service import CatalogService,ServiceError
from tests.catalog.test_integrated_pilot import sample


def verifier():
    return dict(edition='bedrock',game_build_id='1.26.52.3',image_sha256='a'*64,
                script_api='2.10.0',settings_sha256='b'*64,report_sha256s=['c'*64])


def fixture(tmp_path):
    obs,_=sample(12345)
    obs['structures']['structure.village']=[[0,0],[1200,0]]
    layouts=[r for r in summarize(obs) if r['anchor'] in ([0,0],[256,0],[-256,0])]
    root=tmp_path/'catalog'
    with SegmentedCatalog(root) as store:
        sid=store.publish([obs],layouts);write_previews(root,derive_previews(store,sid))
    positions=obs['structures']['structure.village']
    assert len(positions)==2
    checks=[dict(feature_id='structure.village',command_id='village',predicted=positions[0],reported=positions[0],outcome='located_exact'),
            dict(feature_id='structure.village',command_id='village',predicted=positions[1],reported=[3000,3000],outcome='coordinate_difference')]
    payload=build_evidence(obs,sid,verifier(),checks)
    body=dict(revision='catalog-product-request-v1',snapshot_id=sid,product_id='research.origin.village.r2000')
    return root,obs,layouts,sid,payload,body


def test_missing_evidence_is_untested_and_rankings_unchanged(tmp_path):
    root,obs,layouts,sid,payload,body=fixture(tmp_path);service=CatalogService(root)
    before=service.product_results(body)
    row=before['results'][0];e=row['structure_evidence']
    assert e['tested_count']==0 and e['untested_count']==row['count']
    write_evidence(root,payload)
    after=service.product_results(body);a=after['results'][0]
    assert (a['world_id'],a['count'],a['witnesses'])==(row['world_id'],row['count'],row['witnesses'])
    assert a['structure_evidence']['located_exact']==1
    assert a['structure_evidence']['coordinate_difference']==1
    assert a['structure_evidence']['generated_count'] is None
    assert a['structure_evidence']['exhaustive_count'] is None


def test_detail_uses_same_selected_anchor_border(tmp_path):
    root,obs,layouts,sid,payload,body=fixture(tmp_path);write_evidence(root,payload)
    # Source fixture has villages at0 and1200: an origin2048 border excludes1200.
    layout=next(r for r in layouts if r['anchor']==[0,0] and r['border_side']==2048)
    detail=CatalogService(root).detail(sid,world_id(obs['identity']),layout['layout_id'])
    e=detail['structure_evidence']['structure.village']
    assert e['predicted_count']==1 and e['tested_count']==1 and e['located_exact']==1
    assert e['coordinate_difference']==0 and e['untested_count']==0
    assert detail['layout']['anchor']==[0,0]
    assert detail['biome_evidence']['checks']==[]


def test_evidence_corruption_never_silently_downgrades(tmp_path):
    root,obs,layouts,sid,payload,body=fixture(tmp_path);path=write_evidence(root,payload)
    path.write_text('{}')
    with pytest.raises(ServiceError) as exc:CatalogService(root).product_results(body)
    assert exc.value.code=='integrity_error'
    layout=layouts[0]
    with pytest.raises(ServiceError) as exc:CatalogService(root).detail(sid,world_id(obs['identity']),layout['layout_id'])
    assert exc.value.code=='integrity_error'


def test_later_snapshot_does_not_inherit_verification(tmp_path):
    root,obs,layouts,sid,payload,body=fixture(tmp_path);write_evidence(root,payload)
    new,rows=sample(456)
    with SegmentedCatalog(root) as store:new_sid=store.publish([new],rows,parent=sid)
    with SegmentedCatalog(root) as store:write_previews(root,derive_previews(store,new_sid))
    response=CatalogService(root).product_results(dict(body,snapshot_id=new_sid))
    assert response['snapshot_id']==new_sid
    assert all(r['structure_evidence']['tested_count']==0 for r in response['results'])


def test_evidence_circle_and_square_edge_semantics(tmp_path):
    obs,_=sample(-1)
    points=[[-2000,0],[-1024,0],[1024,0],[2000,0],[2001,0]]
    obs['structures']['structure.village']=points
    layouts=[r for r in summarize(obs) if r['anchor']==[0,0]]
    root=tmp_path/'catalog'
    with SegmentedCatalog(root) as store:
        sid=store.publish([obs],layouts);write_previews(root,derive_previews(store,sid))
    checks=[dict(feature_id='structure.village',command_id='village',predicted=p,reported=p,outcome='located_exact') for p in points]
    write_evidence(root,build_evidence(obs,sid,verifier(),checks))
    service=CatalogService(root)
    result=service.product_results(dict(revision='catalog-product-request-v1',snapshot_id=sid,product_id='research.origin.village.r2000'))
    assert result['results'][0]['count']==4
    assert result['results'][0]['structure_evidence']['located_exact']==4
    selected=next(r for r in layouts if r['border_side']==2048)
    detail=service.detail(sid,world_id(obs['identity']),selected['layout_id'])
    assert detail['structure_evidence']['structure.village']['predicted_count']==1
    assert detail['structure_evidence']['structure.village']['located_exact']==1


def test_evidence_root_ancestor_symlink_rejected(tmp_path):
    root,obs,layouts,sid,payload,body=fixture(tmp_path)
    alias=tmp_path/'alias';alias.symlink_to(root.parent,target_is_directory=True)
    with pytest.raises(ValueError,match='Symlink'):
        write_evidence(alias/root.name,payload)


def test_durable_publication_propagates_directory_fsync_failure(tmp_path,monkeypatch):
    root,obs,layouts,sid,payload,body=fixture(tmp_path)
    from seed_search.catalog import evidence
    monkeypatch.setattr(evidence,'_fsync_dir',lambda _:(_ for _ in ()).throw(OSError('fsync failed')))
    with pytest.raises(OSError,match='fsync failed'):write_evidence(root,payload)
    assert not list((root/'evidence'/sid).glob('.tmp_*'))


def test_concurrent_publication_never_clobbers_another_payload(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    import copy
    from seed_search.catalog.evidence import read_evidence
    root,obs,layouts,sid,payload,body=fixture(tmp_path)
    other=copy.deepcopy(payload);other['verifier']['report_sha256s']=['d'*64]
    def publish(value):
        try:return str(write_evidence(root,value))
        except ValueError:return None
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(publish,[payload,other]))
    assert sum(v is not None for v in results)==1
    stored=read_evidence(root,sid,payload['world_id'],payload['observation_id'])
    assert stored in (payload,other)
    assert not list((root/'evidence'/sid).glob('.tmp_*'))
