import React, { useCallback, useEffect, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import HorizonTabs from '../components/HorizonTabs';
import ErrorState from '../components/ErrorState';
import LoadingState from '../components/LoadingState';
import { OFFICIAL_HORIZONS_WEEKS, OfficialHorizonWeeks } from '../config/api.config';
import { HorizonMetrics } from '../services/arbovirusData';
import { cardShadow, colors, radii, spacing, typography } from '../theme/colors';

export default function ModelsScreen() {
  const [horizon, setHorizon] = useState<OfficialHorizonWeeks>(4);
  const [metrics, setMetrics] = useState<HorizonMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const load = useCallback(async () => {
    setError(null);
    try { setMetrics(await loadMetrics(horizon)); }
    catch (e) { setError(e instanceof Error ? e.message : 'Erro inesperado.'); }
  }, [horizon]);
  useEffect(() => { load(); }, [load]);
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!metrics) return <LoadingState label="Carregando métricas do S3..." />;
  const best = Object.entries(metrics.classificacao).reduce((winner, entry) =>
    (entry[1]['ROC-AUC'] ?? -1) > (winner[1]['ROC-AUC'] ?? -1) ? entry : winner);
  return <ScrollView style={styles.screen} contentContainerStyle={styles.content}
    refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} />}>
    <Text style={styles.title}>Métricas dos modelos</Text>
    <Text style={styles.subtitle}>Avaliação real por horizonte de previsão.</Text>
    <HorizonTabs horizons={[...OFFICIAL_HORIZONS_WEEKS]} availableHorizons={[...OFFICIAL_HORIZONS_WEEKS]} selected={horizon}
      onSelect={value => { setMetrics(null); setHorizon(value as OfficialHorizonWeeks); }} />
    <Text style={styles.section}>Classificação</Text>
    {Object.entries(metrics.classificacao).map(([name, values]) => <View key={name} style={styles.card}>
      <View style={styles.header}><Text style={styles.name}>{name}</Text>{name === best[0] && <Text style={styles.badge}>Melhor ROC-AUC</Text>}</View>
      <View style={styles.grid}>{Object.entries(values).map(([label, value]) => <Metric key={label} label={label} value={value} />)}</View>
    </View>)}
    <Text style={styles.section}>Regressão · Random Forest</Text>
    <View style={styles.card}><View style={styles.grid}>{Object.entries(metrics.regressao_random_forest).map(([label, value]) => <Metric key={label} label={label} value={value} />)}</View></View>
  </ScrollView>;
}

const METRICS_URLS: Record<OfficialHorizonWeeks, string> = {
  4: 'https://dengue-model-results-mldengue.s3.us-east-1.amazonaws.com/outputs/horizontes/04_semanas/metricas/metricas_modelos.json',
  8: 'https://dengue-model-results-mldengue.s3.us-east-1.amazonaws.com/outputs/horizontes/08_semanas/metricas/metricas_modelos.json',
  12: 'https://dengue-model-results-mldengue.s3.us-east-1.amazonaws.com/outputs/horizontes/12_semanas/metricas/metricas_modelos.json',
  16: 'https://dengue-model-results-mldengue.s3.us-east-1.amazonaws.com/outputs/horizontes/16_semanas/metricas/metricas_modelos.json',
};

async function loadMetrics(horizon: OfficialHorizonWeeks): Promise<HorizonMetrics> {
  const url = METRICS_URLS[horizon];
  const response = await fetchS3(url, horizon);
  if (!response.ok) throw new Error(`Métricas de ${horizon} semanas: HTTP ${response.status}.`);
  const body = await response.json() as HorizonMetrics;
  if (body.horizonte_semanas !== horizon || !body.classificacao || Object.keys(body.classificacao).length === 0 || !body.regressao_random_forest) {
    throw new Error(`O arquivo de métricas de ${horizon} semanas possui formato inválido.`);
  }
  return body;
}

async function fetchS3(url: string, horizon: number): Promise<Response> {
  const alternatives = [url, url.replace('.s3.us-east-1.amazonaws.com', '.s3.amazonaws.com')];
  let lastError: unknown;
  for (const candidate of alternatives) {
    try {
      const separator = candidate.includes('?') ? '&' : '?';
      return await fetch(`${candidate}${separator}app=models&horizon=${horizon}&v=4`, {
        cache: 'no-store',
        mode: 'cors',
      });
    } catch (error) { lastError = error; }
  }
  throw lastError instanceof Error ? lastError : new Error('Falha de rede ao acessar o S3.');
}
function Metric({ label, value }: { label: string; value: number }) {
  const ratio = !['RMSE', 'MAE'].includes(label);
  return <View style={styles.metric}><Text style={styles.metricValue}>{ratio ? value.toFixed(3) : value.toFixed(1)}</Text><Text style={styles.metricLabel}>{label}</Text></View>;
}
const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background }, content: { paddingHorizontal: 20, paddingTop: spacing.md, paddingBottom: spacing.xxl },
  title: { ...typography.h1, color: colors.textPrimary }, subtitle: { ...typography.body, color: colors.textSecondary, marginTop: 2, marginBottom: spacing.lg },
  section: { ...typography.h2, color: colors.textPrimary, marginVertical: spacing.md },
  card: { ...cardShadow, backgroundColor: colors.surface, borderWidth: 0, borderRadius: radii.lg, padding: spacing.lg, marginBottom: spacing.md },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: spacing.sm }, name: { ...typography.h3, color: colors.textPrimary, flex: 1 },
  badge: { ...typography.caption, color: colors.success, fontWeight: '700', backgroundColor: `${colors.success}14`, paddingHorizontal: 8, paddingVertical: 4, borderRadius: radii.pill }, grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md, marginTop: spacing.md },
  metric: { minWidth: 70, backgroundColor: colors.surfaceSoft, borderRadius: radii.sm, padding: spacing.sm }, metricValue: { ...typography.h3, color: colors.primaryDark }, metricLabel: { ...typography.caption, color: colors.muted },
});
