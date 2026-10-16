# Restored probability display and live biome selection

Restored both panels in Search targets while retaining the Run settings and Console tabs. The probability panel uses the existing historical model and explicitly identifies its estimates as uncalibrated for the sliding 1664 search.

At the user's explicit request, biome selection now changes actual v2 search requirements. The UI exposes the 13 supported Overworld palette families, defaults to all 13, supports clearing/restoring the selection, and locks controls during active/paused jobs. Historical profiles retain their fixed palettes. Optional luxury biomes remain bonuses, not additional selectable palette requirements. Nether biome requirements and Mansion Dark Forest viability remain mandatory.

Selections travel through the common preview/launch payload, server validation, saved policy.yaml, native execution, retained evidence, and resume. Unknown/duplicate family names are rejected. A new native policy mask retains canonical surface/cave bit positions even when earlier families are removed. The independent Python selector uses the same requested families with its own prefix-count implementation. Customized results qualify against the chosen palette, not necessarily the full default blueprint. README and blueprint documentation explain this distinction.

Validation:

- 105 tests passed: new live-palette tests, HTTP-to-CLI/resume contract, dynamic v1 baseline and v2 scoring suites. This includes each of the 13 missing-family cases, empty/subset/reordered selections, invalid input, and independent reference parity.
- 55 additional contract, integration, server-hardening, and audit-regression tests passed after the required native rebuild. An earlier run against the old production ABI had two expected stale-extension failures; those passed with the rebuilt artifact.
- 10 UI contract tests passed, including toggle-to-request parity, control locking, and unchanged run settings.
- TypeScript/Vite build and UI lint passed.
- Fresh PGO/LTO/OpenMP production build deployed to the default native directory and packaged extension. Source and binary hashes matched; three optimized/reference positive fixtures passed for default, empty, and mixed surface/cave selections.
- Live HTTP preview confirmed the requested palette. Browser verification showed toggling Desert changed the selected count and model estimate, validated the command preview, and preserved both Run settings and Console.

The idle web server was restarted and the browser reloaded. All 13 blueprint families were restored after interaction testing. No user sweep was launched. The current UI is shown in dashboard.png; detailed test logs and rebuild output are alongside this report.
