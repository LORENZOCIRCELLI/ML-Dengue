import React, { useCallback, useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { api } from '../services/api';
import { ChartDefinition, Metadata, ModelInfo, Prediction } from '../types';
import { colors, spacing, typography } from '../theme/colors';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import ModelSelector from '../components/ModelSelector';
import HorizonTabs from '../components/HorizonTabs';
import PredictionCard from '../components/PredictionCard';
import GenericChart from '../components/GenericChart';
import { OFFICIAL_HORIZONS_WEEKS } from '../config/api.config';

interface ScreenData {
  metadata: Metadata;
  models: ModelInfo[];
  predictions: Prediction[];
  probabilityChart?: ChartDefinition;
}

export default function PredictionsScreen() {
  const [data, setData] = useState<ScreenData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);
  const [selectedHorizon, setSelectedHorizon] = useState<number>(OFFICIAL_HORIZONS_WEEKS[0]);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [metadata, modelsRes, predictionsRes, chartsRes] = await Promise.all([
        api.getMetadata(),
        api.getModels(),
        api.getPredictions(),
        api.getCharts(),
      ]);
      setData({
        metadata,
        models: modelsRes.models,
        predictions: predictionsRes.predictions,
        probabilityChart: chartsRes.charts.find((c) => c.id === 'outbreak_probability_timeline'),
      });
      const defaultModel = modelsRes.models.find((m) => m.isDefault) ?? modelsRes.models[0];
      setSelectedModelId((prev) => prev ?? defaultModel.id);
      setSelectedHorizon((prev) => (metadata.availableHorizonsWeeks.includes(prev) ? prev : metadata.availableHorizonsWeeks[0]));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro inesperado.');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!data || !selectedModelId) return <LoadingState label="Carregando previsões..." />;

  const { metadata, models, predictions, probabilityChart } = data;
  const classificationModels = models.filter((m) => m.type === 'classification');
  const currentModel = models.find((m) => m.id === selectedModelId)!;
  const currentPrediction = predictions.find(
    (p) => p.modelId === selectedModelId && p.horizonWeeks === selectedHorizon
  );

  const modelChart: ChartDefinition | undefined = probabilityChart && {
    ...probabilityChart,
    series: probabilityChart.series.filter((s) =>
      classificationModels.some((m) => m.shortName === s.name && m.id === selectedModelId)
    ),
  };

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Previsões</Text>

      <ModelSelector
        models={classificationModels}
        selectedModelId={selectedModelId}
        onSelect={setSelectedModelId}
      />

      <View style={{ marginTop: spacing.md }}>
        <Text style={styles.label}>Horizonte de previsão</Text>
        <HorizonTabs
          horizons={OFFICIAL_HORIZONS_WEEKS as unknown as number[]}
          availableHorizons={metadata.availableHorizonsWeeks}
          selected={selectedHorizon}
          onSelect={setSelectedHorizon}
        />
      </View>

      <View style={{ marginTop: spacing.lg, alignItems: 'center' }}>
        <PredictionCard horizonWeeks={selectedHorizon} prediction={currentPrediction} />
      </View>

      <Text style={styles.description}>{currentModel.description}</Text>

      {modelChart && modelChart.series.length > 0 && (
        <View style={{ marginTop: spacing.lg }}>
          <GenericChart chart={modelChart} />
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { paddingHorizontal: 20, paddingTop: spacing.md, paddingBottom: spacing.xxl },
  title: { ...typography.h1, color: colors.textPrimary, marginBottom: spacing.lg },
  label: { ...typography.caption, color: colors.textSecondary, fontWeight: '700', marginBottom: spacing.sm },
  description: {
    ...typography.body,
    color: colors.textSecondary,
    marginTop: spacing.md,
    textAlign: 'center',
  },
});
