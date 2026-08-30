// Minimal, professional palette — decision-support dashboard, not a
// data-viz playground. Keep the number of colors small (Nielsen: minimalist
// design) and reserve saturated colors for risk signaling only.
export const colors = {
  background: '#F7F8FA',
  surface: '#FFFFFF',
  border: '#E4E7EC',
  textPrimary: '#1A1D23',
  textSecondary: '#5B6472',
  muted: '#9AA2AE',

  primary: '#2A6F97',
  primaryDark: '#1C4E6B',

  success: '#2A9D8F',
  warning: '#E9A23B',
  danger: '#E63946',

  chartPalette: ['#2A6F97', '#E63946', '#2A9D8F', '#E9A23B', '#264653'],
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
};

export const radii = {
  sm: 8,
  md: 12,
  lg: 16,
  pill: 999,
};

export const typography = {
  h1: { fontSize: 26, fontWeight: '700' as const },
  h2: { fontSize: 20, fontWeight: '700' as const },
  h3: { fontSize: 16, fontWeight: '600' as const },
  body: { fontSize: 14, fontWeight: '400' as const },
  caption: { fontSize: 12, fontWeight: '400' as const },
};
