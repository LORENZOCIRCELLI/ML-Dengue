import { API_CONFIG } from '../../config/api.config';
import {
  BacktestResponse,
  ChartsResponse,
  Metadata,
  ModelsResponse,
  PredictionsResponse,
} from '../../types';

// ---------------------------------------------------------------------------
// Provedor AWS — único lugar do app que monta URLs a partir de API_CONFIG.
// Implementa a MESMA interface que mockProvider.ts, então services/api.ts
// pode alternar entre os dois sem a UI perceber a diferença.
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
    this.name = 'ApiError';
  }
}

async function getJson<T>(path: string, query?: Record<string, string | number>): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), API_CONFIG.timeoutMs);

  const qs = query
    ? '?' + new URLSearchParams(Object.entries(query).map(([k, v]) => [k, String(v)])).toString()
    : '';

  try {
    const response = await fetch(`${API_CONFIG.baseUrl}${path}${qs}`, {
      signal: controller.signal,
      headers: { Accept: 'application/json' },
    });
    if (!response.ok) {
      throw new ApiError(`Falha ao buscar ${path} (HTTP ${response.status})`, response.status);
    }
    return (await response.json()) as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(`Não foi possível conectar ao servidor (${path}).`);
  } finally {
    clearTimeout(timeout);
  }
}

export const awsProvider = {
  getMetadata: (): Promise<Metadata> => getJson(API_CONFIG.endpoints.metadata),

  getModels: (): Promise<ModelsResponse> => getJson(API_CONFIG.endpoints.models),

  getPredictions: (regionId?: string): Promise<PredictionsResponse> =>
    getJson(API_CONFIG.endpoints.predictions, regionId ? { regionId } : undefined),

  getCharts: (regionId?: string): Promise<ChartsResponse> =>
    getJson(API_CONFIG.endpoints.charts, regionId ? { regionId } : undefined),

  getBacktest: (
    startDate: string,
    endDate: string,
    horizonWeeks: number,
    modelId: string
  ): Promise<BacktestResponse> =>
    getJson(API_CONFIG.endpoints.backtest, { start: startDate, end: endDate, horizonWeeks, modelId }),
};
