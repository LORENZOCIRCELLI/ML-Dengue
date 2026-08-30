import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { RiskLevel } from '../types';
import { radii, spacing, typography } from '../theme/colors';
import { riskColor, riskLabel } from '../utils/risk';

interface Props {
  level: RiskLevel | undefined;
  size?: 'sm' | 'lg';
}

// Deliberately text + color, never color alone (accessibility, and Nielsen
// #2 — match real-world language: "Risco alto", not "P(surto) = 0.71").
export default function RiskBadge({ level, size = 'sm' }: Props) {
  const color = riskColor(level);
  const label = riskLabel(level);
  const isLarge = size === 'lg';

  return (
    <View style={[styles.badge, { backgroundColor: `${color}1A`, borderColor: color }]}>
      <View style={[styles.dot, { backgroundColor: color }]} />
      <Text style={[styles.text, isLarge && styles.textLg, { color }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.sm,
    borderRadius: radii.pill,
    borderWidth: 1,
  },
  dot: { width: 8, height: 8, borderRadius: 4, marginRight: spacing.xs },
  text: { ...typography.caption, fontWeight: '700' },
  textLg: { fontSize: 15 },
});
