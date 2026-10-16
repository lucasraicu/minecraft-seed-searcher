# UI settings → machine execution

Date: 2026-10-15. Status: **implemented and verified on the working tree**. This records the UI parity follow-up after the [remaining audit fixes](../remaining-fixes-2026-10-15/IMPLEMENTATION.md); historical audit reports and manifests remain snapshots of their respective versions.

## Delivered behavior

| UI setting or action | Machine behavior |
|---|---|
| Search policy | Resolves the selected validated backend profile; switching profiles restores that profile's targets, geometry, required biomes, and default deficit budget. |
| Structure target counts | Every displayed target is explicitly included in the request, including unchanged defaults. Edited counts reach the saved YAML and evaluator configuration. Fixed targets are disabled; editable targets respect policy floors and the count ceiling. |
| Seed count and starting index | Become `--count` and `--start-index`. The index stays a decimal string across JavaScript/JSON so values above JavaScript's safe integer limit remain exact. Range overflow is rejected. |
| Deficit budget | Becomes `--max-misses` and is validated against the selected policy. |
| Native threads and batch size | Become `--native-threads` and `--native-batch-size`, with the same UI/backend bounds. |
| Machine command preview | Debounced preview uses the same UI request builder, backend policy resolver, and command builder as launch. Stale previews are hidden on edits. Preview validates settings without creating a run or starting native work. Build and disk checks occur at launch. |
| Actual launch | Saves `policy.yaml` and `launch.json`, including exact argv, working directory, required `PYTHONPATH`, shell command, resolved policy, and controls. The command card exposes these values and a copy button. |
| Pause/resume and page refresh | Active/paused/verification jobs lock search edits. Resume uses the checkpoint's saved policy and controls; the UI restores those settings and shows the resume command. The latest launch receipt is reloaded when selecting a run. |
| Fixed policy and display controls | Unsupported planning knobs have been replaced with read-only policy information. Map/result-view controls are explicitly display-only. |

The preview command is a **template** containing `<new-run>`; launch assigns the directory and creates its policy file. The actual command is copyable with its real paths and environment, including when invoked from another working directory. Reusing an executed command does not bypass existing fresh-run or computation-identity checks; interrupted work should use its resume command. `launch.json` records the latest scan/resume invocation, not a full invocation history.

Profile editability and required-biome metadata are generated from backend configuration and its validator by `scripts/export_web_policy.py`. This avoids maintaining a separate UI interpretation of editable targets. No native scoring, climate logic, automatic terrain screening, or BDS scheduling was added for this task.

## Verification

- **Full Python suite: 1,120 passed in 363.71 seconds** ([log](pytest.log)).
- **Actual TypeScript UI/helper checks: 9 passed** ([log](ui-handlers.log)); these are also exercised by the Python suite's Node wrapper.
- **Production web build: passed** ([log](web-build.log)).
- **Web lint: passed without warnings** ([log](web-lint.log)).
- `git diff --check`: passed.

The new integration test constructs a request with the actual TypeScript helper, posts it through HTTP preview/start, compares the captured process argv/environment and saved YAML against the UI values, and executes the copied command from another directory. It scans one input, then resumes to three total using the saved settings. It verifies exact starting index `9007199254741001`, edited Overworld/Nether targets, one thread, batch size two, and deficit budget one against the real native CLI and SQLite checkpoint. Five invalid-input cases verify that preview and start reject identically without creating runs. All test runs use temporary directories.

This establishes configuration and command parity, including real native execution and resume. The component checks execute handlers/rendered trees without a full browser session; they do not certify visual layout. Small native test runs do not establish production throughput or actual generated-world correctness.

Source and evidence hashes are retained in [manifest.json](manifest.json).
