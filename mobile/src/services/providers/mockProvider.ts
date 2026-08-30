import {
  BacktestResponse,
  ChartsResponse,
  Metadata,
  ModelsResponse,
  Prediction,
  PredictionsResponse,
} from '../../types';

// ---------------------------------------------------------------------------
// Provedor MOCK — implementa a mesma interface que o provedor AWS
// (services/providers/awsProvider.ts). A UI nunca importa este arquivo
// diretamente; sempre passa por services/api.ts.
// ---------------------------------------------------------------------------

const MOCK_LATENCY_MS = 350;

async function delay<T>(value: T): Promise<T> {
  await new Promise((resolve) => setTimeout(resolve, MOCK_LATENCY_MS));
  return value;
}

function seededRandom(seed: number): () => number {
  let s = seed % 2147483647;
  if (s <= 0) s += 2147483646;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

function isoWeeksLater(iso: string, weeks: number): string {
  const d = new Date(iso);
  d.setDate(d.getDate() + weeks * 7);
  return d.toISOString().slice(0, 10);
}

function weeksBetween(startIso: string, endIso: string): number {
  const ms = new Date(endIso).getTime() - new Date(startIso).getTime();
  return Math.max(Math.round(ms / (7 * 24 * 60 * 60 * 1000)), 1);
}

export const mockProvider = {
  getMetadata: (): Promise<Metadata> =>
    delay(require('../../mock/metadata.json') as Metadata),

  getModels: (): Promise<ModelsResponse> =>
    delay(require('../../mock/models.json') as ModelsResponse),

  getPredictions: (_regionId?: string): Promise<PredictionsResponse> =>
    delay(require('../../mock/predictions.json') as PredictionsResponse),

  getCharts: (_regionId?: string): Promise<ChartsResponse> =>
    delay(require('../../mock/charts.json') as ChartsResponse),

  // -------------------------------------------------------------------
  // Retrospectiva / Backtesting — ainda NÃO existe endpoint real. Gera,
  // de forma determinística (mesma seed para os mesmos parâmetros), uma
  // série "observada" e uma série "prevista" plausíveis para o período e
  // horizonte escolhidos. Isso é claramente dado fictício — nunca deve
  // ser confundido com resultado real do notebook. Quando o endpoint AWS
  // existir, awsProvider.getBacktest troca este gerador por uma chamada
  // HTTP real, sem mudar o schema consumido pela UI.
  // -------------------------------------------------------------------
  getBacktest: (
    startDate: string,
    endDate: string,
    horizonWeeks: number,
    modelId: string
  ): Promise<BacktestResponse> => {
    const rng = seededRandom(
      Date.parse(startDate) + Date.parse(endDate) + horizonWeeks * 97
    );
    const totalWeeks = weeksBetween(startDate, endDate);

    const observed: Prediction['outbreakProbability'][] = [];
    const observedSeries: { x: string; y: number }[] = [];
    const predictedSeries: { x: string; y: number }[] = [];

    let baseCases = 40 + rng() * 30;
    for (let i = 0; i <= totalWeeks; i++) {
      const date = isoWeeksLater(startDate, i);
      baseCases = Math.max(baseCases + (rng() - 0.5) * 18, 5);
      observedSeries.push({ x: date, y: Math.round(baseCases) });

      // "Previsto" = o que o modelo teria dito `horizonWeeks` antes desta
      // data, com ruído — simula uma previsão antecipada imperfeita.
      const predictionError = (rng() - 0.5) * 22;
      predictedSeries.push({ x: date, y: Math.max(Math.round(baseCases + predictionError), 0) });
    }

    const errors = observedSeries.map((o, i) => o.y - predictedSeries[i].y);
    const mae = errors.reduce((acc, e) => acc + Math.abs(e), 0) / errors.length;
    const rmse = Math.sqrt(errors.reduce((acc, e) => acc + e * e, 0) / errors.length);
    const meanObserved = observedSeries.reduce((a, o) => a + o.y, 0) / observedSeries.length;
    const meanPredicted = predictedSeries.reduce((a, p) => a + p.y, 0) / predictedSeries.length;
    const covariance = observedSeries.reduce(
      (acc, o, i) => acc + (o.y - meanObserved) * (predictedSeries[i].y - meanPredicted),
      0
    );
    const stdObserved = Math.sqrt(
      observedSeries.reduce((acc, o) => acc + (o.y - meanObserved) ** 2, 0)
    );
    const stdPredicted = Math.sqrt(
      predictedSeries.reduce((acc, p) => acc + (p.y - meanPredicted) ** 2, 0)
    );
    const correlation =
      stdObserved > 0 && stdPredicted > 0 ? covariance / (stdObserved * stdPredicted) : null;

    return delay({
      isSynthetic: true,
      period: { start: startDate, end: endDate },
      horizonWeeks,
      modelId,
      observed: observedSeries,
      predicted: predictedSeries,
      metrics: {
        mae: Math.round(mae * 10) / 10,
        rmse: Math.round(rmse * 10) / 10,
        correlation: correlation === null ? null : Math.round(correlation * 100) / 100,
      },
    });
  },
};
