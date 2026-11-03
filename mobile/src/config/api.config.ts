export type DataSourceMode = 'mock' | 'aws';

export const DATA_SOURCE: DataSourceMode =
  (process.env.EXPO_PUBLIC_DATA_SOURCE as DataSourceMode) ?? 'mock';

export const API_CONFIG = {
  baseUrl:
    process.env.EXPO_PUBLIC_API_BASE_URL ??
    'https://PLACEHOLDER.execute-api.sa-east-1.amazonaws.com/v1',
  endpoints: {
    metadata: '/metadata',
    models: '/models',
    predictions: '/predictions',
    charts: '/charts',
    backtest: '/backtest',
  },
  timeoutMs: 10000,
};

export const OFFICIAL_HORIZONS_WEEKS = [4, 8, 12, 16] as const;

export type OfficialHorizonWeeks = (typeof OFFICIAL_HORIZONS_WEEKS)[number];
