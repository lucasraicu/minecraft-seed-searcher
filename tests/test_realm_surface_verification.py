import copy
import json

import pytest

from seed_search.realm.config import default_config
from seed_search.realm.surface import verify_surface_families


class Adapter:
    def __init__(self, names=('minecraft:roofed_forest','minecraft:taiga')):
        self.names=names; self.calls=[]
    def cache_identity(self):return {'version':'pinned-test'}
    def verify_surface_points(self,seed,points,**kwargs):
        self.calls.append((seed,points,kwargs))
        return {'id':'fixture','seed':str(seed),'requested_points':[list(p) for p in sorted({tuple(p) for p in points})],
                'source':'actual','actual':True,'operation':'surface_points_v1',
                'identity':self.cache_identity(),'status':'PARTIAL','existence_only':True,'absence_verified':False,
                'surface_biome_observations':[{'x':p[0],'z':p[1],'name':n,'status':'OBSERVED'} for p,n in zip(points,self.names)]}


def candidate():return {'id':'7:100:200','seed':'7','stronghold':[100,200],'qualification':'PREDICTED','baseline_score':12}


def test_verified_positive_families_do_not_promote_baseline_or_claim_absence():
    c=candidate();before=copy.deepcopy(c)
    result=verify_surface_families(c,default_config(),Adapter(),[[100,200],[200,300]])
    assert result['wooded_requirement']=='VERIFIED'
    assert result['classification']['wooded_families']==['dark_pale','taiga']
    assert result['classification']['uncertainty']['wooded_family_count_interval']==[2,5]
    assert not result['absence_verified'] and result['status']=='PARTIAL'
    assert c==before


@pytest.mark.parametrize('points',[[[1444,200]],[[-1245,200]],[[100,1544]],[[True,200]],[[100,1.5]],[],[[100,200]]*17])
def test_invalid_or_outside_points_fail_before_provider(points):
    adapter=Adapter()
    with pytest.raises(ValueError):verify_surface_families(candidate(),default_config(),adapter,points)
    assert not adapter.calls


def test_missing_unknown_unmapped_samples_never_reject():
    result=verify_surface_families(candidate(),default_config(),Adapter(('forest','new_unknown_woodland')),[[100,200],[200,300]])
    assert result['wooded_requirement']=='PENDING'
    assert result['classification']['uncertainty']['wooded_family_count_interval']==[1,5]


def test_conflicting_names_at_one_point_do_not_count_two_families():
    result=verify_surface_families(candidate(),default_config(),Adapter(('forest','taiga')),[[100,200],[100,200]])
    assert result['wooded_requirement']=='PENDING'
    assert result['conflicting_coordinates']==[[100,200]]


def test_failed_or_unpinned_result_cannot_verify_presence():
    class Untrusted(Adapter):
        def verify_surface_points(self,*args,**kwargs):
            r=super().verify_surface_points(*args,**kwargs);r['identity']={'version':'other'};return r
    assert verify_surface_families(candidate(),default_config(),Untrusted(),[[100,200],[200,300]])['wooded_requirement']=='PENDING'


@pytest.mark.parametrize('field,value',[('seed','999'),('requested_points',[[101,200]]),('status','FAILED')])
def test_mismatched_request_evidence_cannot_verify_presence(field,value):
    class Untrusted(Adapter):
        def verify_surface_points(self,*args,**kwargs):
            r=super().verify_surface_points(*args,**kwargs);r[field]=value;return r
    assert verify_surface_families(candidate(),default_config(),Untrusted(),[[100,200],[200,300]])['wooded_requirement']=='PENDING'


def test_cli_saves_separate_surface_channel_preserving_pool_scores(tmp_path,monkeypatch,capsys):
    from seed_search.realm import cli,verification
    from test_realm_report_recovery import populated
    store,cfg=populated(tmp_path);before=store.get_candidate('0:1:2');store.close()
    monkeypatch.setattr(verification,'VerificationAdapter',lambda *args:Adapter())
    points=tmp_path/'points.json';points.write_text(json.dumps([[1,2],[2,3]]))
    cli.main(['verify-biomes','--run',str(tmp_path),'--candidate','0:1:2','--points',str(points)])
    from seed_search.realm.store import RealmStore
    with RealmStore(tmp_path,resume=True) as saved:
        after=saved.get_candidate('0:1:2')
        assert after['qualification']==before['qualification']
        assert after['baseline_score']==before['baseline_score']
        assert after['biomes']==before['biomes']
        assert after['surface_biome_verification']['wooded_requirement']=='VERIFIED'
        assert saved.status()['completed_seeds']==3
    capsys.readouterr()


def test_surface_rescore_uses_saved_names_without_generation(tmp_path):
    from test_realm_report_recovery import populated
    from seed_search.realm.reports import rescore
    store,cfg=populated(tmp_path)
    try:
        c=store.get_candidate('0:1:2')
        evidence=verify_surface_families(c,cfg,Adapter(('pale_garden','bamboo_jungle')),[[1,2],[2,3]])
        store.upsert_candidate({'id':c['id'],'surface_biome_verification':evidence})
        cfg['biomes']['variant_bonuses']['pale_garden']=11
        rescore(store,cfg)
        saved=store.get_candidate(c['id'])['surface_biome_verification']
        assert saved['classification']['score']==13
        assert saved['wooded_requirement']=='VERIFIED'
        assert saved['observation']==evidence['observation']
        assert not saved['classification']['uncertainty']['exhaustive_verified']
        assert saved['score_revision']
        from seed_search.realm.reports import export
        import csv
        export(store)
        with (store.run/'results'/'baseline.csv').open() as f:
            rows=list(csv.DictReader(f))
        observed=next(row for row in rows if row['candidate_id']==c['id'])
        assert observed['surface_wooded_requirement']=='VERIFIED'
        assert json.loads(observed['surface_wooded_families'])==['dark_pale','jungle']
        assert json.loads(observed['surface_bonus_interval'])[0]==13
        assert 'Actual surface wooded requirement: VERIFIED' in (store.run/'results'/'SUMMARY.md').read_text()
    finally:store.close()


def test_publication_uses_policy_changed_during_generation(tmp_path):
    from test_realm_report_recovery import populated
    from seed_search.realm.surface import save_surface_verification
    from seed_search.realm.reports import rescore
    store,cfg=populated(tmp_path)
    try:
        c=store.get_candidate('0:1:2')
        evidence=verify_surface_families(c,cfg,Adapter(('pale_garden','bamboo_jungle')),[[1,2],[2,3]])
        assert evidence['classification']['score']==5
        cfg['biomes']['variant_bonuses']['pale_garden']=11
        rescore(store,cfg)
        saved=save_surface_verification(store,c['id'],evidence)
        assert saved['surface_biome_verification']['classification']['score']==13
        assert saved['surface_biome_verification']['score_revision']==store.get_state('rescore_revision')['id']
        assert saved['qualification']=='PREDICTED'
    finally:store.close()
