import { useCallback, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { useAsyncResource } from '../hooks/useAsyncResource';
import { results } from '../services/results';
import { ResultEntry } from '../types/results';
import { colors, radii, typography } from '../theme/colors';
import { featureName } from '../utils/results';

const methodNames: Record<string, string> = {
  shap: 'SHAP',
  saliency: 'Saliency',
  integrated_gradients: 'Integrated Gradients',
};

export default function ExplanationPanel({ entry }: { entry: ResultEntry }) {
  const load = useCallback(() => results.getExplanation(entry), [entry]);
  const resource = useAsyncResource(entry.explicabilidade, load);
  const [selectedMethod, setSelectedMethod] = useState('');

  if (resource.error) {
    return (
      <View style={styles.card}>
        <Text style={styles.body}>{resource.error}</Text>
        <Pressable
          onPress={resource.reload}
          accessibilityRole="button"
          style={styles.retry}
        >
          <Text>Tentar explicabilidade novamente</Text>
        </Pressable>
      </View>
    );
  }
  if (!resource.data)
    return (
      <View style={styles.card}>
        <ActivityIndicator />
        <Text style={styles.note}>Carregando explicabilidade…</Text>
      </View>
    );

  const explanation = resource.data;
  const methods = Object.keys(explanation.metodos);
  const methodKey = methods.includes(selectedMethod) ? selectedMethod : methods[0];
  const method = explanation.metodos[methodKey];
  if (!method) return null;
  const rows = [...method.importanciaPorVariavel].sort(
    (a, b) => b.mean_absolute_attribution - a.mean_absolute_attribution,
  );
  const maximum = Math.max(...rows.map((row) => row.mean_absolute_attribution), 0.000001);
  const local = [...method.previsao]
    .sort((a, b) => Math.abs(b.attribution) - Math.abs(a.attribution))
    .slice(0, 8);

  return (
    <View style={styles.card}>
      <Text style={styles.title}>Entenda o modelo.</Text>
      <View style={styles.tabs}>
        {methods.map((key) => (
          <Pressable
            key={key}
            onPress={() => setSelectedMethod(key)}
            accessibilityRole="button"
            accessibilityState={{ selected: methodKey === key }}
            style={[styles.tab, methodKey === key && styles.selected]}
          >
            <Text style={[styles.tabText, methodKey === key && styles.selectedText]}>
              {methodNames[key] ?? key}
            </Text>
          </Pressable>
        ))}
      </View>
      <Text style={styles.subtitle}>Importância global por variável</Text>
      <Text style={styles.note}>
        Partição: {explanation.particaoGlobal}. Unidade: {method.unidade}.
      </Text>
      {rows.map((row) => (
        <View key={row.feature} style={styles.importance}>
          <View style={styles.line}>
            <Text style={styles.feature}>{featureName(row.feature)}</Text>
            <Text style={styles.number}>{row.mean_absolute_attribution.toFixed(4)}</Text>
          </View>
          <View style={styles.track}>
            <View
              style={[
                styles.bar,
                { width: `${(row.mean_absolute_attribution / maximum) * 100}%` },
              ]}
            />
          </View>
        </View>
      ))}
      <Text style={styles.note}>{method.regraAgregacao}.</Text>
      <Text style={styles.subtitle}>Contribuições nesta previsão</Text>
      <Text style={styles.note}>
        Oito maiores contribuições em valor absoluto. Valores assinados na unidade do
        método.
      </Text>
      {local.map((row) => (
        <View style={styles.localRow} key={row.feature}>
          <Text style={styles.feature}>{featureName(row.feature)}</Text>
          <Text style={styles.number}>
            {row.attribution >= 0 ? '+' : ''}
            {row.attribution.toFixed(4)}
          </Text>
        </View>
      ))}
      <Text style={styles.note}>{explanation.interpretacao}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surfaceSoft,
    borderRadius: radii.lg,
    padding: 24,
    marginTop: 24,
  },
  title: { ...typography.h2, color: colors.textPrimary },
  subtitle: { ...typography.h3, color: colors.textPrimary, marginTop: 26 },
  body: { ...typography.body, color: colors.textPrimary },
  note: { ...typography.caption, color: colors.textSecondary, marginTop: 10 },
  tabs: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 20 },
  tab: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: colors.surface,
    borderRadius: radii.pill,
  },
  selected: { backgroundColor: colors.primary },
  tabText: { ...typography.caption, color: colors.textPrimary, fontWeight: '600' },
  selectedText: { color: colors.surface },
  importance: { marginTop: 20 },
  line: { flexDirection: 'row', justifyContent: 'space-between', gap: 12 },
  feature: { ...typography.caption, flex: 1, color: colors.textPrimary },
  number: {
    ...typography.caption,
    fontVariant: ['tabular-nums'],
    color: colors.textPrimary,
  },
  track: { backgroundColor: colors.surface, height: 8, borderRadius: 4, marginTop: 8 },
  bar: { height: 8, backgroundColor: '#1687A7', borderRadius: 4 },
  localRow: {
    flexDirection: 'row',
    gap: 12,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  retry: { paddingVertical: 16 },
});
