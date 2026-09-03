import { OFFICIAL_HORIZONS_WEEKS, OfficialHorizonWeeks } from '../config/api.config';

const ROOT = 'https://dengue-model-results-mldengue.s3.us-east-1.amazonaws.com/outputs/horizontes';
export interface TimelinePoint { data: string; casos: number; mediaMovel4: number | null; mediaMovel12: number | null; }
export interface HorizonData {
  linhaTempo: TimelinePoint[];
  distribuicao: { x_label: string; x_centro: number; y_frequencia: number }[];
  metricasDistribuicao: { media: number; mediana: number; p85: number };
}
export interface HorizonMetrics {
  horizonte_semanas: number;
  classificacao: Record<string, Record<string, number>>;
  regressao_random_forest: Record<string, number>;
}
function folder(horizon: number) { return `${String(horizon).padStart(2, '0')}_semanas`; }
async function json<T>(url: string): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15_000);
  try {
    const response = await fetch(url, { signal: controller.signal, headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json() as T;
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw new Error('A fonte de dados demorou para responder.');
    const detail = error instanceof Error ? error.message : 'erro de rede';
    throw new Error(`Não foi possível carregar os dados epidemiológicos (${detail}). No Expo Web, verifique o CORS do bucket S3.`);
  } finally { clearTimeout(timeout); }
}
export const arbovirusData = {
  getData: (horizon: OfficialHorizonWeeks) => json<HorizonData>(`${ROOT}/${folder(horizon)}/dados/app_dados_dengue.json`),
  getMetrics: (horizon: OfficialHorizonWeeks) => json<HorizonMetrics>(`${ROOT}/${folder(horizon)}/metricas/metricas_modelos.json`),
  getAll: () => Promise.all(OFFICIAL_HORIZONS_WEEKS.map(async horizon => ({ horizon, data: await arbovirusData.getData(horizon), metrics: await arbovirusData.getMetrics(horizon) }))),
};
