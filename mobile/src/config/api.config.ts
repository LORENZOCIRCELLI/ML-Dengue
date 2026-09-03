// ---------------------------------------------------------------------------
// ÚNICO ARQUIVO com toda a configuração de endpoints AWS + a chave que liga
// entre dados mockados e API real.
//
// Quando os endpoints reais existirem, troque os valores abaixo — nenhum
// outro arquivo do app precisa mudar. Nenhum componente de UI e nenhum outro
// serviço deve importar URLs diretamente; tudo passa por API_CONFIG.
// ---------------------------------------------------------------------------

// 'mock'  -> lê os JSONs locais em src/mock/ (funciona sem internet/AWS)
// 'aws'   -> chama os endpoints definidos em API_CONFIG abaixo
// Pode também ser definido em build-time via variável de ambiente Expo:
//   EXPO_PUBLIC_DATA_SOURCE=aws npx expo start
export type DataSourceMode = 'mock' | 'aws';

export const DATA_SOURCE: DataSourceMode =
  (process.env.EXPO_PUBLIC_DATA_SOURCE as DataSourceMode) ?? 'mock';

// PLACEHOLDER — substitua pela URL real da API Gateway/CloudFront quando
// disponível (ver docs/aws_architecture.md). Pode também vir de
// EXPO_PUBLIC_API_BASE_URL em tempo de build, sem editar este arquivo.
export const API_CONFIG = {
  baseUrl:
    process.env.EXPO_PUBLIC_API_BASE_URL ??
    'https://PLACEHOLDER.execute-api.sa-east-1.amazonaws.com/v1',

  endpoints: {
    metadata: '/metadata',
    models: '/models',
    predictions: '/predictions',
    charts: '/charts',
    // backtesting aceita querystring: ?start=&end=&horizonWeeks=&modelId=
    backtest: '/backtest',
  },

  timeoutMs: 10_000,
};

// Horizontes oficiais com dados e métricas reais publicados no S3.
export const OFFICIAL_HORIZONS_WEEKS = [4, 8, 12, 16] as const;
export type OfficialHorizonWeeks = (typeof OFFICIAL_HORIZONS_WEEKS)[number];
