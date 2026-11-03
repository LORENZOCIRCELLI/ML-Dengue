import { StyleSheet, Text, View } from 'react-native';
import { ForecastResult } from '../types/results';
import { colors, radii, typography } from '../theme/colors';
import { displayDate, percent } from '../utils/results';

interface Props {
  prediction: ForecastResult;
}

export default function PredictionCard({ prediction }: Props) {
  const historical = prediction.desempenhoHistorico;

  return (
    <View style={styles.container}>
      <View
        style={[
          styles.card,
          {
            backgroundColor: prediction.aumentoCasosPrevisto ? colors.pink : colors.cyan,
          },
        ]}
      >
        <Text style={styles.eyebrow}>
          {prediction.nomeModelo} · {prediction.horizonteSemanas} semanas
        </Text>
        <Text style={styles.date}>
          Previsão para a semana de {displayDate(prediction.dataAlvo)}
        </Text>
        <Text style={styles.label}>Aumento de casos previsto</Text>
        <Text style={styles.answer}>
          {prediction.aumentoCasosPrevisto ? 'Sim.' : 'Não.'}
        </Text>
        <Text style={styles.criterion}>Critério: {prediction.criterio}</Text>
      </View>
      <View style={styles.history}>
        <Text style={styles.eyebrow}>DESEMPENHO HISTÓRICO DO MODELO</Text>
        <Text style={styles.accuracy}>
          {percent(historical.acuracia)} <Text style={styles.unit}>de acerto</Text>
        </Text>
        <Text style={styles.body}>
          Em {historical.semanasAvaliadas} semanas avaliadas.
        </Text>
        <Text style={styles.note}>Avaliação {historical.tipoAvaliacao}.</Text>
        <Text style={styles.note}>{prediction.notaTaxaAcerto}</Text>
      </View>
      <View style={styles.notice}>
        <Text style={styles.noticeTitle}>Modelo experimental.</Text>
        <Text style={styles.note}>{prediction.aviso}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: 16 },
  card: { borderRadius: radii.lg, padding: 26 },
  eyebrow: {
    ...typography.caption,
    fontWeight: '600',
    letterSpacing: 0.8,
    color: colors.textPrimary,
  },
  date: { ...typography.h3, marginTop: 18, color: colors.textPrimary },
  label: { ...typography.body, marginTop: 28, color: colors.textPrimary },
  answer: {
    fontSize: 64,
    lineHeight: 76,
    fontWeight: '600',
    letterSpacing: -2,
    color: colors.textPrimary,
  },
  criterion: { ...typography.body, marginTop: 20, color: colors.textPrimary },
  history: { backgroundColor: colors.surfaceSoft, borderRadius: radii.lg, padding: 26 },
  accuracy: {
    fontSize: 42,
    lineHeight: 54,
    fontWeight: '600',
    letterSpacing: -1,
    color: colors.textPrimary,
    marginTop: 16,
  },
  unit: { ...typography.body, letterSpacing: 0 },
  body: { ...typography.body, color: colors.textPrimary },
  note: { ...typography.caption, color: colors.textSecondary, marginTop: 10 },
  notice: { padding: 8 },
  noticeTitle: { ...typography.h3, color: colors.textPrimary },
});
