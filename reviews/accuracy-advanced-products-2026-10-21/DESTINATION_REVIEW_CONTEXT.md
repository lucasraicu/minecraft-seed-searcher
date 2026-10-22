# Final migration destination integration review
User approved catalog migration while preserving personal backend. Old configured catalog root remains unchanged; new policy gets a disjoint root and catalog backend adopts it. Without explicit routing, blank public folder in Sweep would use old personal server environment. These actual snippets fix that without restarting personal backend. Explicit user folder always wins; personal-only adds no GET. Only opt-in preview/start resolves root; preview already posts harmless receipt requests.

Checks Codex ran: real network module19PASS includes manual folder, personal-only/no fetch, configured currentroot lookup, failure and abort; Python HTTP12PASS; frontend TypeScript/VitePASS. Interactive browser QA remains waived.

```ts
/** Resolve the serving catalog's policy workspace without changing personal defaults. */
export async function resolvePublicCatalogRoot<T extends {catalogEnabled?: boolean; catalogRoot?: string}>(
  payload: T, options: {signal?: AbortSignal; fetchFn?: typeof fetch} = {},
): Promise<T> {
  if (!payload.catalogEnabled || payload.catalogRoot?.trim()) return payload;
  const {data} = await requestJson<{ok: boolean; configured: boolean; catalog_root?: string}>(
    '/api/catalog/automation-status', {method: 'GET', timeoutMs: 8000, ...options},
  );
  if (!data?.ok || !data.configured || typeof data.catalog_root !== 'string' ||
      !data.catalog_root.startsWith('/') || data.catalog_root.length > 4096 || data.catalog_root.includes('\0'))
    throw new Error('Choose a configured public catalog folder before enabling public harvesting.');
  return {...payload, catalogRoot: data.catalog_root};
}
```
```tsx
import { FunnelModal } from './components/FunnelModal';
import { buildSweepRequest } from './utils/sweep';
import {
  requestJson,
  resolvePublicCatalogRoot,
  TimeoutError,
  calculateBackoff,
  determineConnectionStatus,
  isResponseStale,
  validStatusPayload,
  validCandidatePage,
  snapshotMismatch,
} from './utils/network';

const VALID_TELEMETRY_STATUSES: TelemetryState['status'][] = [
  'idle',
  'running',
  'paused',
  'completed',
```
```tsx

  const previewKey = JSON.stringify(request.body);
  useEffect(() => {
    if (!request.body) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const result = await requestJson<{ ok: boolean; launch?: LaunchReceipt; error?: string }>(
          '/api/sweep/preview',
          {
            method: 'POST',
            body: await resolvePublicCatalogRoot(request.body, {signal: controller.signal}),
            timeoutMs: 5000,
            signal: controller.signal,
          }
        );
        if (controller.signal.aborted) return;
        const data = result.data;
        setPreview({
          key: previewKey,
          receipt: data?.ok ? data.launch ?? null : null,
          error: data?.ok ? '' : data?.error || 'Preview failed',
        });
      } catch (error) {
        if (!controller.signal.aborted) {
          setPreview({
            key: previewKey,
            receipt: null,
            error: error instanceof Error ? error.message : String(error),
          });
        }
      }
    }, 300);
    return () => {
      clearTimeout(timer);
      controller.abort();
```
```tsx
  }, []);

  const handleToggleSweep = useCallback(async () => {
    try {
      if (telemetry.status === 'running' || telemetry.status === 'paused') {
        await postCommand('/api/sweep/stop');
        setTelemetry((prev) => ({ ...prev, status: 'idle', seedsPerSec: 0 }));
        showToast('Sweep stopped; checkpoint retained');
        return;
      }
      const data = await postCommand('/api/sweep/start', await resolvePublicCatalogRoot(buildSweepRequest(config)));
      applyLaunch(data, true);
      setTelemetry((prev) => ({
        ...prev,
        status: 'running',
        runId: data.runId,
```
```python
def get(handler,catalog=None):
    url=urlparse(handler.path);path=url.path
    if not path.startswith('/api/catalog/'):return False
    catalog=catalog or service()
    def operation():
        if path=='/api/catalog/status':return catalog.status()
        if path=='/api/catalog/automation-status':
            from ..catalog.automation import status
            return dict(ok=True,catalog_root=str(catalog.root) if catalog.root else None,
                        **(status(catalog.root) if catalog.root else dict(configured=False,state='unconfigured')))
        if path=='/api/catalog/capabilities':return catalog.capabilities()
        if path=='/api/catalog/products':
            params=parse_qs(url.query,keep_blank_values=True)
            if set(params)-{'snapshot_id'} or ('snapshot_id' in params and len(params['snapshot_id'])!=1):
                raise ServiceError('Expected one optional snapshot_id')
            return catalog.products(params['snapshot_id'][0] if 'snapshot_id' in params else None)
        if path=='/api/catalog/snapshots':return catalog.snapshots()
        if path=='/api/catalog/detail':
            params=parse_qs(url.query,keep_blank_values=True)
            if set(params)!={'snapshot_id','world_id','layout_id'} or any(len(v)!=1 for v in params.values()):
                raise ServiceError('Expected one snapshot_id, world_id and layout_id')
            return catalog.detail(params['snapshot_id'][0],params['world_id'][0],params['layout_id'][0])
        raise ServiceError('Unknown Catalog endpoint','not_found',404)
    _call(handler,operation);return True

```
