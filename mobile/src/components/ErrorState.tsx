import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, radii, typography } from '../theme/colors';

interface Props {
  message?: string;
  onRetry?: () => void;
}

export default function ErrorState({
  message = 'Não foi possível carregar os dados agora.',
  onRetry,
}: Props) {
  return (
    <View style={styles.container}>
      <View style={styles.icon}>
        <Ionicons name="cloud-offline-outline" size={36} color={colors.textPrimary} />
      </View>
      <Text accessibilityRole="header" style={styles.title}>
        Vamos tentar de novo?
      </Text>
      <Text accessibilityRole="alert" style={styles.message}>
        {message}
      </Text>
      {onRetry && (
        <Pressable
          style={({ pressed }) => [styles.button, pressed && styles.pressed]}
          onPress={onRetry}
          accessibilityRole="button"
        >
          <Text style={styles.buttonText}>Tentar novamente</Text>
          <Ionicons name="arrow-forward" size={19} color={colors.surface} />
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
    backgroundColor: colors.background,
  },
  icon: {
    width: 96,
    height: 96,
    backgroundColor: colors.pink,
    borderRadius: 32,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 28,
  },
  title: {
    ...typography.h2,
    color: colors.textPrimary,
    textAlign: 'center',
  },
  message: {
    ...typography.body,
    color: colors.textSecondary,
    textAlign: 'center',
    maxWidth: 380,
    marginTop: 12,
    marginBottom: 28,
  },
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 20,
    backgroundColor: colors.primary,
    paddingVertical: 18,
    paddingHorizontal: 28,
    borderRadius: radii.pill,
    minHeight: 56,
  },
  pressed: {
    opacity: 0.75,
  },
  buttonText: {
    ...typography.body,
    color: colors.surface,
    fontWeight: '600',
  },
});
