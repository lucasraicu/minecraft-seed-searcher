"""Offline integrity/prediction/signature replay; never starts Bedrock or a search."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tarfile
import tempfile

HERE=Path(__file__).resolve().parent
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def main():
    manifest=json.loads((HERE/'MANIFEST.json').read_text());archive=HERE/'variant-controls.tar.gz';assert sha(archive.read_bytes())==manifest['archive_sha256']
    files={}
    with tarfile.open(archive)as tar:
        members=tar.getmembers();assert len(members)<=512
        for member in members:
            assert member.isfile()and not member.name.startswith('/')and'..'not in Path(member.name).parts and member.name not in files
            raw=tar.extractfile(member).read();expected=manifest['members'][member.name]
            assert len(raw)==expected['bytes']and sha(raw)==expected['sha256'];files[member.name]=raw
    assert set(files)==set(manifest['members'])and sum(map(len,files.values()))==manifest['total_uncompressed_bytes']
    load=lambda name:json.loads(files[name])
    protocol=load('protocols/FROZEN_PROTOCOL.json');budget=load('budget/BDS_BUDGET.json');assert budget['charged_seconds']<=1200 and budget['active']is None and len(budget['attempted'])==8
    amendment=load('protocols/IGLOO_REQUEST_AMENDMENT_APPROVAL.json');assert amendment['approval']=='Approve the two additional 59-block requests'
    templates={r['path']:r for r in load('templates/IGLOO_TEMPLATES.json')}
    for row in templates.values():assert sha(files['templates/'+row['path']])==row['sha256']
    def validate_report(report,console,case):
        assert report['case']==case and report['status']=='observed'and report['clean_shutdown']and report['owned_container_removed']and report['save_confirmed']and report['build_verified']
        assert report['identity']==dict(seed=case['seed'],api='2.10.0',players=0)
        assert re.search(rb'\bVersion: 1\.26\.52\.3(?:\s|$)',console)
        assert report['settings_sha256']==sha(files[f'cases/{case["id"]}/server.properties'])
    with tempfile.TemporaryDirectory()as tmp:
        module_path=Path(tmp)/'recognize_variants.py';module_path.write_bytes(files['source/recognize_variants.py']);spec=importlib.util.spec_from_file_location('portable_variant_recognizer',module_path);rv=importlib.util.module_from_spec(spec);spec.loader.exec_module(rv)
        static=rv.static_checks(templates);out=[]
        for case in protocol['cases']:
            idx=case['id'];obs=load(f'observations/{idx}.json');assert sha(canonical(obs))==case['observation_id']and obs['identity']['seed']==case['seed']
            if case['feature']=='igloo_basement':
                inv=obs['realm']['inventory']['igloo_basement'];assert case['start']in obs['structures']['structure.igloo'];assert (case['start']in inv['points'])is case['predicted']
                if not case['predicted']:assert inv['status']=='complete'
            else:
                assert [*case['start'],case['predicted_variant']]in obs['realm']['inventory']['bastion_variant']['points']
            if idx in(0,3,4):
                report=load(f'followups/{idx}/report.json');validate_report(report,files[f'followups/{idx}/console.log'],case)
                assert report['cumulative_world_seconds']<=180 and report['cumulative_world_requests']<=(9 if idx in(3,4)else 8)
                assert report['followup_provenance']['original_report_sha256']==sha(files[f'cases/{idx}/report.json'])
                assert report['followup_provenance']['archive_sha256']==sha(files[f'prior-worlds/case-{idx}.tar.gz'])
                if idx in(3,4):assert len(report['results'])==1 and report['results'][0]['blockReads']==len(report['results'][0]['pointRows'])==59
                value=rv.igloo(rv.from_report(report),templates)['value']
            else:
                report=load(f'cases/{idx}/report.json');validate_report(report,files[f'cases/{idx}/console.log'],case)
                entities=load('saved-basement-proof/entities.json'if idx==2 else f'cases/{idx}/entities.json')
                for path,digest in entities['source_hashes'].items():assert sha(files[f'worlds/{idx}/'+path])==digest
                if idx==2:
                    proof=load('saved-basement-proof/report.json');assert proof['provenance']['source_report_sha256']==sha(files['cases/2/report.json'])
                    value=rv.igloo_positive_entities(entities['entities'],templates,case['start'])['value']
                else:
                    assert report['locate_matches_frozen_start'];value=rv.bastion(entities['entities'])['value']
            assert value is case['predicted'];out.append(dict(world=case['world_id'],feature=case['feature'],value=value))
        for feature in('igloo_basement','bastion_treasure'):
            for label in(True,False):assert len({r['world']for r in out if r['feature']==feature and r['value']is label})==2
    print(json.dumps(dict(status='PASS',members=len(files),control_worlds=len(out),static_checks=static,game_runtime_seconds=budget['charged_seconds'],archive_sha256=manifest['archive_sha256'])))

if __name__=='__main__':main()
