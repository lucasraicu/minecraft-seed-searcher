"""Add navigation indexes only; never move, rename or delete a payload."""
from pathlib import Path
from urllib.parse import quote
root=Path(__file__).resolve().parents[2]
def put(name,text):
 p=root/name
 if p.exists():raise FileExistsError(name)
 p.write_text(text)
def link(path,label=None):return f'[{label or path.name}]({quote(path.as_posix())})'
put('docs/REPOSITORY_MAP.md','''# Repository map

Current release: [biome expansion report](../reviews/biome-expansion-plan-2026-10-22/RELEASE_REPORT.md).
The release is completed and adopted. Variant controls and structural organization
are separate ongoing work; neither feature gate is cleared by a navigation index.

- [Quickstart](../README.md), [agent rules](../AGENTS.md), [operational handoff](../CODEX_HANDOFF.md).
- [Seed blueprint](../MASTER_SEED_BLUEPRINT.md), [server deployment guide](../SERVER_SETUP_GUIDE.md).
- [Organization plan](../REPO_ORGANIZATION_PLAN.md), [variant proposal](../reviews/variant-controls-and-organization-2026-10-22/VARIANT_VALIDATION_PROPOSAL.md).
- [Catalog v1](catalog/v1/README.md), [catalog v3](catalog/v3/README.md), [accuracy notes](catalog/ACCURACY.md).
- [Scripts](../scripts/README.md), [tests](../tests/README.md), [reviews/evidence](../reviews/README.md).
- [Historical handoff](archive/CODEX_HANDOFF_ARCHIVE_20261022.md).

`src/seed_search`, `native` and `vendor` keep their established paths. Frozen JSON
contracts, fixtures, build fingerprints and historical evidence are not relocated.
Live runs, SQLite/WAL/checkpoints, native binaries, external catalog roots and
recovery snapshots are protected runtime data, not cleanup candidates. Navigation
categories do not authorize deletion, native rebuilds, searches or server restarts.
''')
groups={}
for p in sorted((root/'scripts').iterdir()):
 if not p.is_file():continue
 n=p.name
 category=('Build/fingerprint-sensitive tools' if n.startswith('build_') else 'Catalog and migration' if n.startswith(('catalog_','migrate_','reanchor_','reindex_','import_catalog')) else 'Generalization' if n.startswith('generalization_') else 'Calibration and metrics' if any(w in n for w in ('calibrat','player_metric')) else 'BDS and predictor diagnostics' if n.startswith(('bds_','predictor_','validate_spawn')) else 'Other utilities — inspect ownership before changes')
 groups.setdefault(category,[]).append(p)
text='# Script navigation\n\nPaths remain unchanged. These are navigation categories, not a finding that tools\nare obsolete or safe to move. Builders may fingerprint their own path/source;\nrecovery CLIs and observer assets have import and adjacency dependencies.\nSee [the organization plan](../REPO_ORGANIZATION_PLAN.md).\n'
for category,files in groups.items():text+='\n## '+category+'\n\n'+'\n'.join('- '+link(Path(p.name)) for p in files)+'\n'
put('scripts/README.md',text)
text='# Test navigation\n\nKeep existing locations and invocation forms. Sibling imports, `__file__` root\ndiscovery and CJS `__dirname` assumptions must be checked before relocation.\nPytest already discovers `tests/` through `pyproject.toml`.\n\nCatalog: `.venv/bin/python -m pytest tests/catalog`\n\nNode checks use `node tests/<name>.cjs` from the repository root. No new runner,\nfixture split or collection behavior is introduced by this index.\n'
for title,files in [('Root Python tests/support',sorted((root/'tests').glob('*.py'))),('Root Node/UI contracts',sorted((root/'tests').glob('*.cjs'))),('Catalog tests',sorted((root/'tests/catalog').glob('test_*.py')))]:
 text+='\n## '+title+'\n\n'+'\n'.join('- '+link(p.relative_to(root/'tests')) for p in files)+'\n'
put('tests/README.md',text)
text='''# Reviews and evidence navigation

The [completed biome release](biome-expansion-plan-2026-10-22/RELEASE_REPORT.md)
includes activation controls, final migration and reserve audits, HTTP acceptance,
preservation hashes and Gemini/Codex reconciliations. Preserve its complete chain,
including failed intermediate attempts and portable fixture manifests.

[Current variant/organization work](variant-controls-and-organization-2026-10-22/VARIANT_VALIDATION_PROPOSAL.md)
is a separate proposal. Directory age is not evidence that its contents can be
removed. The list below changes navigation only; no review has moved or been deleted.
Entries link to an available entry document where one exists; status must be read
from the actual report, not inferred from the directory name.

## Existing review directories

'''
for p in sorted((root/'reviews').iterdir()):
 if not p.is_dir():continue
 target=next((p/n for n in ('RELEASE_REPORT.md','FINAL_REVIEW.md','README.md','RECONCILIATION.md','PLAN.md') if (p/n).is_file()),p)
 text+='- '+link(target.relative_to(root/'reviews'),p.name)+'\n'
put('reviews/README.md',text)
print('Created four navigation indexes; no payload moved/deleted.')
