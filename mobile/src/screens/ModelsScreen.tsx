import { useCallback, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import EvaluationRoc from '../components/EvaluationRoc';
import HorizonTabs from '../components/HorizonTabs';
import ErrorState from '../components/ErrorState';
import LoadingState from '../components/LoadingState';
import ScreenHeader from '../components/ScreenHeader';
import { useAsyncResource } from '../hooks/useAsyncResource';
import { results } from '../services/results';
import { EvaluationMetrics, ResultEntry } from '../types/results';
import { catalogHorizons, modelNames, percent } from '../utils/results';
import { colors, radii, typography } from '../theme/colors';
import { screenContent } from '../theme/layout';

export default function ModelsScreen() {
  const catalog = useAsyncResource('catalogo', results.getCatalog);
  const [horizon, setHorizon] = useState(4);

  if (catalog.error)
    return <ErrorState message={catalog.error} onRetry={catalog.reload} />;
  if (!catalog.data) return <LoadingState />;

  const horizons = catalogHorizons(catalog.data);
  const selected = horizons.includes(horizon) ? horizon : horizons[0];
  const entries = catalog.data.resultados.filter(
    (entry) => entry.horizonteSemanas === selected,
  );

  return (
    <ScrollView style={styles.screen} contentContainerStyle={screenContent}>
      <ScreenHeader
        title="Por trás da previsão."
        subtitle="Avaliação histórica dos três modelos para aumento de casos."
        icon="layers-outline"
      />
      <HorizonTabs
        horizons={horizons}
        availableHorizons={horizons}
        selected={selected}
        onSelect={setHorizon}
      />
      <Text style={styles.note}>
        Métricas da partição de teste. Avaliação retrospectiva exploratória; os resultados
        não garantem o acerto de uma previsão individual.
      </Text>
      {entries.map((entry, index) => (
        <ModelEvaluation
          key={`${entry.modelo}/${selected}`}
          entry={entry}
          tone={[colors.cyan, colors.pink, colors.lavender][index % 3]}
        />
      ))}
      <View style={styles.pending}>
        <Text style={styles.name}>Regressão</Text>
        <Text style={styles.note}>
          Os resultados desta seção ainda não estão disponíveis na exportação atual.
        </Text>
      </View>
    </ScrollView>
  );
}

function ModelEvaluation({ entry, tone }: { entry: ResultEntry; tone: string }) {
  const load = useCallback(() => results.getMetrics(entry), [entry]);
  const metrics = useAsyncResource(entry.metricas, load);

  if (metrics.error)
    return <ErrorState message={metrics.error} onRetry={metrics.reload} />;
  if (!metrics.data)
    return (
      <LoadingState label={`Carregando ${modelNames[entry.modelo] ?? entry.modelo}…`} />
    );

  const value = metrics.data;
  const test = value.metricas.find((row) => row.split === 'teste')!;
  const matrix = value.matrizesConfusao.teste;

  return (
    <View style={[styles.card, { backgroundColor: tone }]}>
      <Text style={styles.name}>{modelNames[entry.modelo] ?? entry.modelo}</Text>
      <Text style={styles.caption}>
        {value.tipoModelo} · {test.n_samples} semanas avaliadas
      </Text>
      <View style={styles.grid}>
        <Metric label="Acerto histórico" value={test.accuracy} />
        <Metric label="F1" value={test.f1} ratio />
        <Metric label="Precisão" value={test.precision} />
        <Metric label="Recall" value={test.recall} />
        <Metric label="ROC-AUC" value={test.roc_auc} ratio />
        <Metric label="PR-AUC" value={test.pr_auc} ratio />
      </View>
      <Text style={styles.caption}>
        {test.n_positive} semanas com aumento no teste. Referência que sempre prevê “não”:{' '}
        {percent(value.baselineSempreNegativoAcuracia)} de acerto.
      </Text>
      <Text style={styles.section}>Treino, validação e teste</Text>
      {value.metricas.map((row) => (
        <SplitSummary key={row.split} row={row} />
      ))}
      {matrix && (
        <View style={styles.matrix}>
          <Text style={styles.section}>Matriz de confusão · teste</Text>
          <Text style={styles.caption}>
            Linhas: observado. Colunas: previsto. Ordem: sem aumento ≥ 50%, aumento ≥ 50%.
          </Text>
          {matrix.valores.map((row, index) => (
            <View style={styles.matrixRow} key={index}>
              {row.map((count, column) => (
                <View style={styles.cell} key={column}>
                  <Text style={styles.metricValue}>{count}</Text>
                  <Text style={styles.cellLabel}>
                    {index === 0 ? 'Sem aumento' : 'Com aumento'} →{' '}
                    {column === 0 ? 'Não' : 'Sim'}
                  </Text>
                </View>
              ))}
            </View>
          ))}
        </View>
      )}
      <EvaluationRoc metrics={value} />
    </View>
  );
}

function Metric({
  label,
  value,
  ratio = false,
}: {
  label: string;
  value: number | null;
  ratio?: boolean;
}) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricValue}>
        {ratio ? (value?.toFixed(3) ?? '—') : percent(value)}
      </Text>
      <Text style={styles.caption}>{label}</Text>
    </View>
  );
}

function SplitSummary({ row }: { row: EvaluationMetrics }) {
  const labels: Record<string, string> = {
    treino: 'Treino',
    validacao: 'Validação',
    teste: 'Teste',
  };
  return (
    <View style={styles.split}>
      <Text style={styles.splitTitle}>
        {labels[row.split] ?? row.split} · {row.n_samples} semanas
      </Text>
      <Text style={styles.caption}>
        Acerto {percent(row.accuracy)} · F1 {row.f1?.toFixed(3) ?? '—'} · Recall{' '}
        {percent(row.recall)} · ROC-AUC {row.roc_auc?.toFixed(3) ?? '—'}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pending: { marginTop: 32 },
  screen: { flex: 1, backgroundColor: colors.background },
  note: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 18,
    marginBottom: 8,
  },
  card: { borderRadius: radii.lg, padding: 24, marginTop: 20 },
  name: { ...typography.h2, color: colors.textPrimary },
  caption: { ...typography.caption, color: colors.textPrimary, marginTop: 6 },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginTop: 22,
    marginBottom: 14,
  },
  metric: {
    flexGrow: 1,
    minWidth: 95,
    backgroundColor: '#FFFFFFCC',
    borderRadius: radii.sm,
    padding: 14,
  },
  metricValue: {
    ...typography.h3,
    color: colors.textPrimary,
    fontVariant: ['tabular-nums'],
  },
  section: { ...typography.h3, color: colors.textPrimary, marginTop: 24 },
  split: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#11111318',
  },
  splitTitle: { ...typography.body, fontWeight: '600', color: colors.textPrimary },
  matrix: { gap: 8 },
  matrixRow: { flexDirection: 'row', gap: 8 },
  cell: { flex: 1, backgroundColor: '#FFFFFFCC', borderRadius: radii.sm, padding: 12 },
  cellLabel: { ...typography.caption, color: colors.textPrimary, marginTop: 4 },
});
