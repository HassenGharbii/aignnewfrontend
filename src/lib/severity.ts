import { fuzzyIncludes } from './arabicText';

export type SeverityTone = 'danger' | 'warning' | 'success' | 'neutral';

export function severityTone(severity: string): SeverityTone {
  if (
    fuzzyIncludes(severity, 'حرج') ||
    fuzzyIncludes(severity, 'مرتفع') ||
    severity.toLowerCase() === 'high' ||
    severity.toLowerCase() === 'critical'
  ) {
    return 'danger';
  }
  if (fuzzyIncludes(severity, 'متوسط') || severity.toLowerCase() === 'medium') return 'warning';
  if (fuzzyIncludes(severity, 'منخفض') || severity.toLowerCase() === 'low') return 'success';
  return 'neutral';
}

export function statusTone(status: string): SeverityTone {
  if (fuzzyIncludes(status, 'مفتوح')) return 'warning';
  if (fuzzyIncludes(status, 'مغلق')) return 'success';
  return 'neutral';
}

export function verificationTone(status: string): SeverityTone {
  if (fuzzyIncludes(status, 'مؤكد')) return 'success';
  if (fuzzyIncludes(status, 'انتظار')) return 'warning';
  return 'neutral';
}

export const TONE_CLASSES: Record<SeverityTone, string> = {
  danger: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  warning: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  success: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  neutral: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
};

export const TONE_DOT: Record<SeverityTone, string> = {
  danger: 'bg-rose-400',
  warning: 'bg-amber-400',
  success: 'bg-emerald-400',
  neutral: 'bg-slate-400',
};

export const TONE_HEX: Record<SeverityTone, string> = {
  danger: '#fb7185',
  warning: '#fbbf24',
  success: '#34d399',
  neutral: '#94a3b8',
};
