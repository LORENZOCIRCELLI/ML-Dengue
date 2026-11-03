import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import Svg, { Line, Path, Text as SvgText } from 'react-native-svg';
import { MetricsResult } from '../types/results';
import { colors, typography } from '../theme/colors';

export default function EvaluationRoc({ metrics }: { metrics: MetricsResult }) {
  const [width, setWidth] = useState(0);
  const points = metrics.curvasRoc.filter((point) => point.split === 'teste');
  const left = 38;
  const top = 12;
  const size = Math.max(width - left - 16, 1);
  const height = 160;
  const line = points
    .map(
      (point, index) =>
        `${index ? 'L' : 'M'} ${left + point.false_positive_rate * size} ${top + (1 - point.true_positive_rate) * height}`,
    )
    .join(' ');

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Curva ROC · teste</Text>
      <View
        onLayout={(event) => setWidth(event.nativeEvent.layout.width)}
        accessible
        accessibilityRole="image"
        accessibilityLabel="Curva ROC do modelo na partição de teste."
        style={styles.plot}
      >
        {width > 0 && (
          <Svg width={width} height={210}>
            {[0, 0.5, 1].map((tick) => (
              <Line
                key={tick}
                x1={left}
                x2={width - 16}
                y1={top + (1 - tick) * height}
                y2={top + (1 - tick) * height}
                stroke="#11111322"
              />
            ))}
            <Line
              x1={left}
              y1={top + height}
              x2={left + size}
              y2={top}
              stroke={colors.textSecondary}
              strokeDasharray="4,4"
            />
            <Path d={line} stroke={colors.textPrimary} strokeWidth={2.5} fill="none" />
            {[0, 0.5, 1].map((tick) => (
              <SvgText
                key={`x${tick}`}
                x={left + tick * size}
                y={top + height + 20}
                textAnchor="middle"
                fontSize={11}
                fill={colors.textPrimary}
              >
                {tick}
              </SvgText>
            ))}
            {[0, 0.5, 1].map((tick) => (
              <SvgText
                key={`y${tick}`}
                x={left - 8}
                y={top + (1 - tick) * height + 4}
                textAnchor="end"
                fontSize={11}
                fill={colors.textPrimary}
              >
                {tick}
              </SvgText>
            ))}
          </Svg>
        )}
      </View>
      <Text style={styles.caption}>
        Eixo X: taxa de falsos positivos (0–1). Eixo Y: recall (0–1).
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginTop: 26 },
  title: { ...typography.h3, color: colors.textPrimary },
  plot: { height: 210, marginTop: 12 },
  caption: { ...typography.caption, color: colors.textPrimary },
});
