import React, { useCallback, useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { api } from '../services/api';
import { Metadata } from '../types';
import { colors, radii, spacing, typography } from '../theme/colors';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import { formatDate } from '../utils/risk';

export default function SettingsScreen() {
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setMetadata(await api.getMetadata());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro inesperado.');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!metadata) return <LoadingState />;

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Configurações</Text>

      <SettingsSection title="Região monitorada">
        <SettingsRow label="Cidade" value={`${metadata.region.name}, ${metadata.region.state}`} />
        <SettingsRow label="País" value={metadata.region.country} />
      </SettingsSection>

      <SettingsSection title="Dados">
        <SettingsRow label="Período coberto" value={`${formatDate(metadata.dataRange.start)} – ${formatDate(metadata.dataRange.end)}`} />
        <SettingsRow label="Variável alvo" value={metadata.targetVariable.label} />
        <SettingsRow label="Horizontes disponíveis" value={metadata.availableHorizonsWeeks.map((h) => `${h} sem.`).join(', ')} />
        <SettingsRow label="Horizontes planejados" value={metadata.plannedHorizonsWeeks.map((h) => `${h} sem.`).join(', ')} />
      </SettingsSection>

      <SettingsSection title="Sobre a previsão">
        <Text style={styles.aboutText}>{metadata.outbreakLabelDefinition.method}</Text>
        {metadata.notes && <Text style={styles.noteText}>{metadata.notes}</Text>}
      </SettingsSection>
    </ScrollView>
  );
}

function SettingsSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <View style={styles.sectionCard}>{children}</View>
    </View>
  );
}

function SettingsRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.md, paddingBottom: spacing.xl },
  title: { ...typography.h1, color: colors.textPrimary, marginBottom: spacing.md },
  section: { marginBottom: spacing.lg },
  sectionTitle: { ...typography.caption, color: colors.textSecondary, marginBottom: spacing.xs, textTransform: 'uppercase' },
  sectionCard: { backgroundColor: colors.surface, borderRadius: radii.md, borderWidth: 1, borderColor: colors.border },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  rowLabel: { ...typography.body, color: colors.textSecondary },
  rowValue: { ...typography.body, color: colors.textPrimary, fontWeight: '600', flexShrink: 1, textAlign: 'right' },
  aboutText: { ...typography.body, color: colors.textSecondary, padding: spacing.md },
  noteText: { ...typography.caption, color: colors.warning, paddingHorizontal: spacing.md, paddingBottom: spacing.md },
});
