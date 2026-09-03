import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { cardShadow, colors, radii, spacing, typography } from '../theme/colors';

interface Props {
  message?: string;
  onRetry?: () => void;
}

// Nielsen #9 — Help users recognize, diagnose, and recover from errors.
// Always plain language, always an explicit way forward (retry).
export default function ErrorState({
  message = 'Não foi possível carregar os dados agora.',
  onRetry,
}: Props) {
  return (
    <View style={styles.container}><View style={styles.card}>
      <Text style={styles.icon}>!</Text>
      <Text style={styles.title}>Algo deu errado</Text>
      <Text style={styles.message}>{message}</Text>
      {onRetry && (
        <Pressable style={styles.button} onPress={onRetry} accessibilityRole="button">
          <Text style={styles.buttonText}>Tentar novamente</Text>
        </Pressable>
      )}
    </View></View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing.lg, backgroundColor: colors.background },
  card: { ...cardShadow, width: '100%', maxWidth: 420, alignItems: 'center', backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.xl },
  icon: { width: 44, height: 44, borderRadius: 22, textAlign: 'center', textAlignVertical: 'center', fontSize: 24, fontWeight: '800', color: colors.danger, backgroundColor: `${colors.danger}18`, marginBottom: spacing.md },
  title: { ...typography.h3, color: colors.textPrimary, marginBottom: spacing.xs },
  message: { ...typography.body, color: colors.textSecondary, textAlign: 'center', marginBottom: spacing.md },
  button: {
    backgroundColor: colors.primary,
    paddingVertical: 12,
    paddingHorizontal: spacing.lg,
    borderRadius: radii.pill,
  },
  buttonText: { color: '#fff', fontWeight: '600' },
});
