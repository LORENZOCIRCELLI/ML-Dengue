import { RESULTS_CONFIG } from '../config/results.config';
import { bundledResults } from '../generated/results';
import {
  ConclusionResult,
  DatasetRow,
  ExplanationResult,
  ForecastResult,
  MetricsResult,
  ResultEntry,
  RetrospectiveResult,
  ResultsCatalog,
} from '../types/results';

function safePath(path: string): string {
  if (
    !/^[a-zA-Z0-9_./-]+\.json$/.test(path) ||
    path.startsWith('/') ||
    path.split('/').includes('..')
  ) {
    throw new Error('O catálogo contém um caminho de arquivo inválido.');
  }
  return path;
}

async function readJson(path: string): Promise<unknown> {
  safePath(path);
  if (!RESULTS_CONFIG.baseUrl) {
    const load = bundledResults[path];
    if (!load)
      throw new Error(
        `Arquivo ausente na exportação: ${path}. Execute o script de exportação.`,
      );
    return load();
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), RESULTS_CONFIG.timeoutMs);
  try {
    const response = await fetch(`${RESULTS_CONFIG.baseUrl}/${path}`, {
      signal: controller.signal,
      headers: { Accept: 'application/json' },
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (error) {
    const detail = error instanceof Error ? error.message : 'Erro de rede';
    throw new Error(`Não foi possível carregar ${path}: ${detail}.`);
  } finally {
    clearTimeout(timeout);
  }
}

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function finite(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function ratio(value: unknown): boolean {
  return value === null || (finite(value) && value >= 0 && value <= 1);
}

function assertIdentity(
  value: unknown,
  entry: ResultEntry,
): asserts value is Record<string, unknown> {
  if (
    !object(value) ||
    value.modelo !== entry.modelo ||
    value.horizonteSemanas !== entry.horizonteSemanas
  ) {
    throw new Error(
      'O resultado recebido não corresponde ao modelo e horizonte selecionados.',
    );
  }
}

function assertForecast(
  value: unknown,
  entry: ResultEntry,
): asserts value is ForecastResult {
  assertIdentity(value, entry);
  if (
    value.schemaVersion !== '1.0.0' ||
    value.dataAlvo !== entry.dataAlvo ||
    typeof value.nomeModelo !== 'string' ||
    typeof value.aumentoCasosPrevisto !== 'boolean' ||
    typeof value.criterio !== 'string' ||
    typeof value.aviso !== 'string' ||
    typeof value.notaTaxaAcerto !== 'string' ||
    !object(value.desempenhoHistorico) ||
    !ratio(value.desempenhoHistorico.acuracia) ||
    value.desempenhoHistorico.acuracia === null ||
    !finite(value.desempenhoHistorico.acuraciaPercentual) ||
    !Number.isInteger(value.desempenhoHistorico.semanasAvaliadas) ||
    typeof value.desempenhoHistorico.tipoAvaliacao !== 'string' ||
    !finite(value.mediaCasosReferencia) ||
    !finite(value.limiteCasosAumento)
  ) {
    throw new Error('O JSON de previsão possui formato inválido.');
  }
}

export const results = {
  async getCatalog(): Promise<ResultsCatalog> {
    const value = await readJson('catalogo.json');
    if (
      !object(value) ||
      value.schemaVersion !== '1.0.0' ||
      !Array.isArray(value.resultados) ||
      !value.resultados.length
    ) {
      throw new Error(
        'O catálogo de resultados está vazio ou possui uma versão incompatível.',
      );
    }
    const keys = new Set<string>();
    for (const entry of value.resultados) {
      if (
        !object(entry) ||
        typeof entry.modelo !== 'string' ||
        typeof entry.horizonteSemanas !== 'number' ||
        typeof entry.dataAlvo !== 'string'
      ) {
        throw new Error('O catálogo contém um resultado inválido.');
      }
      const key = `${entry.modelo}/${entry.horizonteSemanas}`;
      if (keys.has(key)) throw new Error('O catálogo contém resultados duplicados.');
      keys.add(key);
      for (const field of [
        'previsao',
        'metricas',
        'explicabilidade',
        'conclusao',
        'resultadoCompleto',
      ]) {
        if (typeof entry[field] !== 'string')
          throw new Error('Recurso ausente no catálogo.');
        safePath(entry[field]);
      }
    }
    for (const entry of value.resultados) {
      if (entry.retrospectiva !== undefined) {
        if (typeof entry.retrospectiva !== 'string') {
          throw new Error('Caminho de retrospectiva inválido no catálogo.');
        }
        safePath(entry.retrospectiva);
      }
    }
    return value as unknown as ResultsCatalog;
  },

  async getForecast(entry: ResultEntry): Promise<ForecastResult> {
    const value = await readJson(entry.previsao);
    assertForecast(value, entry);
    return value;
  },

  async getMetrics(entry: ResultEntry): Promise<MetricsResult> {
    const value = await readJson(entry.metricas);
    assertIdentity(value, entry);
    if (
      !Array.isArray(value.metricas) ||
      !value.metricas.some((row) => object(row) && row.split === 'teste') ||
      !value.metricas.every(
        (row) =>
          object(row) &&
          typeof row.split === 'string' &&
          Number.isInteger(row.n_samples) &&
          Number.isInteger(row.n_positive) &&
          ['accuracy', 'f1', 'precision', 'recall', 'roc_auc', 'pr_auc'].every((field) =>
            ratio(row[field]),
          ),
      ) ||
      !object(value.matrizesConfusao) ||
      !Array.isArray(value.curvasRoc) ||
      !value.curvasRoc.every(
        (point) =>
          object(point) &&
          ratio(point.false_positive_rate) &&
          ratio(point.true_positive_rate) &&
          finite(point.false_positive_rate) &&
          finite(point.true_positive_rate),
      ) ||
      !finite(value.baselineSempreNegativoAcuracia)
    ) {
      throw new Error('O JSON de métricas não contém a avaliação de teste.');
    }
    return value as unknown as MetricsResult;
  },

  async getExplanation(entry: ResultEntry): Promise<ExplanationResult> {
    const value = await readJson(entry.explicabilidade);
    if (
      !object(value) ||
      !object(value.metodos) ||
      typeof value.interpretacao !== 'string' ||
      !Object.values(value.metodos).every(
        (method) =>
          object(method) &&
          typeof method.unidade === 'string' &&
          typeof method.regraAgregacao === 'string' &&
          Array.isArray(method.importanciaPorVariavel) &&
          method.importanciaPorVariavel.every(
            (row) =>
              object(row) &&
              typeof row.feature === 'string' &&
              finite(row.mean_absolute_attribution),
          ) &&
          Array.isArray(method.previsao) &&
          method.previsao.every(
            (row) =>
              object(row) && typeof row.feature === 'string' && finite(row.attribution),
          ),
      )
    ) {
      throw new Error('O JSON de explicabilidade possui formato inválido.');
    }
    return value as unknown as ExplanationResult;
  },

  async getConclusion(entry: ResultEntry): Promise<ConclusionResult> {
    const value = await readJson(entry.conclusao);
    assertIdentity(value, entry);
    if (value.dataAlvo !== entry.dataAlvo || typeof value.texto !== 'string') {
      throw new Error('O JSON de conclusão possui formato inválido.');
    }
    return value as unknown as ConclusionResult;
  },

  async getRetrospective(entry: ResultEntry): Promise<RetrospectiveResult> {
    if (!entry.retrospectiva) {
      throw new Error(
        'A retrospectiva ainda não está disponível para este modelo e horizonte.',
      );
    }
    const value = await readJson(entry.retrospectiva);
    assertIdentity(value, entry);
    const outcomes = [
      'verdadeiro_negativo',
      'falso_positivo',
      'falso_negativo',
      'verdadeiro_positivo',
    ];
    if (
      value.schemaVersion !== '1.0.0' ||
      value.particao !== 'teste' ||
      typeof value.nomeModelo !== 'string' ||
      typeof value.criterio !== 'string' ||
      typeof value.aviso !== 'string' ||
      typeof value.notaMetodologica !== 'string' ||
      !object(value.periodoAlvo) ||
      typeof value.periodoAlvo.inicio !== 'string' ||
      typeof value.periodoAlvo.fim !== 'string' ||
      !object(value.desempenhoHistorico) ||
      !finite(value.desempenhoHistorico.acuracia) ||
      !object(value.contagens) ||
      !outcomes.every(
        (key) => object(value.contagens) && Number.isInteger(value.contagens[key]),
      ) ||
      !Array.isArray(value.registros) ||
      !value.registros.length ||
      value.registros.length !== value.desempenhoHistorico.semanasAvaliadas ||
      !value.registros.every(
        (row) =>
          object(row) &&
          typeof row.dataEmissao === 'string' &&
          typeof row.dataAlvo === 'string' &&
          finite(row.casosObservados) &&
          finite(row.mediaCasosReferencia) &&
          finite(row.limiteCasosAumento) &&
          typeof row.aumentoPrevisto === 'boolean' &&
          typeof row.aumentoObservado === 'boolean' &&
          typeof row.acertou === 'boolean' &&
          row.acertou === (row.aumentoPrevisto === row.aumentoObservado) &&
          typeof row.resultado === 'string' &&
          outcomes.includes(row.resultado),
      )
    ) {
      throw new Error('O JSON de retrospectiva possui formato inválido.');
    }
    return value as unknown as RetrospectiveResult;
  },

  async getDataset(): Promise<DatasetRow[]> {
    const value = await readJson('data/dataset_utilizado.json');
    if (
      !Array.isArray(value) ||
      !value.length ||
      !value.every(
        (row) =>
          object(row) &&
          typeof row.dt_pri_sem === 'string' &&
          typeof row.casos_dengue === 'number',
      )
    ) {
      throw new Error('O JSON da série histórica possui formato inválido.');
    }
    return value as DatasetRow[];
  },
};
