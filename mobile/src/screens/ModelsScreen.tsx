import React, { useCallback, useEffect, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import HorizonTabs from '../components/HorizonTabs';
import ErrorState from '../components/ErrorState';
import LoadingState from '../components/LoadingState';
import { OFFICIAL_HORIZONS_WEEKS, OfficialHorizonWeeks } from '../config/api.config';
import { arbovirusData, HorizonMetrics } from '../services/arbovirusData';
import { colors, radii, spacing, typography } from '../theme/colors';

export default function ModelsScreen() {
  const [horizon, setHorizon] = useState<OfficialHorizonWeeks>(4);
  const [metrics, setMetrics] = useState<HorizonMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const load = useCallback(async () => {
    setError(null);
    try { setMetrics(await arbovirusData.getMetrics(horizon)); }
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
function Metric({ label, value }: { label: string; value: number }) {
  const ratio = !['RMSE', 'MAE'].includes(label);
  return <View style={styles.metric}><Text style={styles.metricValue}>{ratio ? value.toFixed(3) : value.toFixed(1)}</Text><Text style={styles.metricLabel}>{label}</Text></View>;
}
const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background }, content: { padding: spacing.md, paddingBottom: spacing.xl },
  title: { ...typography.h1, color: colors.textPrimary }, subtitle: { ...typography.body, color: colors.textSecondary, marginBottom: spacing.md },
  section: { ...typography.h2, color: colors.textPrimary, marginVertical: spacing.md },
  card: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, padding: spacing.md, marginBottom: spacing.md },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: spacing.sm }, name: { ...typography.h3, color: colors.textPrimary, flex: 1 },
  badge: { ...typography.caption, color: colors.success, fontWeight: '700' }, grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md, marginTop: spacing.md },
  metric: { minWidth: 62 }, metricValue: { ...typography.h3, color: colors.primaryDark }, metricLabel: { ...typography.caption, color: colors.muted },
});
