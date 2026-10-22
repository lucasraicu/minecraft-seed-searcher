# Repository map

Current locally adopted catalog release: [variant controls and organization](../reviews/variant-controls-and-organization-2026-10-22/RELEASE_REPORT.md).
Both predicted variants are enabled. The [prior biome expansion](../reviews/biome-expansion-plan-2026-10-22/RELEASE_REPORT.md)
remains preserved release evidence. Eight approved documents moved; no evidence deleted.

- [Pre-GPU readiness plan](PRE_GPU_READINESS_PLAN.md).
- [Quickstart](../README.md), [agent rules](../AGENTS.md), [operational handoff](../CODEX_HANDOFF.md).
- [Seed blueprint](../MASTER_SEED_BLUEPRINT.md), [server deployment guide](../SERVER_SETUP_GUIDE.md).
- [Organization plan](../REPO_ORGANIZATION_PLAN.md), [variant proposal](../reviews/variant-controls-and-organization-2026-10-22/VARIANT_VALIDATION_PROPOSAL.md).
- [Catalog v1](catalog/v1/README.md), [catalog v3](catalog/v3/README.md), [accuracy notes](catalog/ACCURACY.md).
- [Scripts](../scripts/README.md), [tests](../tests/README.md), [reviews/evidence](../reviews/README.md).
- [Historical handoff](archive/CODEX_HANDOFF_ARCHIVE_20261022.md).
- [Catalog architecture and interfaces](specs/CATALOG_WEB_ARCHITECTURE_AND_INTERFACE_SPEC.md), [architecture diagrams](specs/DIAGRAMS.md).
- [Archived 1664 blueprint](blueprints/archive/MASTER_SEED_BLUEPRINT_1664_V2.md), [preserved audit context](audits/AUDIT_CONTEXT.md).
- [Platform specification](specs/MASTER_PLATFORM_SPECIFICATION.md), [dual-harvest architecture](specs/DUAL_HARVEST_GPU_CATALOG_ARCHITECTURE.md).
- [Player policy](catalog/PUBLIC_CATALOG_PLAYER_POLICY.md), [catalog master proposal](catalog/proposals/Public_Catalog_Master_Plan.md).

`src/seed_search`, `native` and `vendor` keep their established paths. Frozen JSON
contracts, fixtures, build fingerprints and historical evidence are not relocated.
Live runs, SQLite/WAL/checkpoints, native binaries, external catalog roots and
recovery snapshots are protected runtime data, not cleanup candidates. Navigation
categories do not authorize deletion, native rebuilds, searches or server restarts.

Current readiness execution: [report](../reviews/pre-gpu-implementation-2026-10-22/REPORT.md),
[GPU contract](gpu/GPU_CONTRACT_V1.md), [database comparison](catalog/DATABASE_COMPARISON.md).

Independent review: [Claude/Gemini audit prompt](audits/INDEPENDENT_REPOSITORY_AUDIT_PROMPT.md).
Repository publication hygiene: [scope and preservation](../reviews/repository-publication-2026-10-22/REPORT.md).
