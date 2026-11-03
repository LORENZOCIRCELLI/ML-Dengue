import { StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, typography } from '../theme/colors';

interface Props {
  title: string;
  subtitle?: string;
  eyebrow?: string;
  icon?: keyof typeof Ionicons.glyphMap;
}

export default function ScreenHeader({
  title,
  subtitle,
  eyebrow = 'AlphaDengue',
  icon = 'pulse-outline',
}: Props) {
  return (
    <View style={styles.container}>
      <View style={styles.topRow}>
        <Text style={styles.eyebrow}>{eyebrow}</Text>
        <View style={styles.icon}>
          <Ionicons name={icon} size={22} color={colors.textPrimary} />
        </View>
      </View>
      <Text accessibilityRole="header" style={styles.title}>
        {title}
      </Text>
      {subtitle && <Text style={styles.subtitle}>{subtitle}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: 28,
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  eyebrow: {
    ...typography.caption,
    color: colors.textSecondary,
    letterSpacing: 2,
    fontWeight: '600',
  },
  icon: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: colors.surfaceSoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    ...typography.h1,
    color: colors.textPrimary,
  },
  subtitle: {
    ...typography.body,
    color: colors.textSecondary,
    marginTop: 10,
    maxWidth: 480,
  },
});
