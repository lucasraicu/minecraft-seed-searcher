# Reference recovery procedure

Private reference root: `~/.local/share/antigravity-worker-mcp/pre-gpu-readiness-approved-20261022`.
The source archive, original metadata and copied catalog are retained. Check archive
SHA and SOURCE_HASHES before using them. This is a same-host reference; compiled
binaries are not claimed portable across operating systems or CPU architectures.

1. Extract source-before.tar.gz into a fresh destination. Verify all978 source/build
   files against SOURCE_HASHES.json before importing. Use the recorded Python3.13.15,
   dependency versions/lockfiles and native compiler/build identities.
2. Native build metadata contains an absolute extension locator. Preserve the original
   identity file, clone the copied build into a new private directory, and rebind only
   its extension locator to that copied extension. Keep extension/content/source and
   runtime hashes unchanged. `restore_native_smoke.py` demonstrates this and verifies
   the catalog source and custom native module both load from the isolated copy.
   The native import guard remains enabled; no binary is patched or recompiled.
3. The Mach-O binaries also depend on the declared absolute OpenMP runtime location.
   Its SHA is verified and a copy is retained as runtime-libomp.dylib. The pinned
   spawn-estimator executable is also copied as world-spawn-reference. On disaster
   recovery, restore missing dependencies to their declared paths from verified copies;
   never overwrite an active binary. Moving dependency/configuration locators changes
   a source-bound policy and requires an explicit new namespace rather than bypassing
   the policy check. The current host's existing dependencies were not replaced.
4. Restore the copied catalog with its entire CAS, immutable bindings, configuration,
   queues and consistent SQLite backups. Do not copy a live main database separately
   from its WAL. Original and copied snapshot IDs and all source-bound references
   must agree before serving. Preserve pins, history, reserves and verification roots.
5. The private validation-venv uses a separately built CPython-matched SQLite3.54.1
   adapter, with source hashes/argv in SQLITE_PRIVATE_RUNTIME.json. Its .pth processes
   the original environment's editable-package hooks and loads the private adapter
   for parent/child interpreters. Recreate dependencies and paths explicitly when
   restoring elsewhere; do not silently relink or downgrade a live interpreter.
6. Run import/native smoke, metadata/hash checks, fixed-observation/query oracles and
   relevant recovery tests before any controlled activation. No such activation or
   live personal/public restart was performed by this task.

Initial packaged-native imports passed. A supplemental custom-build import exposed
its absolute locator; direct relocation correctly failed the guard. The explicit
copied-metadata relocation then passed, with the original archive and all content
hashes unchanged. See RESTORE_NATIVE_SMOKE.json.
