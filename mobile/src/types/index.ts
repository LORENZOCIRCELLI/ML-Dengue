// ---------------------------------------------------------------------------
// Tipos gerados a partir do schema em docs/json_schema.md.
// Mantenha este arquivo em sincronia com export_dengue_json.py.
// ---------------------------------------------------------------------------

export type RiskLevel = 'low' | 'moderate' | 'high' | 'unknown';

export type ModelType = 'classification' | 'regression';

export interface Region {
  id: string;
  name: string;
  state: string;
  country: string;
}

export interface Metadata {
  generatedAt: string;
  sourceNotebook: string;
  region: Region;
  targetVariable: { column: string; label: string; unit: string };
  outbreakLabelDefinition: { method: string; horizonWeeks: number };
  dataRange: { start: string; end: string };
  riskThresholds: { low: number; moderate: number; high: number };
  availableHorizonsWeeks: number[];
  plannedHorizonsWeeks: number[];
  notes?: string;
}

export interface ClassificationMetrics {
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  f1Score: number | null;
  rocAuc: number | null;
}

export interface RegressionMetrics {
  rmse: number | null;
  mae: number | null;
  r2: number | null;
}

export interface ModelInfo {
  id: string;
  name: string;
  shortName: string;
  type: ModelType;
  description: string;
  isDefault: boolean;
  status: 'available' | 'unavailable';
  // keyed by horizonWeeks as a string, e.g. "16"
  metrics: Record<string, ClassificationMetrics | RegressionMetrics>;
}

export interface ModelsResponse {
  generatedAt: string;
  models: ModelInfo[];
  bestModelByRocAuc: string | null;
}

// A single "card" of prediction data: either a classification prediction
// (outbreakProbability / riskLevel / predictedOutbreak) or a regression
// prediction (expectedCases). Consumers should branch on which fields
// are present.
export interface Prediction {
  modelId: string;
  regionId: string;
  horizonWeeks: number;
  asOfDate: string;
  targetDate: string;
  outbreakProbability?: number;
  riskLevel?: RiskLevel;
  predictedOutbreak?: boolean;
  expectedCases?: number;
  confidence: 'model_probability' | 'model_estimate';
}

export interface PredictionsResponse {
  generatedAt: string;
  referenceDate: string;
  predictions: Prediction[];
}

export type ChartType = 'line' | 'bar' | 'area';

export interface ChartAxis {
  label: string;
  type?: 'date' | 'category' | 'value';
  unit?: string | null;
  min?: number;
  max?: number;
}

export interface ChartPoint {
  x: string; // ISO date, category label, or numeric-as-string
  y: number | null;
}

export interface ChartSeries {
  name: string;
  data: ChartPoint[];
}

export interface ChartReferenceLine {
  value: number;
  label: string;
}

export interface ChartDefinition {
  id: string;
  type: ChartType;
  title: string;
  description: string;
  xAxis: ChartAxis;
  yAxis: ChartAxis;
  series: ChartSeries[];
  referenceLines?: ChartReferenceLine[];
}

export interface ChartsResponse {
  generatedAt: string;
  charts: ChartDefinition[];
}

// ---------------------------------------------------------------------------
// Retrospectiva / Backtesting
// "Se estivéssemos naquele período, o que a IA teria previsto?"
// Ainda não há endpoint real — ver services/providers/mockProvider.ts.
// ---------------------------------------------------------------------------

export interface BacktestPoint {
  x: string; // data ISO
  y: number; // casos (observado) ou casos estimados (previsto)
}

export interface BacktestMetrics {
  mae: number | null;
  rmse: number | null;
  correlation: number | null;
}

export interface BacktestResponse {
  isSynthetic: boolean; // true enquanto vier do mockProvider — nunca confundir com resultado real
  period: { start: string; end: string };
  horizonWeeks: number;
  modelId: string;
  observed: BacktestPoint[];
  predicted: BacktestPoint[];
  metrics: BacktestMetrics;
}

// ---------------------------------------------------------------------------
// App-level derived types
// ---------------------------------------------------------------------------

export interface HorizonSummary {
  horizonWeeks: number;
  hasData: boolean;
  prediction?: Prediction;
}
