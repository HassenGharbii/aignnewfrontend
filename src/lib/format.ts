const numberFormatter = new Intl.NumberFormat('ar-TN');

export function formatNumber(n: number): string {
  return numberFormatter.format(n);
}

export function formatDate(date: Date | string | null): string {
  if (!date) return '—';
  const d = typeof date === 'string' ? new Date(date) : date;
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('ar-TN', { year: 'numeric', month: '2-digit', day: '2-digit' });
}

export function formatDateTime(date: Date | string | null): string {
  if (!date) return '—';
  const d = typeof date === 'string' ? new Date(date) : date;
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString('ar-TN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max).trimEnd()}…`;
}

const relativeTimeFormatter = new Intl.RelativeTimeFormat('ar', { numeric: 'auto' });

export function formatRelativeTime(date: Date | string | null): string {
  if (!date) return '—';
  const d = typeof date === 'string' ? new Date(date) : date;
  if (Number.isNaN(d.getTime())) return '—';

  const diffSeconds = Math.round((d.getTime() - Date.now()) / 1000);
  const abs = Math.abs(diffSeconds);

  if (abs < 60) return relativeTimeFormatter.format(diffSeconds, 'second');
  if (abs < 3600) return relativeTimeFormatter.format(Math.round(diffSeconds / 60), 'minute');
  if (abs < 86400) return relativeTimeFormatter.format(Math.round(diffSeconds / 3600), 'hour');
  if (abs < 2592000) return relativeTimeFormatter.format(Math.round(diffSeconds / 86400), 'day');
  return relativeTimeFormatter.format(Math.round(diffSeconds / 2592000), 'month');
}
