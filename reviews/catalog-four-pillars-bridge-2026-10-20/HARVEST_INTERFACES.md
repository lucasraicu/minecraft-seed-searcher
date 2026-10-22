# Approved queue interfaces for Stage C

Read approved PLAN.md for budget/durability behavior. New files ONLY
catalog/harvest.py, catalog/harvest_worker.py, tests/catalog/test_harvest.py.
Codex owns CLI/native wiring and real native child/publisher adapter.

harvest.py:
DEFAULT_CAPS = dict(sample_cap=100,pending_cap=100,world_seconds=120,
 total_seconds=600,rss_bytes=4<<30,output_bytes=2<<30,max_attempts=3).
Only lower positive limits allowed in first milestone. descriptor version
'catalog-harvest-v1'; immutable canonical JSON with digest campaign_id,
search (permutation/sequential/strided/manifest, includes run_key/low32/manifest),
start/count unsigned decimal strings, observation identity template seed='0',
personal_identity_sha256, root absolute, caps, sampling offset0/stride
max(1,ceil(count/sample_cap)); samples at start+i*stride while index<start+count.
Use realm.runner._seed for exact supported sequence semantics without native
calls. Validate all preflight, signedseed decimal strings, full64 bounds.

make_descriptor(search,start,count,observation_identity,personal_identity_sha256,
 root,*,caps=None)->dict. Validate unsupported/oversized input (manifest<=10000,
 totaldescriptor<=1MiB), count0 allowed, no filesystem mutation here.
write_descriptor(spool_dir,descriptor)->Path: atomic/fsync create if absent or
verify exact equivalent existing; no overwrite different bytes; reject symlinks
all ancestors. Use <campaign_id>.json. Durable spool before personal launch.

HarvestQueue(root,*,busy_ms=5000) contextmanager owns separate harvest.sqlite;
reject personal DB names/tables and symlinks. WAL/synchronousFULL/shorttransactions.
Local publisher flock 'harvest.lock' used by ALL lease changes/claims/acks and
publication ownership context. Never signal external/recycled PID.
- register(descriptor): idempotent campaign; root must match queue root.
- expand(): lazy up to pending_cap globally pending/leased/retryable; remaining
  sampled ranges persist cursor. Duplicate full identity never creates extra job.
- claim(worker_id,*,now=None,lease_seconds=150)->job|None. Leased job includes
  task_id,campaign_id,seed,identity,generation,worker_id,checkpoint/caps,attempt.
  Store process start identity/heartbeat, stale expiry reclaim fencesgeneration.
  max3attempts, retry backoff bounded; record terminalfailed not endlessretry.
- heartbeat(job,*,now=None): requires matching token.
- publication(job) contextmanager holds lock, validates unexpired matching token;
  caller publishes within it then acknowledge(job,snapshot_id) (no deadlock).
- acknowledge(job,snapshot_id), fail(job,reason,*,partial=False,now=None),
  defer(job,reason): guarded generation; immutable/bounded diagnostics.
- set_campaign_state(campaign_id,state): pause/resume/cancel only owncampaign;
  define impact on already leased jobs and fence cancellation. No other campaign
  sharing an idempotent world job may be silently cancelled.
- status()->JSON dict campaigns/jobs counts/cursors/reasons, no fake progress.
  make recovery from descriptor alone explicit registration command.

Keep schema simple enough to test concurrent queues. Validate IDs/path boundaries,
source/model/extractor identity conflicts; process leases never accepted from
stale generation. Publication idempotency handled by Codex publisher lookup before
publish, queue acknowledgement may replay after crash.

harvest_worker.py:
drain(queue,extract,publish,*,max_worlds=100,clock=time.monotonic)->dict.
extract(job,remaining_seconds)->validated complete observation dict OR raise.
publish(job,obs)->snapshot_id called only inside queue.publication(job).
Extract checkpoints private queue-root/staging; never query partial artifacts.
Use jobcaps and max_worlds; failures record retry/stop reasons. Queue may keep
partial checkpoint for compatible resume. Do not busy loop on backoff/emptyqueue.
Resource-aware actual subprocess adapter owned by Codex; injected tests don't
pretend to establish native RSS/time compliance. Return completed/failed/deferred,
stop_reason and elapsed. No new real seed extraction or other code changes.

Tests with fake identity/clock/extractor: sequence/parity endpoints/seeds64,
descriptor corruption/pathsymlink, cap validation, pendingcap+cursor, duplicate
registration, two queue connections, generationexpiry/cancel, publication lock,
ackfail/replay, backoff/attempts, pause/resume/cancel and budget/defer. No tools
or commands from agent; built-in file tools only; bridge runs declared tests.
