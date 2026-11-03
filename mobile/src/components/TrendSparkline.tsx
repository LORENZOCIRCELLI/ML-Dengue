import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';
import { colors } from '../theme/colors';

interface Props {
  values: number[];
}

export default function TrendSparkline({ values }: Props) {
  const [width, setWidth] = useState(0);
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const range = maximum - minimum || 1;
  const points = values.map((value, index) => ({
    x: 4 + (index / Math.max(values.length - 1, 1)) * Math.max(width - 8, 0),
    y: 64 - ((value - minimum) / range) * 52,
  }));
  const line = points
    .map((point, index) => `${index ? 'L' : 'M'} ${point.x} ${point.y}`)
    .join(' ');
  const last = points[points.length - 1];

  return (
    <View
      accessible
      accessibilityRole="image"
      accessibilityLabel="Tendência dos casos nas últimas doze semanas."
      onLayout={(event) => setWidth(event.nativeEvent.layout.width)}
      style={styles.container}
    >
      {width > 0 && last && (
        <Svg width={width} height={76}>
          <Path
            d={line}
            stroke={colors.textPrimary}
            strokeWidth={2}
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <Circle cx={last.x} cy={last.y} r={4} fill={colors.textPrimary} />
        </Svg>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    height: 76,
    marginTop: 24,
  },
});
