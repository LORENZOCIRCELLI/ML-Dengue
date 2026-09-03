import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { colors, radii, spacing, typography } from '../theme/colors';

interface Props {
  horizons: number[]; // e.g. [1, 2, 3, 4] — generic, not hard-coded to today's notebook
  availableHorizons: number[]; // horizons that actually have model data
  selected: number;
  onSelect: (horizon: number) => void;
}

export default function HorizonTabs({ horizons, availableHorizons, selected, onSelect }: Props) {
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
  row: { flexDirection: 'row', gap: spacing.sm, backgroundColor: colors.surfaceSoft, padding: 4, borderRadius: radii.md },
  tab: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    borderRadius: radii.sm,
    backgroundColor: 'transparent',
    borderWidth: 0,
  },
  tabSelected: { backgroundColor: colors.surface, shadowColor: '#173B42', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 5, elevation: 2 },
  tabDisabled: { backgroundColor: colors.background, borderStyle: 'dashed' },
  tabText: { ...typography.body, fontWeight: '600', color: colors.textPrimary },
  tabTextSelected: { color: colors.primaryDark },
  tabTextDisabled: { color: colors.muted },
});
