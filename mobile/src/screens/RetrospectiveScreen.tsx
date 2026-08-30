import React, { useCallback, useState } from 'react';
import { ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { api } from '../services/api';
import { BacktestResponse, ChartDefinition } from '../types';
import { colors, radii, spacing, typography } from '../theme/colors';
import { OFFICIAL_HORIZONS_WEEKS } from '../config/api.config';
import HorizonTabs from '../components/HorizonTabs';
import GenericChart from '../components/GenericChart';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';

const DEFAULT_START = '2025-01-01';
const DEFAULT_END = '2025-04-30';
const DEFAULT_MODEL_ID = 'random_forest_optimized';

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

// "Se estivéssemos naquele período, o que a IA teria previsto?"
// Backtesting/retrospective view: manager picks a past window + horizon,
// sees REAL vs. AI-PREDICTED for that window side by side.
export default function RetrospectiveScreen() {
  const [startDate, setStartDate] = useState(DEFAULT_START);
  const [endDate, setEndDate] = useState(DEFAULT_END);
  const [horizonWeeks, setHorizonWeeks] = useState<number>(OFFICIAL_HORIZONS_WEEKS[3]);
  const [result, setResult] = useState<BacktestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isValidRange = DATE_RE.test(startDate) && DATE_RE.test(endDate) && startDate < endDate;

  const runBacktest = useCallback(async () => {
    if (!isValidRange) {
      setError('Informe datas válidas (AAAA-MM-DD) com início antes do fim.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.getBacktest(startDate, endDate, horizonWeeks, DEFAULT_MODEL_ID);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro inesperado.');
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate, horizonWeeks, isValidRange]);

  const comparisonChart: ChartDefinition | undefined = result ? {
    id: 'backtest_comparison',
    type: 'line',
    title: 'Real vs. Previsto pela IA',
    description: `O que teria sido previsto ${result.horizonWeeks} semanas à frente, comparado ao que de fato aconteceu.`,
    xAxis: { label: 'Data', type: 'date' },
    yAxis: { label: 'Casos', unit: 'cases' },
    series: [
      { name: 'REAL (observado)', data: result.observed },
      { name: 'PREVISTO PELA IA', data: result.predicted },
    ],
  } : undefined;

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Retrospectiva</Text>
      <Text style={styles.subtitle}>
        Selecione um período passado: veja o que a IA teria previsto naquele momento, comparado ao
        que de fato aconteceu.
      </Text>

      <View style={styles.formRow}>
        <View style={styles.dateField}>
          <Text style={styles.label}>Data inicial</Text>
          <TextInput
            style={styles.input}
            value={startDate}
            onChangeText={setStartDate}
            placeholder="AAAA-MM-DD"
            autoCapitalize="none"
          />
        </View>
        <View style={styles.dateField}>
          <Text style={styles.label}>Data final</Text>
          <TextInput
            style={styles.input}
            value={endDate}
            onChangeText={setEndDate}
            placeholder="AAAA-MM-DD"
            autoCapitalize="none"
          />
        </View>
      </View>

      <Text style={[styles.label, { marginTop: spacing.md }]}>Horizonte de previsão</Text>
      <HorizonTabs
        horizons={OFFICIAL_HORIZONS_WEEKS as unknown as number[]}
        availableHorizons={OFFICIAL_HORIZONS_WEEKS as unknown as number[]}
        selected={horizonWeeks}
        onSelect={setHorizonWeeks}
      />

      <TouchableOpacity style={styles.button} onPress={runBacktest} accessibilityRole="button">
        <Text style={styles.buttonText}>Gerar retrospectiva</Text>
      </TouchableOpacity>

      {loading && <LoadingState label="Calculando retrospectiva..." />}
      {error && !loading && <ErrorState message={error} onRetry={runBacktest} />}

      {result && !loading && !error && (
        <>
          {result.isSynthetic && (
            <View style={styles.mockNotice}>
              <Text style={styles.mockNoticeText}>
                Dados fictícios (mock) — ainda não há endpoint AWS de backtesting real.
              </Text>
            </View>
          )}

          {comparisonChart && <GenericChart chart={comparisonChart} height={260} />}

          <View style={styles.metricsRow}>
            <MetricBox label="MAE" value={result.metrics.mae} />
            <MetricBox label="RMSE" value={result.metrics.rmse} />
            <MetricBox label="Correlação" value={result.metrics.correlation} />
          </View>
        </>
      )}
    </ScrollView>
  );
}

function MetricBox({ label, value }: { label: string; value: number | null }) {
  return (
    <View style={styles.metricBox}>
      <Text style={styles.metricValue}>{value === null ? '—' : value}</Text>
      <Text style={styles.metricLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.md, paddingBottom: spacing.xl },
  title: { ...typography.h1, color: colors.textPrimary, marginBottom: spacing.xs },
  subtitle: { ...typography.body, color: colors.textSecondary, marginBottom: spacing.md },
  formRow: { flexDirection: 'row', gap: spacing.md },
  dateField: { flex: 1 },
  label: { ...typography.caption, color: colors.textSecondary, marginBottom: spacing.xs },
  input: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radii.sm,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    ...typography.body,
    color: colors.textPrimary,
  },
  button: {
    backgroundColor: colors.primary,
    borderRadius: radii.pill,
    paddingVertical: spacing.sm,
    alignItems: 'center',
    marginTop: spacing.lg,
    marginBottom: spacing.md,
  },
  buttonText: { color: '#fff', fontWeight: '700' },
  mockNotice: {
    backgroundColor: `${colors.warning}1A`,
    borderRadius: radii.sm,
    padding: spacing.sm,
    marginBottom: spacing.md,
  },
  mockNoticeText: { ...typography.caption, color: colors.warning, fontWeight: '600' },
  metricsRow: { flexDirection: 'row', gap: spacing.lg, marginTop: spacing.sm, justifyContent: 'center' },
  metricBox: { alignItems: 'center' },
  metricValue: { ...typography.h2, color: colors.primaryDark },
  metricLabel: { ...typography.caption, color: colors.muted },
});
