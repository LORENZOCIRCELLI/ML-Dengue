import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import HorizonTabs from '../components/HorizonTabs';
import GenericChart from '../components/GenericChart';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import { OFFICIAL_HORIZONS_WEEKS, OfficialHorizonWeeks } from '../config/api.config';
import { HorizonData } from '../services/arbovirusData';
import { ChartDefinition } from '../types';
import { cardShadow, colors, radii, spacing, typography } from '../theme/colors';

export default function TrendsScreen() {
  const [horizon, setHorizon] = useState<OfficialHorizonWeeks>(4);
  const [data, setData] = useState<HorizonData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const load = useCallback(async () => {
    setError(null);
    try { setData(await loadTrendData(horizon)); }
    catch (e) { setError(e instanceof Error ? e.message : 'Erro inesperado.'); }
  }, [horizon]);
  useEffect(() => { load(); }, [load]);
  const chart = useMemo<ChartDefinition | undefined>(() => data ? ({
    id: 's3-timeline', type: 'line', title: 'Casos semanais', description: 'Últimas 52 semanas disponíveis e médias móveis.',
    xAxis: { label: 'Semana', type: 'date' }, yAxis: { label: 'Casos', unit: 'casos' },
    series: [
      { name: 'Casos', data: data.linhaTempo.slice(-52).map(point => ({ x: point.data, y: point.casos })) },
      { name: 'Média móvel 4', data: data.linhaTempo.slice(-52).map(point => ({ x: point.data, y: point.mediaMovel4 })) },
      { name: 'Média móvel 12', data: data.linhaTempo.slice(-52).map(point => ({ x: point.data, y: point.mediaMovel12 })) },
    ],
  }) : undefined, [data]);
  const select = (value: number) => { setData(null); setHorizon(value as OfficialHorizonWeeks); };
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!data || !chart) return <LoadingState label="Carregando dados do S3..." />;
  const last = data.linhaTempo[data.linhaTempo.length - 1];
  return <ScrollView style={styles.screen} contentContainerStyle={styles.content}
    refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} />}>
    <Text style={styles.title}>Dados epidemiológicos</Text>
    <Text style={styles.subtitle}>Resultados reais publicados pelo pipeline de previsão.</Text>
    <HorizonTabs horizons={[...OFFICIAL_HORIZONS_WEEKS]} availableHorizons={[...OFFICIAL_HORIZONS_WEEKS]} selected={horizon} onSelect={select} />
    <View style={styles.cards}>
      <Stat label="Última semana" value={last.casos.toLocaleString('pt-BR')} />
      <Stat label="Média histórica" value={data.metricasDistribuicao.media.toFixed(1)} />
      <Stat label="Mediana" value={data.metricasDistribuicao.mediana.toFixed(1)} />
      <Stat label="Percentil 85" value={data.metricasDistribuicao.p85.toFixed(1)} />
    </View>
    <GenericChart chart={chart} height={280} />
    <Text style={styles.note}>Horizonte: {horizon} semanas · Último registro: {new Date(`${last.data}T12:00:00`).toLocaleDateString('pt-BR')}</Text>
  </ScrollView>;
}

const DATA_URLS: Record<OfficialHorizonWeeks, string> = {
  4: 'https://dengue-model-results-mldengue.s3.us-east-1.amazonaws.com/outputs/horizontes/04_semanas/dados/app_dados_dengue.json',
  8: 'https://dengue-model-results-mldengue.s3.us-east-1.amazonaws.com/outputs/horizontes/08_semanas/dados/app_dados_dengue.json',
  12: 'https://dengue-model-results-mldengue.s3.us-east-1.amazonaws.com/outputs/horizontes/12_semanas/dados/app_dados_dengue.json',
  16: 'https://dengue-model-results-mldengue.s3.us-east-1.amazonaws.com/outputs/horizontes/16_semanas/dados/app_dados_dengue.json',
};

async function loadTrendData(horizon: OfficialHorizonWeeks): Promise<HorizonData> {
  const response = await fetchS3(DATA_URLS[horizon], horizon);
  if (!response.ok) throw new Error(`Tendências de ${horizon} semanas: HTTP ${response.status}.`);
  const body = await response.json() as HorizonData;
  if (!Array.isArray(body.linhaTempo) || body.linhaTempo.length === 0 || !body.metricasDistribuicao) {
    throw new Error(`O arquivo de tendências de ${horizon} semanas possui formato inválido.`);
  }
  return body;
}

async function fetchS3(url: string, horizon: number): Promise<Response> {
  const alternatives = [url, url.replace('.s3.us-east-1.amazonaws.com', '.s3.amazonaws.com')];
  let lastError: unknown;
  for (const candidate of alternatives) {
    try {
      const separator = candidate.includes('?') ? '&' : '?';
      return await fetch(`${candidate}${separator}app=trends&horizon=${horizon}&v=4`, {
        cache: 'no-store',
        mode: 'cors',
      });
    } catch (error) { lastError = error; }
  }
  throw lastError instanceof Error ? lastError : new Error('Falha de rede ao acessar o S3.');
}
function Stat({ label, value }: { label: string; value: string }) {
  return <View style={styles.card}><Text style={styles.value}>{value}</Text><Text style={styles.label}>{label}</Text></View>;
}
const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background }, content: { paddingHorizontal: 20, paddingTop: spacing.md, paddingBottom: spacing.xxl },
  title: { ...typography.h1, color: colors.textPrimary }, subtitle: { ...typography.body, color: colors.textSecondary, marginTop: 2, marginBottom: spacing.lg },
  cards: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, marginVertical: spacing.lg },
  card: { ...cardShadow, width: '48%', backgroundColor: colors.surface, borderWidth: 0, borderRadius: radii.md, padding: spacing.md },
  value: { ...typography.h2, color: colors.primaryDark }, label: { ...typography.caption, color: colors.textSecondary },
  note: { ...typography.caption, color: colors.muted, textAlign: 'center', marginTop: spacing.md },
});
