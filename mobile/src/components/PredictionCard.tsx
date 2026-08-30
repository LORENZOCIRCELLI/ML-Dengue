import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Prediction } from '../types';
import { colors, radii, spacing, typography } from '../theme/colors';
import { formatDate, formatPercent, riskDescription } from '../utils/risk';
import RiskBadge from './RiskBadge';

interface Props {
  horizonWeeks: number;
  prediction?: Prediction;
}

// The single most important widget in the app: answers "is an outbreak
// expected?" at a glance, with no ML jargon. If there's no prediction for
// this horizon yet, it says so plainly instead of showing a blank card.
export default function PredictionCard({ horizonWeeks, prediction }: Props) {
  if (!prediction) {
    return (
      <View style={[styles.card, styles.cardEmpty]}>
        <Text style={styles.horizon}>{horizonWeeks} semana{horizonWeeks > 1 ? 's' : ''}</Text>
        <Text style={styles.unavailable}>Previsão ainda não disponível para este horizonte.</Text>
      </View>
    );
  }

  const isRegression = prediction.expectedCases !== undefined;

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <Text style={styles.horizon}>{horizonWeeks} semana{horizonWeeks > 1 ? 's' : ''}</Text>
        {!isRegression && <RiskBadge level={prediction.riskLevel} />}
      </View>

      {isRegression ? (
        <Text style={styles.bigNumber}>{Math.round(prediction.expectedCases!)} casos esperados</Text>
      ) : (
        <>
          <Text style={styles.bigNumber}>{formatPercent(prediction.outbreakProbability)}</Text>
          <Text style={styles.subLabel}>probabilidade de surto</Text>
          <Text style={styles.description}>{riskDescription(prediction.riskLevel)}</Text>
        </>
      )}

      <View style={styles.footerRow}>
        <Text style={styles.footerText}>Referente a {formatDate(prediction.targetDate)}</Text>
        <Text style={styles.footerText}>Base: {formatDate(prediction.asOfDate)}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    width: 220,
    marginRight: spacing.sm,
  },
  cardEmpty: { justifyContent: 'center', alignItems: 'center', minHeight: 140 },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.sm },
  horizon: { ...typography.h3, color: colors.textPrimary },
  bigNumber: { ...typography.h1, color: colors.textPrimary, marginTop: spacing.xs },
  subLabel: { ...typography.caption, color: colors.textSecondary, marginBottom: spacing.xs },
  description: { ...typography.caption, color: colors.textSecondary },
  footerRow: { marginTop: spacing.sm, borderTopWidth: 1, borderTopColor: colors.border, paddingTop: spacing.xs },
  footerText: { ...typography.caption, color: colors.muted },
  unavailable: { ...typography.caption, color: colors.muted, textAlign: 'center', marginTop: spacing.sm },
});
