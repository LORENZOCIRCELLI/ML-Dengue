import React from 'react';
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { ModelInfo } from '../types';
import { colors, radii, spacing, typography } from '../theme/colors';

interface Props {
  models: ModelInfo[];
  selectedModelId: string;
  onSelect: (modelId: string) => void;
}

// Model selection is a data-source switch, never an execution trigger:
// selecting a model only changes which JSON the app requests/filters.
// Human-readable names only — no "rf_optimized_v2_gridsearch" in the UI.
export default function ModelSelector({ models, selectedModelId, onSelect }: Props) {
  return (
    <View>
      <Text style={styles.label}>Modelo de previsão</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.row}>
        {models.map((model) => {
          const selected = model.id === selectedModelId;
          return (
            <TouchableOpacity
              key={model.id}
              onPress={() => onSelect(model.id)}
              accessibilityRole="button"
              accessibilityState={{ selected }}
              style={[styles.chip, selected && styles.chipSelected]}
            >
              <Text style={[styles.chipText, selected && styles.chipTextSelected]}>
                {model.shortName}
              </Text>
              {model.isDefault && !selected && <Text style={styles.recommended}>Recomendado</Text>}
            </TouchableOpacity>
          );
        })}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  label: { ...typography.caption, color: colors.textSecondary, marginBottom: spacing.xs, marginLeft: spacing.md },
  row: { paddingHorizontal: spacing.md, gap: spacing.sm },
  chip: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderRadius: radii.pill,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    marginRight: spacing.sm,
  },
  chipSelected: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { ...typography.body, color: colors.textPrimary, fontWeight: '600' },
  chipTextSelected: { color: '#fff' },
  recommended: { ...typography.caption, color: colors.success, marginTop: 2 },
});
