// Minimal, professional palette — decision-support dashboard, not a
// data-viz playground. Keep the number of colors small (Nielsen: minimalist
// design) and reserve saturated colors for risk signaling only.
export const colors = {
  background: '#F3F7F8',
  surface: '#FFFFFF',
  surfaceSoft: '#EAF4F5',
  border: '#DDE8EA',
  textPrimary: '#132C33',
  textSecondary: '#526A70',
  muted: '#82969B',

  primary: '#087F8C',
  primaryDark: '#075E68',
  primaryLight: '#DDF2F3',

  success: '#258A6D',
  warning: '#D99022',
  danger: '#D84A55',

  chartPalette: ['#2A6F97', '#E63946', '#2A9D8F', '#E9A23B', '#264653'],
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 44,
};

export const radii = {
  sm: 10,
  md: 16,
  lg: 22,
  pill: 999,
};

export const typography = {
  h1: { fontSize: 30, lineHeight: 36, fontWeight: '800' as const, letterSpacing: -0.5 },
  h2: { fontSize: 20, lineHeight: 26, fontWeight: '700' as const },
  h3: { fontSize: 16, lineHeight: 22, fontWeight: '700' as const },
  body: { fontSize: 14, lineHeight: 21, fontWeight: '400' as const },
  caption: { fontSize: 12, lineHeight: 17, fontWeight: '400' as const },
};

export const cardShadow = {
  shadowColor: '#173B42',
  shadowOffset: { width: 0, height: 4 },
  shadowOpacity: 0.08,
  shadowRadius: 12,
  elevation: 3,
};
