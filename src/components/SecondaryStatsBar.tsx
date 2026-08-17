import { useMemo } from 'react';
import { useFilters } from '../context/FiltersContext';
import { formatNumber } from '../lib/format';

function StatChip({
  icon,
  label,
  value,
  tone = 'neutral',
}: {
  icon: string;
  label: string;
  value: string;
  tone?: 'neutral' | 'alert';
}) {
  return (
    <div
      className={`flex items-center gap-2 rounded-full border px-3.5 py-2 text-xs ${
        tone === 'alert'
          ? 'border-rose-500/30 bg-rose-500/10 text-rose-300'
          : 'border-white/8 bg-white/[0.02] text-slate-300'
      }`}
    >
      <span>{icon}</span>
      <span className="font-bold text-slate-100">{value}</span>
      <span className={tone === 'alert' ? 'text-rose-300/80' : 'text-slate-500'}>{label}</span>
    </div>
  );
}

export function SecondaryStatsBar() {
  const { filteredEvents } = useFilters();

  const stats = useMemo(() => {
    let vehicles = 0;
    let pendingVerification = 0;
    let hazmat = 0;
    let confidenceSum = 0;
    let confidenceCount = 0;

    for (const e of filteredEvents) {
      vehicles += e.parsed.facts.عدد_المركبات ?? 0;
      if (e.parsed.verificationStatus?.includes('انتظار')) pendingVerification += 1;
      if (e.parsed.facts.مواد_خطرة_متسربة) hazmat += 1;
      if (e.parsed.confidence !== null) {
        confidenceSum += e.parsed.confidence;
        confidenceCount += 1;
      }
    }

    return {
      vehicles,
      pendingVerification,
      hazmat,
      avgConfidence: confidenceCount > 0 ? Math.round((confidenceSum / confidenceCount) * 100) : null,
    };
  }, [filteredEvents]);

  return (
    <div className="flex flex-wrap items-center gap-2">
      <StatChip icon="🚗" label="مركبة متورطة" value={formatNumber(stats.vehicles)} />
      <StatChip icon="🕐" label="بلاغ قيد التحقق" value={formatNumber(stats.pendingVerification)} />
      {stats.avgConfidence !== null && (
        <StatChip icon="🎯" label="دقة التصنيف الآلي" value={`${stats.avgConfidence}%`} />
      )}
      {stats.hazmat > 0 && (
        <StatChip icon="☣️" label="حادث بمواد خطرة متسربة" value={formatNumber(stats.hazmat)} tone="alert" />
      )}
    </div>
  );
}
