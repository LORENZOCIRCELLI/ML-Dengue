import React, { useCallback, useEffect, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import ErrorState from '../components/ErrorState';
import LoadingState from '../components/LoadingState';
import { arbovirusData, HorizonData, HorizonMetrics } from '../services/arbovirusData';
import { cardShadow, colors, radii, spacing, typography } from '../theme/colors';

interface DashboardData { data: HorizonData; metrics: HorizonMetrics; }
type CurrentRisk = 'Baixo' | 'Moderado' | 'Alto';

function calculateCurrentRisk(cases: number, median: number, percentile85: number): CurrentRisk {
  if (cases >= percentile85) return 'Alto';
  if (cases >= median) return 'Moderado';
  return 'Baixo';
}

function riskColor(risk: CurrentRisk): string {
  if (risk === 'Alto') return colors.danger;
  if (risk === 'Moderado') return colors.warning;
  return colors.success;
}

export default function DashboardScreen() {
  const [result, setResult] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const load = useCallback(async () => {
    setError(null);
    try {
      const [data, metrics] = await Promise.all([arbovirusData.getData(16), arbovirusData.getMetrics(16)]);
      setResult({ data, metrics });
    } catch (e) { setError(e instanceof Error ? e.message : 'Erro inesperado.'); }
  }, []);
  useEffect(() => { load(); }, [load]);
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!result) return <LoadingState label="Carregando painel do S3..." />;

  const last = result.data.linhaTempo[result.data.linhaTempo.length - 1];
  const currentRisk = calculateCurrentRisk(
    last.casos,
    result.data.metricasDistribuicao.mediana,
    result.data.metricasDistribuicao.p85
  );
  const currentRiskColor = riskColor(currentRisk);
  const best = Object.entries(result.metrics.classificacao).reduce((winner, entry) =>
    (entry[1]['ROC-AUC'] ?? -1) > (winner[1]['ROC-AUC'] ?? -1) ? entry : winner);
  return <ScrollView style={styles.screen} contentContainerStyle={styles.content}
    refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} />}>
    <Text style={styles.eyebrow}>DADOS REAIS · HORIZONTE DE 16 SEMANAS</Text>
    <Text style={styles.title}>Situação atual</Text>
    <View style={[styles.riskCard, { backgroundColor: `${currentRiskColor}12` }]}>
      <Text style={styles.riskLabel}>Nível epidemiológico atual</Text>
      <Text style={[styles.riskValue, { color: currentRiskColor }]}>{currentRisk}</Text>
      <Text style={styles.riskDescription}>{last.casos.toLocaleString('pt-BR')} casos na última semana</Text>
      <Text style={styles.riskThresholds}>
        Mediana histórica: {result.data.metricasDistribuicao.mediana.toFixed(1)} · Percentil 85: {result.data.metricasDistribuicao.p85.toFixed(1)}
      </Text>
    </View>
    <View style={styles.hero}>
      <Text style={styles.heroLabel}>Melhor modelo de classificação</Text>
      <Text style={styles.model}>{best[0]}</Text>
      <Text style={styles.auc}>ROC-AUC {best[1]['ROC-AUC'].toFixed(3)}</Text>
      <Text style={styles.explanation}>Selecionado automaticamente pela maior ROC-AUC no arquivo de métricas de 16 semanas.</Text>
    </View>
    <Text style={styles.section}>Último dado epidemiológico</Text>
    <View style={styles.row}>
      <Stat label="Casos na semana" value={last.casos.toLocaleString('pt-BR')} />
      <Stat label="Média móvel 4" value={last.mediaMovel4?.toFixed(1) ?? '—'} />
      <Stat label="Média móvel 12" value={last.mediaMovel12?.toFixed(1) ?? '—'} />
    </View>
    <Text style={styles.footer}>Último registro: {new Date(`${last.data}T12:00:00`).toLocaleDateString('pt-BR')} · Fonte: pipeline S3</Text>
  </ScrollView>;
}
function Stat({ label, value }: { label: string; value: string }) {
  return <View style={styles.stat}><Text style={styles.statValue}>{value}</Text><Text style={styles.statLabel}>{label}</Text></View>;
}
const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background }, content: { paddingHorizontal: 20, paddingTop: spacing.md, paddingBottom: spacing.xxl },
  eyebrow: { ...typography.caption, color: colors.primary, fontWeight: '800', letterSpacing: 0.7 }, title: { ...typography.h1, color: colors.textPrimary, marginTop: 2, marginBottom: spacing.lg },
  riskCard: { borderWidth: 0, elevation: 0, shadowOpacity: 0, borderRadius: radii.lg, padding: spacing.lg, marginBottom: spacing.md },
  riskLabel: { ...typography.body, color: colors.textSecondary }, riskValue: { fontSize: 32, fontWeight: '800', marginTop: spacing.xs },
  riskDescription: { ...typography.h3, color: colors.textPrimary, marginTop: spacing.sm }, riskThresholds: { ...typography.caption, color: colors.muted, marginTop: spacing.sm },
  hero: { ...cardShadow, backgroundColor: colors.surface, borderWidth: 0, borderRadius: radii.lg, padding: spacing.lg },
  heroLabel: { ...typography.body, color: colors.textSecondary }, model: { fontSize: 27, fontWeight: '800', color: colors.primaryDark, marginTop: spacing.xs },
  auc: { ...typography.h3, color: colors.success, marginTop: spacing.sm }, explanation: { ...typography.caption, color: colors.muted, marginTop: spacing.sm },
  section: { ...typography.h2, color: colors.textPrimary, marginTop: spacing.lg, marginBottom: spacing.sm }, row: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  stat: { ...cardShadow, flexGrow: 1, minWidth: 100, backgroundColor: colors.surface, borderWidth: 0, borderRadius: radii.md, padding: spacing.md },
  statValue: { ...typography.h2, color: colors.textPrimary }, statLabel: { ...typography.caption, color: colors.textSecondary },
  footer: { ...typography.caption, color: colors.muted, textAlign: 'center', marginTop: spacing.lg },
});
