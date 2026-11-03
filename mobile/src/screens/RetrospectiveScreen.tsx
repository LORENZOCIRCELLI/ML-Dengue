import { useCallback, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import HorizonTabs from '../components/HorizonTabs';
import LoadingState from '../components/LoadingState';
import ModelSelector from '../components/ModelSelector';
import ScreenHeader from '../components/ScreenHeader';
import { useAsyncResource } from '../hooks/useAsyncResource';
import { results } from '../services/results';
import { ResultEntry, RetrospectiveOutcome, RetrospectiveRecord } from '../types/results';
import { colors, radii, typography } from '../theme/colors';
import { screenContent } from '../theme/layout';
import { catalogHorizons, catalogModels, displayDate, percent } from '../utils/results';

const outcomeLabels: Record<RetrospectiveOutcome, string> = {
  verdadeiro_negativo: 'Acerto: sem aumento',
  verdadeiro_positivo: 'Acerto: com aumento',
  falso_positivo: 'Falso alarme',
  falso_negativo: 'Aumento não detectado',
};

const filters = [
  { id: 'todos', label: 'Todas' },
  { id: 'erros', label: 'Erros' },
  { id: 'falso_positivo', label: 'Falsos alarmes' },
  { id: 'falso_negativo', label: 'Não detectados' },
] as const;

const PAGE_SIZE = 12;

type Filter = (typeof filters)[number]['id'];

export default function RetrospectiveScreen() {
  const catalog = useAsyncResource('catalogo', results.getCatalog);
  const [model, setModel] = useState('random_forest');
  const [horizon, setHorizon] = useState(4);

  if (catalog.error)
    return <ErrorState message={catalog.error} onRetry={catalog.reload} />;
  if (!catalog.data) return <LoadingState />;

  const available = {
    ...catalog.data,
    resultados: catalog.data.resultados.filter((entry) => entry.retrospectiva),
  };
  const models = catalogModels(available);
  if (!models.length)
    return (
      <EmptyState
        title="Retrospectiva a caminho."
        message="O catálogo ainda não contém resultados históricos para esta seção."
      />
    );
  const selectedModel = models.some((item) => item.id === model) ? model : models[0].id;
  const horizons = catalogHorizons(available, selectedModel);
  const selectedHorizon = horizons.includes(horizon) ? horizon : horizons[0];
  const entry = available.resultados.find(
    (item) => item.modelo === selectedModel && item.horizonteSemanas === selectedHorizon,
  )!;

  return (
    <ScrollView style={styles.screen} contentContainerStyle={screenContent}>
      <ScreenHeader
        title="Olhar para aprender."
        subtitle="Compare os aumentos previstos e observados, semana a semana."
        icon="time-outline"
      />
      <ModelSelector
        models={models}
        selectedModelId={selectedModel}
        onSelect={setModel}
      />
      <Text style={styles.label}>Horizonte de previsão</Text>
      <HorizonTabs
        horizons={catalogHorizons(available)}
        availableHorizons={horizons}
        selected={selectedHorizon}
        onSelect={setHorizon}
      />
      <RetrospectiveDetails entry={entry} key={entry.retrospectiva} />
    </ScrollView>
  );
}

function RetrospectiveDetails({ entry }: { entry: ResultEntry }) {
  const load = useCallback(() => results.getRetrospective(entry), [entry]);
  const resource = useAsyncResource(entry.retrospectiva ?? '', load);
  const [filter, setFilter] = useState<Filter>('todos');
  const [page, setPage] = useState(0);

  if (resource.error)
    return <ErrorState message={resource.error} onRetry={resource.reload} />;
  if (!resource.data) return <LoadingState label="Carregando retrospectiva…" />;

  const value = resource.data;
  const correct =
    value.contagens.verdadeiro_positivo + value.contagens.verdadeiro_negativo;
  const records = [...value.registros].reverse().filter((record) => {
    if (filter === 'erros') return !record.acertou;
    return filter === 'todos' || record.resultado === filter;
  });
  const pages = Math.max(1, Math.ceil(records.length / PAGE_SIZE));
  const selectedPage = Math.min(page, pages - 1);
  const visible = records.slice(selectedPage * PAGE_SIZE, (selectedPage + 1) * PAGE_SIZE);

  return (
    <View style={styles.details}>
      <View style={styles.hero}>
        <Text style={styles.eyebrow}>
          {value.nomeModelo} · {value.horizonteSemanas} semanas
        </Text>
        <Text style={styles.accuracy}>{percent(value.desempenhoHistorico.acuracia)}</Text>
        <Text style={styles.body}>
          de acerto em {value.registros.length} semanas de teste.
        </Text>
        <Text style={styles.note}>
          Semanas-alvo: {displayDate(value.periodoAlvo.inicio)} a{' '}
          {displayDate(value.periodoAlvo.fim)}.
        </Text>
      </View>
      <View style={styles.stats}>
        <Stat label="Acertos" value={correct} />
        <Stat label="Falsos alarmes" value={value.contagens.falso_positivo} />
        <Stat label="Aumentos não detectados" value={value.contagens.falso_negativo} />
      </View>
      <Text style={styles.note}>
        Resumo do histórico completo; os filtros abaixo alteram somente a lista de
        semanas.
      </Text>
      <Text style={styles.body}>Critério: {value.criterio}</Text>
      <Text style={styles.section}>O que aconteceu em cada semana?</Text>
      <Text style={styles.note}>
        Da semana-alvo mais recente para a mais antiga. “Sim” indica aumento de pelo menos
        50% segundo o critério acima.
      </Text>
      <View style={styles.filters}>
        {filters.map((item) => (
          <Pressable
            key={item.id}
            accessibilityRole="button"
            accessibilityState={{ selected: filter === item.id }}
            onPress={() => {
              setFilter(item.id);
              setPage(0);
            }}
            style={[styles.chip, filter === item.id && styles.selectedChip]}
          >
            <Text
              style={[styles.chipText, filter === item.id && styles.selectedChipText]}
            >
              {item.label}
            </Text>
          </Pressable>
        ))}
      </View>
      <Text accessibilityLiveRegion="polite" style={styles.note}>
        {records.length} semanas neste filtro.
      </Text>
      {visible.map((record) => (
        <WeekRecord key={record.dataAlvo} record={record} />
      ))}
      {!records.length && (
        <Text style={styles.body}>Nenhuma semana corresponde a este filtro.</Text>
      )}
      {pages > 1 && (
        <View style={styles.pagination}>
          <PageButton
            label="Anterior"
            disabled={selectedPage === 0}
            onPress={() => setPage(selectedPage - 1)}
          />
          <Text style={styles.note}>
            {selectedPage + 1} / {pages}
          </Text>
          <PageButton
            label="Próxima"
            disabled={selectedPage === pages - 1}
            onPress={() => setPage(selectedPage + 1)}
          />
        </View>
      )}
      <View style={styles.notice}>
        <Text style={styles.title}>Modelo experimental.</Text>
        <Text style={styles.note}>{value.notaMetodologica}</Text>
        <Text style={styles.note}>{value.aviso}</Text>
      </View>
    </View>
  );
}

function WeekRecord({ record }: { record: RetrospectiveRecord }) {
  return (
    <View style={styles.week}>
      <Text style={styles.title}>Semana de {displayDate(record.dataAlvo)}</Text>
      <Text style={styles.note}>
        Previsão emitida em {displayDate(record.dataEmissao)}.
      </Text>
      <View style={styles.comparison}>
        <Text style={styles.comparisonText}>
          Previsto: {record.aumentoPrevisto ? 'sim' : 'não'}
        </Text>
        <Text style={styles.comparisonText}>
          Observado: {record.aumentoObservado ? 'sim' : 'não'}
        </Text>
      </View>
      <Text
        style={[
          styles.outcome,
          { color: record.acertou ? colors.success : colors.danger },
        ]}
      >
        {outcomeLabels[record.resultado]}
      </Text>
      <Text style={styles.note}>
        Casos observados: {record.casosObservados.toLocaleString('pt-BR')} casos/semana.
      </Text>
      <Text style={styles.note}>
        Média de referência: {record.mediaCasosReferencia.toLocaleString('pt-BR')} ·
        Limiar de aumento: {record.limiteCasosAumento.toLocaleString('pt-BR')}{' '}
        casos/semana.
      </Text>
    </View>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <View style={styles.stat}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.note}>{label}</Text>
    </View>
  );
}

function PageButton({
  label,
  disabled,
  onPress,
}: {
  label: string;
  disabled: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled}
      accessibilityState={{ disabled }}
      onPress={onPress}
      style={[styles.chip, disabled && styles.disabled]}
    >
      <Text style={styles.chipText}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  label: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 24,
    marginBottom: 10,
  },
  details: { marginTop: 24, gap: 16 },
  hero: { backgroundColor: colors.cyan, padding: 26, borderRadius: radii.lg },
  eyebrow: { ...typography.caption, fontWeight: '600', color: colors.textPrimary },
  accuracy: {
    fontSize: 48,
    lineHeight: 60,
    letterSpacing: -1.5,
    fontWeight: '600',
    color: colors.textPrimary,
    marginTop: 16,
  },
  body: { ...typography.body, color: colors.textPrimary },
  note: { ...typography.caption, color: colors.textSecondary, marginTop: 6 },
  stats: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  stat: {
    flex: 1,
    minWidth: 95,
    backgroundColor: colors.lavender,
    borderRadius: radii.md,
    padding: 16,
  },
  statValue: { ...typography.h2, color: colors.textPrimary },
  section: { ...typography.h2, color: colors.textPrimary, marginTop: 10 },
  filters: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: {
    backgroundColor: colors.surfaceSoft,
    paddingVertical: 14,
    paddingHorizontal: 18,
    borderRadius: radii.pill,
  },
  chipText: { ...typography.caption, color: colors.textPrimary, fontWeight: '600' },
  selectedChip: { backgroundColor: colors.primary },
  selectedChipText: { color: colors.surface },
  week: { padding: 22, backgroundColor: colors.surfaceSoft, borderRadius: radii.md },
  title: { ...typography.h3, color: colors.textPrimary },
  comparison: { flexDirection: 'row', flexWrap: 'wrap', gap: 20, marginTop: 18 },
  comparisonText: { ...typography.body, fontWeight: '600', color: colors.textPrimary },
  outcome: { ...typography.body, fontWeight: '600', marginTop: 12 },
  pagination: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 10,
  },
  disabled: { opacity: 0.4 },
  notice: { paddingVertical: 16 },
});
