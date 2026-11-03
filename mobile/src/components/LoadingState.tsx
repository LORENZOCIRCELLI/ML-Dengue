import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { colors, typography } from '../theme/colors';

interface Props {
  label?: string;
}

export default function LoadingState({ label = 'Carregando seus dados…' }: Props) {
  return (
    <View style={styles.container}>
      <View style={styles.indicator}>
        <ActivityIndicator size="large" color={colors.textPrimary} />
      </View>
      <Text accessibilityRole="header" style={styles.title}>
        Só um instante.
      </Text>
      <Text
        accessibilityRole="progressbar"
        accessibilityLiveRegion="polite"
        style={styles.label}
      >
        {label}
      </Text>
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
  indicator: {
    width: 88,
    height: 88,
    borderRadius: 30,
    backgroundColor: colors.cyan,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 28,
  },
  title: {
    ...typography.h2,
    color: colors.textPrimary,
  },
  label: {
    ...typography.body,
    color: colors.textSecondary,
    marginTop: 10,
    textAlign: 'center',
  },
});
