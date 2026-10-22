import copy
import json
import pytest
from seed_search.catalog.validation_contracts import controls,pilot_controls,validate_controls,cohort
from seed_search.catalog.evaluation import heldout_cases
from seed_search.catalog.usefulness import import_requests,split_groups


def test_new_campaign_has_explicit_separate_frozen_population():
    old=controls({'identity':'test'});new=pilot_controls({'identity':'test'})
    assert validate_controls(new)==new and validate_controls(old)==old
    assert old['cohort']==cohort() and len(new['cohort'])==len(set(new['cohort']))==100
    assert not set(old['cohort'])&set(new['cohort'])
    assert new['extract_seconds']==old['extract_seconds']==900
    changed=copy.deepcopy(new);changed['cohort'][0]='1'
    with pytest.raises(ValueError):validate_controls(changed)
    changed=copy.deepcopy(old);changed['cohort_start']=100
    with pytest.raises(ValueError):validate_controls(changed)
    assert len(heldout_cases(seed=2026102005,count=256)['cases'])==256
    assert heldout_cases()['sha256']!=heldout_cases(seed=2026102005,count=256)['sha256']


def test_grouped_requests_do_not_fabricate_player_evidence():
    request=heldout_cases()['cases'][0]['template']
    rows=[dict(participant=f'person-{i}',request=request,annotation='I want this base') for i in range(8)]
    corpus=import_requests(json.dumps(rows));split=split_groups(corpus)
    assert split['status']=='split_ready_not_demand_validated'
    assert not set(split['train'])&set(split['heldout']) and split['heldout']
    assert split_groups(import_requests(json.dumps(rows[:1])))['status']=='not_evaluated'
    assert split_groups(import_requests(json.dumps(rows),source='developer'))['status']=='not_evaluated'
    rows[0]['source']='synthetic'
    with pytest.raises(ValueError):import_requests(json.dumps(rows),source='player')
    with pytest.raises(ValueError):import_requests('[{"participant":"x","participant":"y"}]')
    with pytest.raises(ValueError):import_requests(' '*((1<<20)+1))
