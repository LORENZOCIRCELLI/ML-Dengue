import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { colors, radii, spacing, typography } from '../theme/colors';

interface Props {
  horizons: readonly number[];
  availableHorizons: readonly number[];
  selected: number;
  onSelect: (horizon: number) => void;
}

export default function HorizonTabs({
  horizons,
  availableHorizons,
  selected,
  onSelect,
}: Props) {
  return (
    <View style={styles.row}>
      {horizons.map((h) => {
        const isSelected = h === selected;
        const isAvailable = availableHorizons.includes(h);
        return (
          <TouchableOpacity
            key={h}
            onPress={() => onSelect(h)}
            disabled={!isAvailable}
            accessibilityRole="tab"
            accessibilityState={{ selected: isSelected, disabled: !isAvailable }}
            style={[
              styles.tab,
              isSelected && isAvailable && styles.tabSelected,
              !isAvailable && styles.tabDisabled,
            ]}
          >
            <Text
              style={[
                styles.tabText,
                isSelected && isAvailable && styles.tabTextSelected,
                !isAvailable && styles.tabTextDisabled,
              ]}
            >
              {h} sem.
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    gap: spacing.sm,
    backgroundColor: colors.surfaceSoft,
    padding: 4,
    borderRadius: radii.pill,
  },
  tab: {
    flex: 1,
    paddingVertical: 14,
    alignItems: 'center',
    borderRadius: radii.pill,
    backgroundColor: 'transparent',
    borderWidth: 0,
  },
  tabSelected: {
    backgroundColor: colors.primary,
    shadowColor: '#173B42',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 5,
    elevation: 2,
  },
  tabDisabled: {
    backgroundColor: colors.background,
    borderStyle: 'dashed',
  },
  tabText: {
    ...typography.body,
    fontWeight: '600',
    color: colors.textPrimary,
  },
  tabTextSelected: {
    color: colors.surface,
  },
  tabTextDisabled: {
    color: colors.muted,
  },
});
