import { StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, typography } from '../theme/colors';

interface Props {
  title?: string;
  message?: string;
}

export default function EmptyState({
  title = 'Um espaço para novidades.',
  message = 'Quando houver dados disponíveis, eles aparecerão aqui.',
}: Props) {
  return (
    <View style={styles.container}>
      <View style={styles.icon}>
        <Ionicons name="file-tray-outline" size={34} color={colors.textPrimary} />
      </View>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.message}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
  },
  icon: {
    width: 88,
    height: 88,
    borderRadius: 30,
    backgroundColor: colors.lavender,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
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
    marginTop: 12,
    maxWidth: 360,
  },
});
