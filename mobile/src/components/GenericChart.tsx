import React, { useMemo, useState } from 'react';
import { LayoutChangeEvent, StyleSheet, Text, View } from 'react-native';
import Svg, { Circle, G, Line, Path, Rect } from 'react-native-svg';
import { ChartDefinition } from '../types';
import { colors, radii, spacing, typography } from '../theme/colors';

interface Props {
  chart: ChartDefinition;
  height?: number;
}

const CHART_PADDING = { top: 16, right: 12, bottom: 28, left: 36 };

// One component renders every chart in charts.json — line, bar, or area —
// because it only reads the generic schema (xAxis/yAxis/series), never a
// variable name. Adding a new chart to the notebook export requires zero
// frontend changes as long as it fits this schema.
export default function GenericChart({ chart, height = 220 }: Props) {
  const [width, setWidth] = useState(0);

  const onLayout = (e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width);

  const { allYValues, categories } = useMemo(() => {
    const ys: number[] = [];
    const cats = new Set<string>();
    chart.series.forEach((s) =>
      s.data.forEach((p) => {
        if (p.y !== null && p.y !== undefined) ys.push(p.y);
        cats.add(p.x);
      })
    );
    return { allYValues: ys, categories: Array.from(cats) };
  }, [chart]);

  if (allYValues.length === 0) {
    return (
      <View style={[styles.card, { height }]}>
        <Text style={styles.title}>{chart.title}</Text>
        <Text style={styles.empty}>Sem dados suficientes para este gráfico.</Text>
      </View>
    );
  }

  const yMin = chart.yAxis.min ?? Math.min(0, ...allYValues);
  const yMax = chart.yAxis.max ?? Math.max(...allYValues) * 1.1;
  const plotW = Math.max(width - CHART_PADDING.left - CHART_PADDING.right, 1);
  const plotH = height - CHART_PADDING.top - CHART_PADDING.bottom;

  const yToPx = (y: number) => {
    const ratio = (y - yMin) / (yMax - yMin || 1);
    return CHART_PADDING.top + plotH - ratio * plotH;
  };

  const isBar = chart.type === 'bar';

  return (
    <View style={styles.card}>
      <Text style={styles.title}>{chart.title}</Text>
      <Text style={styles.description}>{chart.description}</Text>

      <View onLayout={onLayout} style={{ height }}>
        {width > 0 && (
          <Svg width={width} height={height}>
            {/* Gridlines */}
            {[0, 0.25, 0.5, 0.75, 1].map((t) => {
              const y = CHART_PADDING.top + t * plotH;
              return (
                <Line
                  key={t}
                  x1={CHART_PADDING.left}
                  x2={width - CHART_PADDING.right}
                  y1={y}
                  y2={y}
                  stroke={colors.border}
                  strokeWidth={1}
                />
              );
            })}

            {isBar
              ? renderBars(chart, categories, plotW, plotH, yToPx)
              : renderLines(chart, categories, plotW, yToPx)}

            {/* Reference lines (e.g. decision threshold) */}
            {chart.referenceLines?.map((ref, i) => (
              <G key={i}>
                <Line
                  x1={CHART_PADDING.left}
                  x2={width - CHART_PADDING.right}
                  y1={yToPx(ref.value)}
                  y2={yToPx(ref.value)}
                  stroke={colors.muted}
                  strokeWidth={1}
                  strokeDasharray="4,4"
                />
              </G>
            ))}
          </Svg>
        )}
      </View>

      <ChartLegend chart={chart} />
    </View>
  );
}

function renderLines(
  chart: ChartDefinition,
  categories: string[],
  plotW: number,
  yToPx: (y: number) => number
) {
  const n = categories.length;
  const xStep = n > 1 ? plotW / (n - 1) : 0;
  const xToPx = (idx: number) => CHART_PADDING.left + idx * xStep;

  return chart.series.map((series, si) => {
    const color = colors.chartPalette[si % colors.chartPalette.length];
    let d = '';
    series.data.forEach((point, i) => {
      if (point.y === null || point.y === undefined) return;
      const idx = categories.indexOf(point.x);
      const x = xToPx(idx);
      const y = yToPx(point.y);
      d += d === '' ? `M ${x} ${y}` : ` L ${x} ${y}`;
    });
    const lastPoint = [...series.data].reverse().find((p) => p.y !== null && p.y !== undefined);
    return (
      <G key={series.name}>
        <Path d={d} stroke={color} strokeWidth={2.5} fill="none" />
        {lastPoint && (
          <Circle
            cx={xToPx(categories.indexOf(lastPoint.x))}
            cy={yToPx(lastPoint.y as number)}
            r={4}
            fill={color}
          />
        )}
      </G>
    );
  });
}

function renderBars(
  chart: ChartDefinition,
  categories: string[],
  plotW: number,
  plotH: number,
  yToPx: (y: number) => number
) {
  const groupCount = categories.length;
  const seriesCount = chart.series.length;
  const groupWidth = plotW / Math.max(groupCount, 1);
  const barWidth = Math.max((groupWidth * 0.7) / Math.max(seriesCount, 1), 2);

  const bars: React.ReactNode[] = [];
  categories.forEach((cat, gi) => {
    chart.series.forEach((series, si) => {
      const point = series.data.find((p) => p.x === cat);
      if (!point || point.y === null || point.y === undefined) return;
      const color = colors.chartPalette[si % colors.chartPalette.length];
      const barX =
        CHART_PADDING.left + gi * groupWidth + groupWidth * 0.15 + si * barWidth;
      const barY = yToPx(point.y);
      const barH = CHART_PADDING.top + plotH - barY;
      bars.push(
        <Rect
          key={`${cat}-${series.name}`}
          x={barX}
          y={barY}
          width={barWidth}
          height={Math.max(barH, 0)}
          fill={color}
          rx={2}
        />
      );
    });
  });
  return bars;
}

function ChartLegend({ chart }: { chart: ChartDefinition }) {
  if (chart.series.length <= 1) return null;
  return (
    <View style={styles.legend}>
      {chart.series.map((s, i) => (
        <View key={s.name} style={styles.legendItem}>
          <View
            style={[styles.legendDot, { backgroundColor: colors.chartPalette[i % colors.chartPalette.length] }]}
          />
          <Text style={styles.legendText}>{s.name}</Text>
        </View>
      ))}
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
    marginBottom: spacing.md,
  },
  title: { ...typography.h3, color: colors.textPrimary },
  description: { ...typography.caption, color: colors.textSecondary, marginBottom: spacing.sm },
  empty: { ...typography.body, color: colors.muted, textAlign: 'center', marginTop: spacing.lg },
  legend: { flexDirection: 'row', flexWrap: 'wrap', marginTop: spacing.sm, gap: spacing.md },
  legendItem: { flexDirection: 'row', alignItems: 'center' },
  legendDot: { width: 8, height: 8, borderRadius: 4, marginRight: 4 },
  legendText: { ...typography.caption, color: colors.textSecondary },
});
