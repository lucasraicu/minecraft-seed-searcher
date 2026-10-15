# Website sweep controls

Open http://localhost:3000 and choose **Xeon Hardware**. Enter a whole seed count and an exact decimal starting index. Runs above 100,000 are supported, subject to the saved memory and disk budgets. Count is limited to JavaScript's safe integer range; starting indices retain full64 precision. Default execution is the validated private native build at 34 threads / 16,384 seeds per batch / B=2.

Use **Refresh runs**, select a saved incomplete compatible web run, then **Resume with saved settings**. Resume preserves its range, policy, retention, batch settings and native identity; it does not apply current new-run controls. Changed computation identities and incompatible builds are rejected. Resume throughput counts only newly completed inputs.

**Blueprint Targets** shows supported live structure ideals with fixed fatal floors and categories. Optional biome, terrain, spawn, overlap and category planning controls are in a separate **Show separate planning estimates** view; these do not change live qualification. Deferred marine and actual-world evidence stay pending. This does not add unsupported filters to the fixed v2 policy.

Verification: frontend production build and lint passed; 10 focused API tests passed. Browser smoke tested a three-input run with exact index `9007199254740993`, and actual resume from 3 to 20 inputs with exact checkpoint coverage and SQLite integrity. No large production sweep was started.
