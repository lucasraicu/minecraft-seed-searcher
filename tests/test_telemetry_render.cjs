// Render the actual component with the project's existing hook-aware TS loader.
const assert = require('node:assert/strict');
const { load, root } = require('./web_test_loader.cjs');
const { renderToStaticMarkup } = require(root + '/web-ui/node_modules/react-dom/server');
const { TelemetryBar } = load(root + '/web-ui/src/components/TelemetryBar.tsx');
const telemetry = {
  status: 'running', runId: 'fixture', seedsPerSec: 42, totalScanned: 10,
  targetCount: 100, candidatesFound: 2, elapsedSeconds: 1, currentStage: 'fixture',
  memoryRssGib: null, activeThreads: null, sweepProgress: 10, history: [42],
};
for (const dataMode of ['connecting', 'live', 'stale', 'disconnected']) {
  const html = renderToStaticMarkup(TelemetryBar({
    telemetry, dataMode, lastContactTime: Date.now(),
    runtimeIdentity: { pid: 123, processStartedAt: Date.now() / 1000,
      loadedServerSourceSha256: 'a'.repeat(64),
      nativeBuild: { path: 'fixture', digest: 'b'.repeat(64), source: 'selected_on_disk' } },
    onToggleSweep() {}, onOpenFunnel() {}, onExport() {},
  }));
  assert.ok(html.includes(dataMode.toUpperCase()), dataMode);
  assert.ok(!html.includes('NaN'), 'Single-point sparkline must remain finite');
  assert.ok(!html.includes('[object Object]'), 'Runtime metadata must be formatted');
  if (dataMode === 'stale') assert.ok(html.includes('seeds/s (stale)'));
  if (dataMode === 'disconnected') assert.ok(html.includes('seeds/s (offline)'));
}
console.log('4 telemetry rendering states passed, including finite single-point history');
