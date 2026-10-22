"""Importer must bind real audit protocol fields, not trust a SUCCESS label."""
import json

import pytest

from scripts.catalog_evidence import collect,IMAGE_SHA
from seed_search.catalog.models import world_id,observation_id
from seed_search.catalog.segments import SegmentedCatalog
from tests.catalog.test_integrated_pilot import sample


def source(tmp_path):
    root=tmp_path/'catalog';obs,rows=sample(12345)
    with SegmentedCatalog(root) as store:sid=store.publish([obs],rows)
    audit=tmp_path/'audit';audit.mkdir();(audit/'worlds/world').mkdir(parents=True)
    (audit/'console.log').write_text('[INFO] Version: 1.26.52.3\n')
    (audit/'worlds/world/server.properties').write_text('level-seed=12345\n')
    x,z=obs['structures']['structure.village'][0]
    report=dict(status='observed',clean_shutdown=True,owned_container_removed=True,
        controls=dict(seed='12345',image_id='sha256:'+IMAGE_SHA,
            prediction=dict(world_id=world_id(obs['identity']),observation_id=observation_id(obs))),
        world_identity=dict(seed='12345'),queries=[dict(kind='structure.village',query=[x,z],command_id='village',dimension='overworld',
            output=[f'[INFO] The nearest minecraft:village is at block {x}, (y?), {z} (0 blocks away)'])])
    path=audit/'report.json';path.write_text(json.dumps(report))
    return root,sid,path,report


def test_import_binds_source_and_deduplicates_repeated_checks(tmp_path):
    root,sid,path,report=source(tmp_path)
    values,skipped=collect(root,sid,[path,path])
    assert len(values)==1 and skipped==0
    assert values[0]['verifier']['game_build_id']=='1.26.52.3'
    assert values[0]['source_identity']['game_build_id'].startswith('research:')
    assert len(values[0]['verifier']['report_sha256s'])==1
    assert len(values[0]['structure_checks'])==1
    assert values[0]['structure_checks'][0]['outcome']=='located_exact'


@pytest.mark.parametrize('case',['wrong_seed','wrong_image','false_cleanup','string_cleanup','empty_response','wrong_source','wrong_command','outside_source'])
def test_import_refuses_invalid_or_unobserved_audits(tmp_path,case):
    root,sid,path,report=source(tmp_path)
    if case=='wrong_seed':report['world_identity']['seed']='9'
    if case=='wrong_image':report['controls']['image_id']='sha256:'+'0'*64
    if case=='false_cleanup':report['clean_shutdown']=False
    if case=='string_cleanup':report['clean_shutdown']='true'
    if case=='empty_response':report['status']='SUCCESS'
    if case=='wrong_source':report['controls']['prediction']['observation_id']='0'*64
    if case=='wrong_command':report['queries'][0]['command_id']='shipwreck'
    if case=='outside_source':report['queries'][0]['query']=[5000,5000]
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError):collect(root,sid,[path])
