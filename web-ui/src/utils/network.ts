/**
 * Bounded JSON network and freshness utilities for Bedrock Seed Searcher web UI.
 */

export class NetworkError extends Error {
  readonly cause?: unknown;
  constructor(message: string, cause?: unknown) {
    super(message);
    this.name = 'NetworkError';
    this.cause = cause;
  }
}

export class TimeoutError extends NetworkError {
  readonly timeoutMs: number;
  constructor(message: string, timeoutMs: number) {
    super(message);
    this.name = 'TimeoutError';
    this.timeoutMs = timeoutMs;
  }
}

export class AbortError extends NetworkError {
  constructor(message = 'Request was aborted') {
    super(message);
    this.name = 'AbortError';
  }
}

export class HttpError extends NetworkError {
  readonly status: number;
  readonly statusText: string;
  readonly url: string;
  readonly responseBody?: unknown;
  constructor(status: number, statusText: string, url: string, responseBody?: unknown) {
    super(`HTTP ${status} ${statusText} for ${url}`);
    this.name = 'HttpError';
    this.status = status;
    this.statusText = statusText;
    this.url = url;
    this.responseBody = responseBody;
  }
}

export class MalformedResponseError extends NetworkError {
  readonly rawText?: string;
  constructor(message: string, rawText?: string, cause?: unknown) {
    super(message, cause);
    this.name = 'MalformedResponseError';
    this.rawText = rawText;
  }
}

export interface RequestJsonOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  headers?: Record<string, string>;
  body?: unknown;
  timeoutMs?: number;
  signal?: AbortSignal | null;
  fetchFn?: typeof fetch;
}

export interface RequestJsonResult<T> {
  data: T;
  status: number;
  elapsedMs: number;
  timestamp: number;
  ok: boolean;
}

/**
 * Executes a bounded HTTP JSON request with timeout deadlines and AbortController cancellation.
 * Rejects with explicit HttpError, TimeoutError, AbortError, or MalformedResponseError.
 */
export async function requestJson<T = unknown>(
  url: string,
  options: RequestJsonOptions = {}
): Promise<RequestJsonResult<T>> {
  const { method = 'GET', headers = {}, body, timeoutMs = 10000, signal,
    fetchFn = globalThis.fetch } = options;
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0 || timeoutMs > 60000) {
    throw new RangeError('Request deadline must be 1–60000 milliseconds');
  }
  if (signal?.aborted) throw new AbortError();
  const controller = new AbortController();
  const startTime = Date.now();
  let rejectCancellation!: (reason: Error) => void;
  const cancellation = new Promise<never>((_, reject) => { rejectCancellation = reject; });
  const onAbort = () => {
    controller.abort();
    rejectCancellation(new AbortError());
  };
  signal?.addEventListener('abort', onAbort, { once: true });
  const timer = setTimeout(() => {
    controller.abort();
    rejectCancellation(new TimeoutError(`Request timed out after ${timeoutMs}ms`, timeoutMs));
  }, timeoutMs);
  const operation = async (): Promise<RequestJsonResult<T>> => {
    const response = await fetchFn(url, {
      method,
      headers: { Accept: 'application/json', ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}), ...headers },
      body: body === undefined ? undefined : typeof body === 'string' ? body : JSON.stringify(body),
      signal: controller.signal,
    });
    const text = await response.text();
    let data: T;
    try { data = JSON.parse(text); }
    catch (cause) {
      if (!response.ok) throw new HttpError(response.status, response.statusText, url, text);
      throw new MalformedResponseError('Backend returned invalid or empty JSON', text, cause);
    }
    if (!response.ok) throw new HttpError(response.status, response.statusText, url, data);
    return { data, status: response.status, elapsedMs: Math.max(0, Date.now() - startTime),
      timestamp: Date.now(), ok: true };
  };
  try {
    // Race the entire body read too; a hung/mock transport cannot ignore abort
    // and permanently suppress polling or leave commandInFlight stuck.
    return await Promise.race([operation(), cancellation]);
  } catch (error: unknown) {
    if (error instanceof NetworkError) throw error;
    if (signal?.aborted) throw new AbortError();
    throw new NetworkError(error instanceof Error ? error.message : String(error), error);
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', onAbort);
  }
}

/** Reject semantic corruption before marking any telemetry as freshly received. */
export function validStatusPayload(value: unknown): boolean {
  if (!value || typeof value !== 'object') return false;
  const data = value as Record<string, unknown>;
  if (!['idle', 'running', 'paused', 'completed', 'bds_verifying', 'error', 'stopped'].includes(String(data.status))) return false;
  for (const key of ['totalScanned', 'seedsPerSec', 'elapsedSeconds', 'targetCount']) {
    if (typeof data[key] !== 'number') return false;
  }
  for (const key of ['totalScanned', 'targetCount', 'candidatesFound', 'seedsPerSec', 'elapsedSeconds', 'sweepProgress']) {
    if (data[key] !== undefined && (typeof data[key] !== 'number' || !Number.isFinite(data[key]) || (data[key] as number) < 0)) return false;
  }
  if (data.history !== undefined && (!Array.isArray(data.history) || !data.history.every(x => typeof x === 'number' && Number.isFinite(x)))) return false;
  if (data.logs !== undefined && (!Array.isArray(data.logs) || !data.logs.every(x => typeof x === 'string'))) return false;
  if (data.progressReadError !== undefined && data.progressReadError !== null && typeof data.progressReadError !== 'string') return false;
  return data.runId === undefined || data.runId === null || typeof data.runId === 'string';
}

export function validCandidatePage(value: unknown): boolean {
  if (!value || typeof value !== 'object') return false;
  const data = value as Record<string, unknown>;
  const countsValid=['primary_count','reserve_count'].every(key=>data[key]===undefined||(Number.isSafeInteger(data[key])&&(data[key] as number)>=0&&(data[key] as number)<=1000));
  if(!countsValid||(data.view!==undefined&&!['primary','reserve'].includes(data.view as string)))return false;
  return Number.isSafeInteger(data.total) && (data.total as number) >= 0 && Array.isArray(data.candidates)
    && data.candidates.every(c => c && typeof c.id === 'string' && typeof c.seed === 'string')
    && (data.runId === undefined || data.runId === null || typeof data.runId === 'string');
}

export function snapshotMismatch(
  response: { runId?: string | null; generation?: number },
  current: { runId?: string | null; generation?: number }
): boolean {
  return (current.runId !== undefined && response.runId !== undefined && current.runId !== response.runId)
    || (current.generation !== undefined && response.generation !== undefined && current.generation !== response.generation);
}

/**
 * Convenience helper returning parsed data from bounded JSON request.
 */
export async function fetchJson<T = any>(
  url: string,
  options: RequestJsonOptions = {}
): Promise<T> {
  const result = await requestJson<T>(url, options);
  return result.data;
}

/**
 * Calculates a bounded exponential backoff delay based on consecutive failure count.
 */
export function calculateBackoff(
  consecutiveFailures: number,
  baseIntervalMs: number,
  maxIntervalMs: number,
  factor = 1.5
): number {
  if (consecutiveFailures <= 0) {
    return baseIntervalMs;
  }
  const multiplier = Math.pow(factor, Math.min(consecutiveFailures, 8));
  const rawDelay = baseIntervalMs * multiplier;
  return Math.min(maxIntervalMs, Math.round(rawDelay));
}

export type ConnectionStatus = 'connecting' | 'live' | 'stale' | 'disconnected';

export interface ConnectionStatusOptions {
  hasEverConnected: boolean;
  consecutiveFailures: number;
  lastContactTimestamp: number | null;
  now?: number;
  staleThresholdMs?: number;
  disconnectThresholdMs?: number;
}

/**
 * Pure function to determine connection status from failure count and elapsed freshness.
 */
export function determineConnectionStatus(options: ConnectionStatusOptions): ConnectionStatus {
  const {
    hasEverConnected,
    consecutiveFailures,
    lastContactTimestamp,
    now = Date.now(),
    staleThresholdMs = 5000,
    disconnectThresholdMs = 12000,
  } = options;

  if (!hasEverConnected && consecutiveFailures === 0 && lastContactTimestamp === null) {
    return 'connecting';
  }

  if (consecutiveFailures >= 3) {
    return 'disconnected';
  }

  if (lastContactTimestamp !== null) {
    const elapsed = now - lastContactTimestamp;
    if (elapsed > disconnectThresholdMs) {
      return 'disconnected';
    }
    if (consecutiveFailures > 0 || elapsed > staleThresholdMs) {
      return 'stale';
    }
    return 'live';
  }

  return consecutiveFailures > 0 ? 'disconnected' : 'connecting';
}

/**
 * Pure guard to detect if a response is stale based on generation or runId.
 */
export function isResponseStale(
  requestGeneration: number,
  currentGeneration: number,
  responseRunId?: string | null,
  activeRunId?: string | null
): boolean {
  if (requestGeneration !== currentGeneration) {
    return true;
  }
  if (
    responseRunId !== undefined &&
    responseRunId !== null &&
    activeRunId !== undefined &&
    activeRunId !== null &&
    responseRunId !== activeRunId
  ) {
    return true;
  }
  return false;
}

/**
 * Helper to format last contact timestamp concisely for TelemetryBar.
 */
export function formatLastContact(timestamp: number | null | undefined, now = Date.now()): string {
  if (!timestamp) return 'No contact yet';
  const elapsedSec = Math.max(0, Math.floor((now - timestamp) / 1000));
  if (elapsedSec < 5) return 'just now';
  if (elapsedSec < 60) return `${elapsedSec}s ago`;
  const mins = Math.floor(elapsedSec / 60);
  return `${mins}m ${elapsedSec % 60}s ago`;
}
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

