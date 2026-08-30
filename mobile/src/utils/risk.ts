import { RiskLevel } from '../types';
import { colors } from '../theme/colors';

export function riskLabel(level: RiskLevel | undefined): string {
  switch (level) {
    case 'high':
      return 'Risco alto';
    case 'moderate':
      return 'Risco moderado';
    case 'low':
      return 'Risco baixo';
    default:
      return 'Sem dados';
  }
}

export function riskColor(level: RiskLevel | undefined): string {
  switch (level) {
    case 'high':
      return colors.danger;
    case 'moderate':
      return colors.warning;
    case 'low':
      return colors.success;
    default:
      return colors.muted;
  }
}

export function riskDescription(level: RiskLevel | undefined): string {
  switch (level) {
    case 'high':
      return 'O modelo indica alta chance de surto. Considere reforçar vigilância e resposta.';
    case 'moderate':
      return 'Sinal de atenção. Acompanhe a tendência nas próximas semanas.';
    case 'low':
      return 'Sem indícios de surto neste horizonte.';
    default:
      return 'Ainda não há previsão disponível para este horizonte.';
  }
}

export function formatPercent(value: number | undefined): string {
  if (value === undefined || value === null || Number.isNaN(value)) return '—';
  return `${Math.round(value * 100)}%`;
}

export function formatDate(iso: string | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' });
}
