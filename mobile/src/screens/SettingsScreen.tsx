import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { OFFICIAL_HORIZONS_WEEKS } from '../config/api.config';
import { cardShadow, colors, radii, spacing, typography } from '../theme/colors';

export default function SettingsScreen() {
  return <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
    <Text style={styles.title}>Configurações</Text>
    <Section title="Região monitorada"><Row label="Cidade" value="Ribeirão Preto, SP" /><Row label="País" value="Brasil" /></Section>
    <Section title="Dados reais">
      <Row label="Fonte" value="Amazon S3" />
      <Row label="Horizontes disponíveis" value={OFFICIAL_HORIZONS_WEEKS.map(h => `${h} sem.`).join(', ')} />
      <Row label="Séries" value="Casos, MM4 e MM12" />
      <Row label="Métricas" value="Classificação e regressão" />
    </Section>
    <Section title="Modelos"><Text style={styles.about}>Random Forest baseline e otimizado, LSTM NumPy e LSTM PyTorch. O painel identifica o melhor classificador pela ROC-AUC do horizonte analisado.</Text></Section>
    <Section title="Notícias"><Text style={styles.about}>Notícias brasileiras sobre dengue, zika, chikungunya, febre amarela e outras arboviroses, fornecidas pela GNews.</Text></Section>
  </ScrollView>;
}
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return <View style={styles.section}><Text style={styles.sectionTitle}>{title}</Text><View style={styles.card}>{children}</View></View>;
}
function Row({ label, value }: { label: string; value: string }) {
  return <View style={styles.row}><Text style={styles.label}>{label}</Text><Text style={styles.value}>{value}</Text></View>;
}
const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background }, content: { paddingHorizontal: 20, paddingTop: spacing.md, paddingBottom: spacing.xxl }, title: { ...typography.h1, color: colors.textPrimary, marginBottom: spacing.lg },
  section: { marginBottom: spacing.lg }, sectionTitle: { ...typography.caption, color: colors.primary, fontWeight: '800', letterSpacing: 0.7, marginBottom: spacing.sm, textTransform: 'uppercase' },
  card: { ...cardShadow, backgroundColor: colors.surface, borderRadius: radii.lg, borderWidth: 0, overflow: 'hidden' },
  row: { flexDirection: 'row', justifyContent: 'space-between', gap: spacing.md, paddingVertical: 14, paddingHorizontal: spacing.lg, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  label: { ...typography.body, color: colors.textSecondary }, value: { ...typography.body, color: colors.textPrimary, fontWeight: '600', flex: 1, textAlign: 'right' },
  about: { ...typography.body, color: colors.textSecondary, padding: spacing.lg },
});
