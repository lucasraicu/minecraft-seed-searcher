# Integrated public UI source review

Gemini High task a20316b6c0e9 succeeded, providerexit0, denied_actions empty.
Static source review only; interactive browser QA was waived by the user.

Codex verified and addressed the four findings: optional product dereference,
coordinate-based Nether witness keys, missing queue.jobs fallback, and missing
witness.feature type validation. Product prop is required and the caller already
selects an actual product; the optional guard is defensive rather than evidence
of an observed production crash. Current backend emits one summary witness per
feature, but coordinate keys also remain correct if that expands.

Codex additionally requires witness observation identity, witness SHA, nonempty
provider and exact squared distance from the same dimension-specific anchor.
Malformed-source regression mutations pass; original 20-row signed64 response
and all 14 actual product render/decoder checks pass. TypeScript/Vite build passes.
Legacy pillar interaction loader now accommodates the added component import and
Gated badge; its real focus/close/copy/stale-response checks pass unchanged.

These checks establish source and automated-render behavior, not visual layout,
DOM focus in a real browser or real clipboard permissions. Larger P1 activation
remains a separate measured calibration gate.
