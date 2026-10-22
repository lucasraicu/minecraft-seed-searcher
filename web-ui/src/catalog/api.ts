import { validStructureEvidence } from './evidenceValidation';
/**
 * Bounded API client for Private Catalog endpoints.
 * Conforms to reviews/catalog-private-pilot-2026-10-20/INTERFACES.md.
 */
import { requestJson, AbortError, HttpError } from '../utils/network';
import type {
  CatalogStatusResponse,
  CatalogCapabilitiesResponse,
  CatalogSnapshotsResponse,
  CatalogQueryRequestBody,
  CatalogQueryResponse,
  CatalogDetailResponse,
} from './types';

const BASE_URL = '/api/catalog';
const DEFAULT_TIMEOUT_MS = 12000;

export async function fetchCatalogStatus(signal?: AbortSignal): Promise<CatalogStatusResponse> {
  try {
    const res = await requestJson<CatalogStatusResponse>(`${BASE_URL}/status`, {
      method: 'GET',
      timeoutMs: DEFAULT_TIMEOUT_MS,
      signal,
    });
    return res.data;
  } catch (error) {
    if (error instanceof AbortError) throw error;
    if (error instanceof HttpError && error.responseBody && typeof error.responseBody === 'object') {
      return error.responseBody as CatalogStatusResponse;
    }
    throw error;
  }
}

export async function fetchCatalogCapabilities(signal?: AbortSignal, snapshotId?: string): Promise<CatalogCapabilitiesResponse> {
  try {
    const res = await requestJson<CatalogCapabilitiesResponse>(`${BASE_URL}/capabilities${snapshotId?`?snapshot_id=${encodeURIComponent(snapshotId)}`:""}`, {
      method: 'GET',
      timeoutMs: DEFAULT_TIMEOUT_MS,
      signal,
    });
    return res.data;
  } catch (error) {
    if (error instanceof AbortError) throw error;
    if (error instanceof HttpError && error.responseBody && typeof error.responseBody === 'object') {
      return error.responseBody as CatalogCapabilitiesResponse;
    }
    throw error;
  }
}

export async function fetchCatalogSnapshots(signal?: AbortSignal): Promise<CatalogSnapshotsResponse> {
  try {
    const res = await requestJson<CatalogSnapshotsResponse>(`${BASE_URL}/snapshots`, {
      method: 'GET',
      timeoutMs: DEFAULT_TIMEOUT_MS,
      signal,
    });
    return res.data;
  } catch (error) {
    if (error instanceof AbortError) throw error;
    if (error instanceof HttpError && error.responseBody && typeof error.responseBody === 'object') {
      return error.responseBody as CatalogSnapshotsResponse;
    }
    throw error;
  }
}

export async function postCatalogQuery(
  body: CatalogQueryRequestBody,
  signal?: AbortSignal
): Promise<CatalogQueryResponse> {
  try {
    const res = await requestJson<CatalogQueryResponse>(`${BASE_URL}/query`, {
      method: 'POST',
      body,
      timeoutMs: 20000,
      signal,
    });
    return res.data;
  } catch (error) {
    if (error instanceof AbortError) throw error;
    if (error instanceof HttpError && error.responseBody && typeof error.responseBody === 'object') {
      return error.responseBody as CatalogQueryResponse;
    }
    throw error;
  }
}

export async function fetchCatalogDetail(
  snapshotId: string,
  worldId: string,
  layoutId: string,
  signal?: AbortSignal
): Promise<CatalogDetailResponse> {
  const query = new URLSearchParams({
    snapshot_id: snapshotId,
    world_id: worldId,
    layout_id: layoutId,
  });
  try {
    const res = await requestJson<CatalogDetailResponse>(`${BASE_URL}/detail?${query.toString()}`, {
      method: 'GET',
      timeoutMs: DEFAULT_TIMEOUT_MS,
      signal,
    });
    if (res.data.structure_evidence !== undefined &&
        (!res.data.structure_evidence || typeof res.data.structure_evidence !== 'object' ||
         Array.isArray(res.data.structure_evidence) || Object.entries(res.data.structure_evidence).some(
           ([feature, value]) => !validStructureEvidence(value, undefined, feature)))) {
      throw new Error('Catalog evidence response is inconsistent.');
    }
    return res.data;
  } catch (error) {
    if (error instanceof AbortError) throw error;
    if (error instanceof HttpError && error.responseBody && typeof error.responseBody === 'object') {
      return error.responseBody as CatalogDetailResponse;
    }
    throw error;
  }
}
