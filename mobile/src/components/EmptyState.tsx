import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors, spacing, typography } from '../theme/colors';

interface Props {
  title?: string;
  message?: string;
}

export default function EmptyState({
  title = 'Nada por aqui ainda',
  message = 'Quando houver dados disponíveis, eles aparecerão nesta tela.',
}: Props) {
  return (
    <View style={styles.container}>
      <Text style={styles.icon}>🗂️</Text>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.message}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing.lg },
  icon: { fontSize: 32, marginBottom: spacing.sm },
  title: { ...typography.h3, color: colors.textPrimary, marginBottom: spacing.xs },
  message: { ...typography.body, color: colors.textSecondary, textAlign: 'center' },
});
