export interface ResultEntry {
  modelo: string;
  horizonteSemanas: number;
  dataAlvo: string;
  previsao: string;
  metricas: string;
  explicabilidade: string;
  conclusao: string;
  resultadoCompleto: string;
  retrospectiva?: string;
}

export interface ResultsCatalog {
  schemaVersion: string;
  versao: string;
  resultados: ResultEntry[];
}

export interface ConfusionMatrix {
  rotulos: string[];
  valores: number[][];
}

export interface ForecastResult {
  schemaVersion: string;
  versao: string;
  modelo: string;
  nomeModelo: string;
  dataReferencia: string;
  dataAlvo: string;
  mediaCasosReferencia: number;
  limiteCasosAumento: number;
  horizonteSemanas: number;
  aumentoCasosPrevisto: boolean;
  resposta: string;
  criterio: string;
  escoreAumentoNaoCalibrado: number;
  limiarDecisao: number;
  desempenhoHistorico: {
    acuracia: number;
    acuraciaPercentual: number;
    semanasAvaliadas: number;
    semanasComAumento: number;
    f1: number;
    precision: number;
    recall: number;
    rocAuc: number | null;
    prAuc: number | null;
    tipoAvaliacao: string;
    matrizConfusao: ConfusionMatrix;
  };
  experimental: boolean;
  aviso: string;
  notaTaxaAcerto: string;
  textoConclusao: string;
}

export interface EvaluationMetrics {
  split: string;
  f1: number | null;
  precision: number | null;
  recall: number | null;
  roc_auc: number | null;
  pr_auc: number | null;
  accuracy: number | null;
  n_samples: number;
  n_positive: number;
  predicted_positive: number;
}

export interface MetricsResult {
  modelo: string;
  horizonteSemanas: number;
  tipoModelo: string;
  metricas: EvaluationMetrics[];
  matrizesConfusao: Record<string, ConfusionMatrix>;
  curvasRoc: {
    split: string;
    false_positive_rate: number;
    true_positive_rate: number;
    threshold: number | null;
  }[];
  tipoTeste: string;
  baselineSempreNegativoAcuracia: number;
}

export interface ExplanationMethod {
  unidade: string;
  importanciaGlobal: AttributionImportance[];
  importanciaPorVariavel: AttributionImportance[];
  regraAgregacao: string;
  previsao: { feature: string; attribution: number; standardized_input: number }[];
}

export interface AttributionImportance {
  feature: string;
  mean_absolute_attribution: number;
  mean_signed_attribution: number;
}

export interface ExplanationResult {
  classeExplicada: string;
  saidaExplicada: string;
  particaoGlobal: string;
  atributos: string[];
  metodos: Record<string, ExplanationMethod>;
  interpretacao: string;
}

export interface ConclusionResult {
  modelo: string;
  horizonteSemanas: number;
  dataAlvo: string;
  texto: string;
  experimental: boolean;
  aviso: string;
  notaTaxaAcerto: string;
}

export interface DatasetRow {
  dt_pri_sem: string;
  casos_dengue: number;
  temperatura_media: number;
  umidade_media: number;
  chuva_total: number;
  semana_sin: number;
  semana_cos: number;
}

export type RetrospectiveOutcome =
  'verdadeiro_negativo' | 'falso_positivo' | 'falso_negativo' | 'verdadeiro_positivo';

export interface RetrospectiveRecord {
  dataEmissao: string;
  dataAlvo: string;
  mediaCasosReferencia: number;
  limiteCasosAumento: number;
  casosObservados: number;
  aumentoObservado: boolean;
  aumentoPrevisto: boolean;
  acertou: boolean;
  resultado: RetrospectiveOutcome;
  escoreAumentoNaoCalibrado: number;
}

export interface RetrospectiveResult {
  schemaVersion: string;
  versao: string;
  modelo: string;
  nomeModelo: string;
  horizonteSemanas: number;
  particao: 'teste';
  tipoAvaliacao: string;
  criterio: string;
  limiarDecisao: number;
  periodoAlvo: { inicio: string; fim: string };
  desempenhoHistorico: ForecastResult['desempenhoHistorico'];
  contagens: Record<RetrospectiveOutcome, number>;
  registros: RetrospectiveRecord[];
  experimental: boolean;
  aviso: string;
  notaMetodologica: string;
}
