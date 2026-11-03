export const colors = {
  background: '#FFFFFF',
  surface: '#FFFFFF',
  surfaceSoft: '#F5F5F7',
  border: '#E8E8ED',
  textPrimary: '#111113',
  textSecondary: '#66666E',
  muted: '#767680',
  primary: '#111113',
  primaryDark: '#111113',
  primaryLight: '#94E1F5',
  cyan: '#94E1F5',
  pink: '#FAD2D5',
  lavender: '#E4DFF7',
  success: '#237458',
  warning: '#94621B',
  danger: '#B83449',
  chartPalette: ['#1687A7', '#D36C84', '#7663AD', '#237458', '#94621B'],
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

export const radii = {
  sm: 14,
  md: 22,
  lg: 30,
  pill: 999,
};

export const typography = {
  h1: { fontSize: 36, lineHeight: 41, fontWeight: '700' as const, letterSpacing: -1.5 },
  h2: { fontSize: 23, lineHeight: 29, fontWeight: '600' as const, letterSpacing: -0.6 },
  h3: { fontSize: 18, lineHeight: 24, fontWeight: '600' as const, letterSpacing: -0.3 },
  body: { fontSize: 15, lineHeight: 23, fontWeight: '400' as const },
  caption: { fontSize: 12, lineHeight: 18, fontWeight: '400' as const },
};

export const cardShadow = {
  shadowColor: '#111113',
  shadowOffset: { width: 0, height: 6 },
  shadowOpacity: 0.035,
  shadowRadius: 18,
  elevation: 1,
};
