import { useCallback, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import ModelSelector from '../components/ModelSelector';
import HorizonTabs from '../components/HorizonTabs';
import PredictionCard from '../components/PredictionCard';
import ExplanationPanel from '../components/ExplanationPanel';
import ScreenHeader from '../components/ScreenHeader';
import { useAsyncResource } from '../hooks/useAsyncResource';
import { results } from '../services/results';
import { ResultEntry } from '../types/results';
import { catalogHorizons, catalogModels } from '../utils/results';
import { colors, radii, typography } from '../theme/colors';
import { screenContent } from '../theme/layout';

export default function PredictionsScreen() {
  const catalog = useAsyncResource('catalogo', results.getCatalog);
  const [model, setModel] = useState('random_forest');
  const [horizon, setHorizon] = useState(4);

  if (catalog.error)
    return <ErrorState message={catalog.error} onRetry={catalog.reload} />;
  if (!catalog.data) return <LoadingState />;

  const models = catalogModels(catalog.data);
  const selectedModel = models.some((item) => item.id === model) ? model : models[0].id;
  const horizons = catalogHorizons(catalog.data, selectedModel);
  const selectedHorizon = horizons.includes(horizon) ? horizon : horizons[0];
  const entry = catalog.data.resultados.find(
    (item) => item.modelo === selectedModel && item.horizonteSemanas === selectedHorizon,
  )!;

  return (
    <ScrollView style={styles.screen} contentContainerStyle={screenContent}>
      <ScreenHeader
        title="Previsões."
        subtitle="Aumento de casos nas próximas semanas, com o desempenho histórico de cada modelo."
        icon="analytics-outline"
      />
      <ModelSelector
        models={models}
        selectedModelId={selectedModel}
        onSelect={setModel}
      />
      <Text style={styles.label}>Horizonte de previsão</Text>
      <HorizonTabs
        horizons={catalogHorizons(catalog.data)}
        availableHorizons={horizons}
        selected={selectedHorizon}
        onSelect={setHorizon}
      />
      <ForecastDetails entry={entry} key={`${entry.modelo}/${entry.horizonteSemanas}`} />
    </ScrollView>
  );
}

function ForecastDetails({ entry }: { entry: ResultEntry }) {
  const load = useCallback(() => results.getForecast(entry), [entry]);
  const forecast = useAsyncResource(entry.previsao, load);
  const [showConclusion, setShowConclusion] = useState(false);

  if (forecast.error)
    return <ErrorState message={forecast.error} onRetry={forecast.reload} />;
  if (!forecast.data) return <LoadingState label="Carregando previsão…" />;

  return (
    <View style={styles.details}>
      <PredictionCard prediction={forecast.data} />
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ expanded: showConclusion }}
        style={styles.button}
        onPress={() => setShowConclusion((value) => !value)}
      >
        <Text style={styles.buttonText}>
          {showConclusion ? 'Ocultar conclusão' : 'Ver conclusão completa'}
        </Text>
      </Pressable>
      {showConclusion && <Conclusion entry={entry} />}
      <ExplanationPanel entry={entry} />
    </View>
  );
}

function Conclusion({ entry }: { entry: ResultEntry }) {
  const load = useCallback(() => results.getConclusion(entry), [entry]);
  const conclusion = useAsyncResource(entry.conclusao, load);
  if (conclusion.error)
    return <ErrorState message={conclusion.error} onRetry={conclusion.reload} />;
  return (
    <Text style={styles.conclusion}>
      {conclusion.data?.texto ?? 'Carregando conclusão…'}
    </Text>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  label: {
    ...typography.caption,
    color: colors.textSecondary,
    fontWeight: '600',
    marginTop: 24,
    marginBottom: 10,
  },
  details: { marginTop: 24 },
  button: {
    backgroundColor: colors.primary,
    borderRadius: radii.pill,
    padding: 18,
    alignItems: 'center',
    marginTop: 20,
  },
  buttonText: { ...typography.body, color: colors.surface, fontWeight: '600' },
  conclusion: {
    ...typography.body,
    color: colors.textPrimary,
    backgroundColor: colors.surfaceSoft,
    padding: 24,
    borderRadius: radii.md,
    marginTop: 16,
  },
});
