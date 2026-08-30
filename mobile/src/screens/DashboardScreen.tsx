import React, { useCallback, useEffect, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { api } from '../services/api';
import { ChartDefinition, Metadata, ModelInfo, Prediction } from '../types';
import { colors, spacing, typography } from '../theme/colors';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import PredictionCard from '../components/PredictionCard';
import GenericChart from '../components/GenericChart';
import RiskBadge from '../components/RiskBadge';
import { formatDate } from '../utils/risk';
import { OFFICIAL_HORIZONS_WEEKS } from '../config/api.config';

interface DashboardData {
  metadata: Metadata;
  defaultModel: ModelInfo;
  predictions: Prediction[];
  trendChart?: ChartDefinition;
}

export default function DashboardScreen() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [metadata, modelsRes, predictionsRes, chartsRes] = await Promise.all([
        api.getMetadata(),
        api.getModels(),
        api.getPredictions(),
        api.getCharts(),
      ]);
      const defaultModel = modelsRes.models.find((m) => m.isDefault) ?? modelsRes.models[0];
      const predictions = predictionsRes.predictions.filter((p) => p.modelId === defaultModel.id);
      const trendChart = chartsRes.charts.find((c) => c.id === 'historical_cases_trend');
      setData({ metadata, defaultModel, predictions, trendChart });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro inesperado.');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!data) return <LoadingState label="Carregando painel..." />;

  const { metadata, defaultModel, predictions, trendChart } = data;
  const primaryHorizon = metadata.availableHorizonsWeeks[0];
  const primaryPrediction = predictions.find((p) => p.horizonWeeks === primaryHorizon);

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      <Text style={styles.regionLabel}>
        {metadata.region.name}, {metadata.region.state}
      </Text>
      <Text style={styles.title}>Situação atual</Text>

      {/* Overall risk indicator — the single most important thing on screen */}
      <View style={styles.overallCard}>
        <Text style={styles.overallLabel}>
          Risco de surto ({primaryHorizon} semana{primaryHorizon > 1 ? 's' : ''} à frente)
        </Text>
        <RiskBadge level={primaryPrediction?.riskLevel} size="lg" />
        <Text style={styles.overallModel}>Segundo o modelo {defaultModel.shortName}</Text>
        {metadata.notes && <Text style={styles.notice}>{metadata.notes}</Text>}
      </View>

      <Text style={styles.sectionTitle}>Previsões por horizonte</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.horizonRow}>
        {OFFICIAL_HORIZONS_WEEKS.map((h) => (
          <PredictionCard
            key={h}
            horizonWeeks={h}
            prediction={predictions.find((p) => p.horizonWeeks === h)}
          />
        ))}
      </ScrollView>

      <Text style={styles.sectionTitle}>Tendência recente</Text>
      {trendChart && <GenericChart chart={trendChart} />}

      <Text style={styles.footerNote}>
        Última atualização: {formatDate(metadata.dataRange.end)} · Fonte: {metadata.sourceNotebook}
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.md, paddingBottom: spacing.xl },
  regionLabel: { ...typography.caption, color: colors.textSecondary },
  title: { ...typography.h1, color: colors.textPrimary, marginBottom: spacing.md },
  overallCard: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: spacing.lg,
  },
  overallLabel: { ...typography.body, color: colors.textSecondary, marginBottom: spacing.sm },
  overallModel: { ...typography.caption, color: colors.muted, marginTop: spacing.sm },
  notice: { ...typography.caption, color: colors.warning, marginTop: spacing.sm },
  sectionTitle: { ...typography.h2, color: colors.textPrimary, marginBottom: spacing.sm, marginTop: spacing.sm },
  horizonRow: { marginBottom: spacing.lg },
  footerNote: { ...typography.caption, color: colors.muted, textAlign: 'center', marginTop: spacing.lg },
});
