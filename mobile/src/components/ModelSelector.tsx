import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { colors, radii, spacing, typography } from '../theme/colors';

interface Props {
  models: { id: string; shortName: string }[];
  selectedModelId: string;
  onSelect: (modelId: string) => void;
}

export default function ModelSelector({ models, selectedModelId, onSelect }: Props) {
  return (
    <View>
      <Text style={styles.label}>Modelo de previsão</Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.row}
      >
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
            </TouchableOpacity>
          );
        })}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  label: {
    ...typography.caption,
    color: colors.textSecondary,
    fontWeight: '700',
    marginBottom: spacing.sm,
  },
  row: {
    gap: spacing.sm,
    paddingRight: spacing.md,
  },
  chip: {
    paddingVertical: 14,
    paddingHorizontal: spacing.md,
    borderRadius: radii.pill,
    backgroundColor: colors.surfaceSoft,
    borderWidth: 0,
    borderColor: colors.border,
    marginRight: 0,
  },
  chipSelected: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
    shadowColor: colors.primaryDark,
    shadowOffset: {
      width: 0,
      height: 3,
    },
    shadowOpacity: 0.15,
    shadowRadius: 6,
    elevation: 2,
  },
  chipText: {
    ...typography.body,
    color: colors.textPrimary,
    fontWeight: '600',
  },
  chipTextSelected: {
    color: '#fff',
  },
  recommended: {
    ...typography.caption,
    color: colors.success,
    marginTop: 2,
  },
});
