import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import ClimateGuide from '../components/ClimateGuide';
import ErrorState from '../components/ErrorState';
import LoadingState from '../components/LoadingState';
import TrendSparkline from '../components/TrendSparkline';
import ScreenHeader from '../components/ScreenHeader';
import { useAsyncResource } from '../hooks/useAsyncResource';
import { results } from '../services/results';
import { displayDate, percent } from '../utils/results';
import { colors, radii, typography } from '../theme/colors';
import { screenContent } from '../theme/layout';

async function loadDashboard() {
  const [catalog, dataset] = await Promise.all([
    results.getCatalog(),
    results.getDataset(),
  ]);
  const horizon = Math.min(...catalog.resultados.map((entry) => entry.horizonteSemanas));
  const entries = catalog.resultados.filter(
    (entry) => entry.horizonteSemanas === horizon,
  );
  const forecasts = await Promise.all(entries.map((entry) => results.getForecast(entry)));
  return { dataset, forecasts, horizon };
}

export default function DashboardScreen() {
  const resource = useAsyncResource('painel', loadDashboard);

  if (resource.error)
    return <ErrorState message={resource.error} onRetry={resource.reload} />;
  if (!resource.data) return <LoadingState />;

  const { dataset, forecasts, horizon } = resource.data;
  const last = dataset[dataset.length - 1];
  const reference = forecasts[0];

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <ScreenHeader
        title="Um olhar à frente."
        subtitle="Acompanhe os dados de dengue de Ribeirão Preto."
        eyebrow="RIBEIRÃO PRETO · SP"
      />
      <ClimateGuide />
      <View style={styles.hero}>
        <View style={styles.heroTop}>
          <Text style={styles.kicker}>PANORAMA DA SEMANA</Text>
          <View style={styles.orb}>
            <Ionicons name="pulse-outline" size={26} />
          </View>
        </View>
        <Text style={styles.cases}>{last.casos_dengue.toLocaleString('pt-BR')}</Text>
        <Text style={styles.heroCaption}>casos registrados</Text>
        <TrendSparkline values={dataset.slice(-12).map((point) => point.casos_dengue)} />
        <Text style={styles.date}>Últimas 12 semanas</Text>
        <View style={styles.heroBottom}>
          <Text style={styles.date}>Semana de {displayDate(last.dt_pri_sem)}</Text>
        </View>
      </View>
      <Text style={styles.section}>A referência da previsão.</Text>
      <View style={styles.row}>
        <Stat
          label="Média das 4 semanas anteriores"
          value={reference.mediaCasosReferencia.toLocaleString('pt-BR')}
          tone={colors.pink}
        />
        <Stat
          label="Limiar de aumento de 50%"
          value={reference.limiteCasosAumento.toLocaleString('pt-BR')}
          tone={colors.lavender}
        />
      </View>
      <Text style={styles.section}>Daqui a {horizon} semanas.</Text>
      {forecasts.map((forecast) => (
        <View style={styles.modelCard} key={forecast.modelo}>
          <Text style={styles.kicker}>
            {forecast.nomeModelo} · {displayDate(forecast.dataAlvo)}
          </Text>
          <Text style={styles.modelName}>
            Aumento previsto: {forecast.aumentoCasosPrevisto ? 'sim' : 'não'}
          </Text>
          <Text style={styles.modelScore}>
            {percent(forecast.desempenhoHistorico.acuracia)}{' '}
            <Text style={styles.scoreLabel}>de acerto histórico</Text>
          </Text>
          <Text style={styles.note}>
            {forecast.desempenhoHistorico.semanasAvaliadas} semanas avaliadas · avaliação{' '}
            {forecast.desempenhoHistorico.tipoAvaliacao}.
          </Text>
        </View>
      ))}
      <Text style={styles.footnote}>Critério: {reference.criterio}</Text>
      <Text style={styles.footnote}>
        Modelo experimental. {reference.aviso} {reference.notaTaxaAcerto}
      </Text>
    </ScrollView>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <View style={[styles.stat, { backgroundColor: tone }]}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.unit}>casos / semana</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: screenContent,
  hero: {
    backgroundColor: colors.cyan,
    borderRadius: radii.lg,
    padding: 26,
    overflow: 'hidden',
  },
  heroTop: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  kicker: {
    ...typography.caption,
    fontWeight: '600',
    letterSpacing: 1.2,
    color: colors.textPrimary,
  },
  orb: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#FFFFFF88',
    alignItems: 'center',
    justifyContent: 'center',
  },
  cases: {
    fontSize: 66,
    lineHeight: 78,
    letterSpacing: -3,
    fontWeight: '700',
    color: colors.textPrimary,
    marginTop: 20,
  },
  heroCaption: {
    ...typography.h3,
    fontWeight: '400',
    color: colors.textPrimary,
  },
  heroBottom: {
    marginTop: 24,
    gap: 8,
  },
  risk: {
    ...typography.body,
    fontWeight: '600',
    color: colors.textPrimary,
  },
  date: {
    ...typography.caption,
    color: colors.textPrimary,
  },
  section: {
    ...typography.h2,
    marginTop: 32,
    marginBottom: 18,
    color: colors.textPrimary,
  },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 14,
  },
  stat: {
    flex: 1,
    minWidth: 130,
    borderRadius: radii.md,
    padding: 20,
  },
  statLabel: {
    ...typography.caption,
    color: colors.textPrimary,
  },
  statValue: {
    fontSize: 34,
    fontWeight: '600',
    letterSpacing: -1,
    marginTop: 26,
    color: colors.textPrimary,
  },
  unit: {
    ...typography.caption,
    color: colors.textPrimary,
    marginTop: 4,
  },
  modelCard: {
    marginTop: 24,
    padding: 26,
    borderRadius: radii.lg,
    backgroundColor: colors.surfaceSoft,
  },
  modelIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
  },
  modelName: {
    ...typography.h2,
    marginTop: 12,
    color: colors.textPrimary,
  },
  modelScore: {
    fontSize: 36,
    fontWeight: '600',
    letterSpacing: -1,
    marginTop: 20,
    color: colors.textPrimary,
  },
  scoreLabel: {
    ...typography.caption,
    color: colors.textSecondary,
    letterSpacing: 0,
  },
  note: {
    ...typography.caption,
    marginTop: 12,
    color: colors.textSecondary,
  },
  footnote: {
    ...typography.caption,
    marginTop: 24,
    color: colors.textSecondary,
  },
});
