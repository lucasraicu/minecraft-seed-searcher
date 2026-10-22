# Versioned derivation compatibility correction

The initial full-record AFTER attempt stopped at configuration validation before
extraction because editing summaries.py changes the source-bound policy identity.
Its result/log and 0.993 seconds are retained and charged; the previous completed
35.153-second BEFORE trial is reused, not discarded.

Original summaries.py was restored byte-for-byte from the task baseline, preserving
all inherited changes. The optimized implementation is additive summaries_fast.py.
New V3 workspaces bind revision catalog-derivation-v3-int64-v1 plus its SHA256 in
configuration.options.derivation. That option participates in the existing policy
hash. Configuration rejects a changed accelerator source. Existing roots keep their
original options and implementation, with no implicit upgrade or budget reset.
Native extraction receives only its existing pinned native/spawn options.

Live automation-status was briefly fail-closed while the original source was edited;
it returned 200/paused again after restoration. No process, live configuration,
ledger, observation, snapshot or consumed budget was changed. This intermediate
failure is retained rather than presented as uninterrupted API availability.

The new policy identity intentionally differs. A complete frozen-observation replay
matches world artifacts, extensions, summaries, memberships, product statuses and
generation exactly after excluding only that explicit policy revision field. See
FIXED_REPLAY_PARITY.json. No old snapshot identity is rewritten.
