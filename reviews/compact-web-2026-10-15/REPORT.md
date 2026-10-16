# Compact web scans at billion-seed scale

Web launches already used --retention survivors. The input-count-based whole-run projection imposed an artificial 4.29-billion-input limit despite compact storage saving only survivors and range receipts.

Compact projections are now advisory telemetry (projection_enforced=false). Actual run usage, free-space reserve, and per-prepared-write capacity checks remain enforced. Full-retention projections remain enforced. This applies to native compact startup and resume as well as web preview/launch. No blueprint predicates changed.

The dashboard labels compact retention explicitly. Rebuilt frontend and restarted idle server. Browser verified a 5,000,000,000-input validated preview and left that draft ready, without launching a sweep.

Verification: 38 relevant regression tests passed, followed by 5 focused tests including a real 5-billion-target compact CLI run stopped after 2 inputs and resumed to 4 inputs. This verifies large-range startup/checkpoint/resume, not completion of a billion-input campaign. Frontend build/lint and git diff --check passed. Low-space and actual-write cap rejection remain tested; full-mode projection boundaries remain tested.
