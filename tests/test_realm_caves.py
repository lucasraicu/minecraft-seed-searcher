from seed_search.realm.caves import verify_caves


def test_unsupported_does_not_report_absence_or_score():
    r=verify_caves('1',(0,0),{})
    assert r['status']=='UNSUPPORTED' and r['score_effect'] is None
    assert all(v['status']=='UNKNOWN' for v in r['families'].values())


def test_manual_actual_positives_and_grid_budget():
    class Actual:
        def sample_caves(self,seed,bounds,spacing,ys):
            return {'actual':True,'source':'official BDS 1.26.52.3','observations':[
                {'x':bounds[0],'y':-16,'z':bounds[1],'biome':'minecraft:lush_caves'}]}
    r=verify_caves('1',(-9,-1),{},adapter=Actual())
    assert r['status']=='PARTIAL'
    assert r['families']['lush_caves']['status']=='VERIFIED'
    assert r['families']['sulfur_caves']['status']=='UNKNOWN'
    assert r['families']['deep_dark']['informational']
    assert not r['coverage']['complete_volume']
    r=verify_caves('1',(0,0),{'manual_caves':{'sample_budget':1}},adapter=Actual())
    assert r['status']=='UNSUPPORTED' and r['sampled_points']==0


def test_prediction_not_actual_and_unknown_absence():
    class Predicted:
        seed=1
        def biome_points(self,points):
            return ['lush_caves']+['plains']*(len(points)-1)
    r=verify_caves('1',(0,0),{},predictor=Predicted())
    assert r['status']=='PREDICTED'
    assert r['families']['lush_caves']['status']=='PREDICTED'
    assert r['families']['dripstone_caves']['status']=='UNKNOWN'


def test_initial_provider_failure_returns_report_with_unknown_families():
    import json
    class Broken:
        def sample_caves(self,*args):
            raise RuntimeError('BDS unavailable')
    r=verify_caves('1',(0,0),{},adapter=Broken())
    assert r['status']=='FAILED' and r['sampled_points']==0
    assert r['errors']==[{'stage':'initial','type':'RuntimeError','message':'BDS unavailable'}]
    assert all(v['status']=='UNKNOWN' for v in r['families'].values())
    assert not r['refinement']['performed']
    assert r['manual_only'] and r['score_effect'] is None
    json.dumps(r,allow_nan=False)  # The CLI can retain this failure artifact.


def test_refinement_failure_preserves_verified_positive_and_records_error():
    class BrokenRefinement:
        calls=0
        def sample_caves(self,seed,bounds,spacing,ys):
            self.calls+=1
            if self.calls>1:
                raise RuntimeError('Chunk unavailable')
            return {'actual':True,'source':'official BDS 1.26.52.3','observations':[
                {'x':bounds[0],'y':-16,'z':bounds[1],'biome':'minecraft:lush_caves'}]}
    cfg={'manual_caves':{'spacing':1344,'sample_budget':128,'max_refinement_regions':2}}
    adapter=BrokenRefinement();r=verify_caves('1',(0,0),cfg,adapter=adapter)
    assert r['status']=='PARTIAL'
    assert r['families']['lush_caves']['status']=='VERIFIED'
    assert r['refinement']['regions'][0]['trigger']=='positive'
    assert r['refinement']['regions'][0]['status']=='FAILED'
    assert r['errors'][0]['stage']=='refinement'
    assert adapter.calls<=3 and r['refinement']['remaining_budget']>=0


def test_missing_manual_cells_trigger_bounded_uncertain_refinement():
    class Missing:
        calls=0
        def sample_caves(self,seed,bounds,spacing,ys):
            self.calls+=1
            rows=[] if self.calls==1 else [
                {'x':bounds[0]+spacing,'y':-16,'z':bounds[1],'biome':'minecraft:dripstone_caves'}]
            return {'actual':True,'source':'official BDS 1.26.52.3','observations':rows}
    cfg={'manual_caves':{'spacing':1344,'sample_budget':128,'max_refinement_regions':1}}
    adapter=Missing();r=verify_caves('1',(0,0),cfg,adapter=adapter)
    assert adapter.calls==2
    assert r['refinement']['regions'][0]['trigger']=='uncertain'
    assert r['families']['dripstone_caves']['status']=='VERIFIED'
    assert r['families']['sulfur_caves']['status']=='UNKNOWN'
    assert not r['coverage']['grid_complete']
    assert r['refinement']['remaining_budget']>=0


def test_error_rows_do_not_count_as_complete_manual_grid():
    class Unknown:
        def sample_caves(self,seed,bounds,spacing,ys):
            return {'actual':True,'source':'official BDS 1.26.52.3','observations':[
                {'x':x,'y':y,'z':z,'error':'Missing chunk','biome':None}
                for z in range(bounds[1],bounds[3],spacing)
                for x in range(bounds[0],bounds[2],spacing) for y in ys]}
    r=verify_caves('1',(0,0),{'manual_caves':{'spacing':1344,'sample_budget':128,'max_refinement_regions':0}},adapter=Unknown())
    assert r['sampled_points']==0 and not r['coverage']['grid_complete']
    assert all(v['status']=='UNKNOWN' for v in r['families'].values())


def test_missing_refinement_overlap_does_not_erase_initial_positive():
    class MissingOverlap:
        calls=0
        def sample_caves(self,seed,bounds,spacing,ys):
            self.calls+=1
            row={'x':-768,'y':-16,'z':-768,'biome':'minecraft:lush_caves'}
            if self.calls>1:
                row.update(biome=None,error='Missing overlap')
            return {'actual':True,'source':'official BDS 1.26.52.3','observations':[row]}
    cfg={'manual_caves':{'spacing':1344,'sample_budget':128,'max_refinement_regions':1}}
    r=verify_caves('1',(0,0),cfg,adapter=MissingOverlap())
    assert r['families']['lush_caves']['status']=='VERIFIED'
    assert len(r['families']['lush_caves']['observations'])==1
    assert not r['coverage']['grid_complete']
