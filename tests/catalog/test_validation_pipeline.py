"""Integrated CLI stage from saved synthetic observations, with no extraction."""
from scripts import catalog_validate as cli
from seed_search.catalog.validation_contracts import controls
from seed_search.catalog.evaluation import heldout_cases
from seed_search.catalog.registry import digest
from tests.catalog.test_ingestion import make_test_build,make_complete_observation


def test_partial_pipeline_preserves_failed_and_unattempted_receipts(tmp_path,monkeypatch):
    from seed_search.catalog import ingestion
    build=make_test_build();config=controls(build);corpus=heldout_cases()
    corpus['cases']=corpus['cases'][:8];corpus['sha256']=digest(corpus['cases'])
    monkeypatch.setattr(cli,'frozen_inputs',lambda:(config,corpus))
    cli.atomic(tmp_path/'controls.json',config);cli.atomic(tmp_path/'heldout.json',corpus)
    checkpoint_map={}
    for index in range(2):
        path=tmp_path/f'cached-{index}.json'
        cli.atomic(path,make_complete_observation(config['cohort'][index],build['identity']))
        checkpoint_map[str(index)]=path.name
    (tmp_path/'bad.json').write_text('{truncated')
    checkpoint_map['2']='bad.json';cli.atomic(tmp_path/'checkpoint-map.json',checkpoint_map)
    receipts=[dict(index=i,seed=seed,status='complete' if i<2 else ('failed' if i==2 else 'pending'))
              for i,seed in enumerate(config['cohort'])]
    def fake_ingest(*_,**kwargs):
        return dict(controls=config,receipts=receipts,summary=dict(total_seeds=100,completed=2,
            failed=1,pending=97,partial=0,active=0,stopped_reason='injected_test_stop'))
    monkeypatch.setattr(ingestion,'ingest',fake_ingest)
    assert cli._pipeline(tmp_path)==2
    report=cli.load(tmp_path/'report.json')
    assert report['status']=='partial' and report['worlds']==2 and report['layouts']==486
    assert report['ingestion_summary']['completed']==2
    assert len(report['missing_indices'])==97 and report['invalid_checkpoints'][0]['index']==2
    assert report['backup_restore'] and report['partition_merge_parity'] and report['retention_oracle_parity']
    assert report['experiments']['defaults']['retained_unqueryable_worlds']==98
    assert report['synthetic']['discriminating'] and report['synthetic']['retained_queryable_worlds']<64
