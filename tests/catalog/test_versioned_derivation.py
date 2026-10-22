"""Additive optimization must never rewrite an existing source-bound policy."""
import copy
import pytest
from seed_search.catalog import automation,spawn_estimator,harvest_native
from seed_search.catalog.models import identity
from seed_search.catalog.registry import REGISTRY_V3,digest
from seed_search.catalog.retention import automation_policy_revision_v3
from seed_search.catalog.ingestion import atomic_json
from test_expansion_storage import observation,extension
from seed_search.catalog.summaries import summarize_v2,summarize_v3
from seed_search.catalog.summaries_fast import summarize_v3 as fast


def setup(monkeypatch):
 monkeypatch.setattr(spawn_estimator,'SpawnEstimator',lambda **kw:None)
 monkeypatch.setattr(harvest_native,'realm_runtime_pin',lambda *a,**kw:{'test_sha256':'f'*64})
 return identity('0',model_id='MC_26_50',native_sha256='a'*64,source_sha256='b'*64),dict(spawn=dict(executable='/mock',binary_sha256='c'*64,source_sha256='b'*64))


def test_new_policy_pins_accelerator_and_rejects_changed_source(tmp_path,monkeypatch):
 ident,options=setup(monkeypatch);automation.configure(tmp_path,ident,options,catalog_registry=REGISTRY_V3)
 cfg=automation.configuration(tmp_path);assert cfg['options']['derivation']==automation.derivation_pin()
 old=copy.deepcopy(cfg);automation.configure(tmp_path,ident,options,catalog_registry=REGISTRY_V3)
 assert automation.configuration(tmp_path)==old
 monkeypatch.setattr(automation,'derivation_pin',lambda:{'revision':'catalog-derivation-v3-int64-v1','source_sha256':'0'*64})
 with pytest.raises(ValueError,match='Derivation source differs'):automation.configuration(tmp_path)


def test_existing_legacy_policy_is_not_silently_upgraded(tmp_path,monkeypatch):
 ident,options=setup(monkeypatch);automation.configure(tmp_path,ident,options,catalog_registry=REGISTRY_V3)
 cfg=automation.configuration(tmp_path);cfg['options'].pop('derivation')
 cfg['policy_revision']=digest([automation_policy_revision_v3(registry=REGISTRY_V3),ident,cfg['options'],cfg['policy_contract'],digest(REGISTRY_V3)])
 legacy=tmp_path/'legacy'
 from seed_search.catalog.store import AutomationStore
 assert AutomationStore(legacy).artifacts.put_json(REGISTRY_V3)==cfg['registry_artifact']
 atomic_json(automation._configuration_path(legacy),cfg)
 from seed_search.catalog.harvest import HarvestQueue
 with HarvestQueue(legacy)as q:
  ledger=automation._ledger(q,cfg)
  prior=ledger.generation()
 automation.configure(legacy,ident,options,catalog_registry=REGISTRY_V3)
 assert automation.configuration(legacy)==cfg and 'derivation'not in cfg['options']
 with HarvestQueue(legacy)as q:assert automation._ledger(q,cfg).generation()==prior


def test_fast_derivation_full_summary_parity_extension_groups_and_base_summaries():
 obs=observation();obs['biomes']['overworld'] += [[x,63,64,4]for x in range(-4096,4096,64)]
 ext=extension(obs);base=summarize_v2(obs)
 for kwargs in ({},{'extension':ext},{'extension':ext,'base_summaries':base}):
  assert fast(obs,**kwargs)==summarize_v3(obs,**kwargs)
