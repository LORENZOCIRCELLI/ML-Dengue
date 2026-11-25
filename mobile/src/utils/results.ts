import { MetricsResult, ResultEntry, ResultsCatalog } from '../types/results';

export function bestModelsByHorizon(
  candidates: { entry: ResultEntry; metrics: MetricsResult }[],
) {
  const ranked = candidates.map(({ entry, metrics }) => {
    const validation = metrics.metricas.find((row) => row.split === 'validacao');
    if (validation?.f1 == null || !Number.isFinite(validation.f1)) {
      throw new Error('F1 de validação indisponível para selecionar o melhor modelo.');
    }
    return { entry, f1: validation.f1, prAuc: validation.pr_auc ?? -1 };
  });
  ranked.sort(
    (a, b) =>
      a.entry.horizonteSemanas - b.entry.horizonteSemanas ||
      b.f1 - a.f1 ||
      b.prAuc - a.prAuc ||
      a.entry.modelo.localeCompare(b.entry.modelo),
  );
  return ranked.filter(
    (candidate, index) =>
      index === 0 ||
      candidate.entry.horizonteSemanas !== ranked[index - 1].entry.horizonteSemanas,
  );
}

export const modelNames: Record<string, string> = {
  random_forest: 'Random Forest',
  rnn: 'RNN',
  lstm: 'LSTM',
};

export function catalogModels(catalog: ResultsCatalog) {
  return [...new Set(catalog.resultados.map((entry) => entry.modelo))].map((id) => ({
    id,
    shortName: modelNames[id] ?? id,
  }));
}

export function catalogHorizons(catalog: ResultsCatalog, model?: string) {
  return [
    ...new Set(
      catalog.resultados
        .filter((entry) => !model || entry.modelo === model)
        .map((entry) => entry.horizonteSemanas),
    ),
  ].sort((a, b) => a - b);
}

export function displayDate(value: string): string {
  const date = value.slice(0, 10);
  const [year, month, day] = date.split('-');
  return `${day}/${month}/${year}`;
}

export function percent(value: number | null): string {
  return value === null
    ? '—'
    : `${(value * 100).toLocaleString('pt-BR', { maximumFractionDigits: 1, minimumFractionDigits: 1 })}%`;
}

export function featureName(value: string): string {
  const [feature, lag] = value.split('__tmenos');
  const labels: Record<string, string> = {
    casos_dengue: 'Casos de dengue',
    temperatura_media: 'Temperatura média',
    umidade_media: 'Umidade média',
    chuva_total: 'Chuva total',
    semana_sin: 'Sazonalidade (seno)',
    semana_cos: 'Sazonalidade (cosseno)',
  };
  const label = labels[feature] ?? feature;
  return lag ? `${label} · ${lag} sem. antes` : label;
}
