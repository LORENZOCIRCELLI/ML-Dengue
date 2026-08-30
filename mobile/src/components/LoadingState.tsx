import React from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { colors, spacing, typography } from '../theme/colors';

interface Props {
  label?: string;
}

// Nielsen #1 — Visibility of system status: every async screen must show
// this instead of a blank view while data loads.
export default function LoadingState({ label = 'Carregando dados...' }: Props) {
  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color={colors.primary} />
      <Text style={styles.label}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing.lg },
  label: { ...typography.body, color: colors.textSecondary, marginTop: spacing.md },
});
