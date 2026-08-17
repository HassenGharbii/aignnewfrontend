import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { useFilters } from '../context/FiltersContext';
import { useCountUp } from '../lib/useCountUp';
import { formatNumber } from '../lib/format';
import { severityTone } from '../lib/severity';

interface Kpi {
  label: string;
  value: number;
  tone: 'accent' | 'danger' | 'warning' | 'success' | 'neutral';
  icon: string;
}

const TONE_TEXT: Record<Kpi['tone'], string> = {
  accent: 'text-cyan-300',
  danger: 'text-rose-400',
  warning: 'text-amber-400',
  success: 'text-emerald-400',
  neutral: 'text-slate-300',
};

const TONE_ICON_BG: Record<Kpi['tone'], string> = {
  accent: 'bg-cyan-500/15 ring-cyan-500/25',
  danger: 'bg-rose-500/15 ring-rose-500/25',
  warning: 'bg-amber-500/15 ring-amber-500/25',
  success: 'bg-emerald-500/15 ring-emerald-500/25',
  neutral: 'bg-slate-500/15 ring-slate-500/25',
};

const TONE_GLOW: Record<Kpi['tone'], string> = {
  accent: 'from-cyan-500/15',
  danger: 'from-rose-500/15',
  warning: 'from-amber-500/15',
  success: 'from-emerald-500/15',
  neutral: 'from-slate-500/15',
};

function KpiCard({ kpi, index }: { kpi: Kpi; index: number }) {
  const animated = useCountUp(kpi.value);
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04, duration: 0.3 }}
      whileHover={{ y: -2 }}
      className="relative overflow-hidden rounded-2xl border border-white/8 bg-white/[0.03] p-4 shadow-lg shadow-black/20 transition-colors hover:border-white/15"
    >
      <div className={`absolute -top-8 -left-8 h-24 w-24 rounded-full bg-gradient-to-br ${TONE_GLOW[kpi.tone]} to-transparent blur-xl`} />
      <div className="relative flex items-center gap-3">
        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-lg ring-1 ${TONE_ICON_BG[kpi.tone]}`}>
          {kpi.icon}
        </div>
        <div className="min-w-0">
          <div className="truncate text-[11px] text-slate-500">{kpi.label}</div>
          <div className={`text-2xl font-extrabold tabular-nums ${TONE_TEXT[kpi.tone]}`}>
            {formatNumber(animated)}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export function KpiRow() {
  const { filteredEvents } = useFilters();

  const kpis = useMemo<Kpi[]>(() => {
    let deaths = 0;
    let injuries = 0;
    let open = 0;
    let closed = 0;
    let high = 0;

    for (const e of filteredEvents) {
      deaths += e.parsed.facts.عدد_الوفيات ?? 0;
      injuries += e.parsed.facts.عدد_الإصابات ?? 0;
      if (e.event_status.includes('مفتوح')) open += 1;
      else if (e.event_status.includes('مغلق')) closed += 1;
      if (severityTone(e.severity) === 'danger') high += 1;
    }

    return [
      { label: 'إجمالي الحوادث', value: filteredEvents.length, tone: 'accent', icon: '🚦' },
      { label: 'عدد القتلى', value: deaths, tone: 'danger', icon: '⚠️' },
      { label: 'عدد الجرحى', value: injuries, tone: 'warning', icon: '🩹' },
      { label: 'حوادث خطورة مرتفعة', value: high, tone: 'danger', icon: '🔥' },
      { label: 'قيد المعالجة', value: open, tone: 'warning', icon: '📂' },
      { label: 'مغلقة', value: closed, tone: 'success', icon: '✅' },
    ];
  }, [filteredEvents]);

  return (
    <div className="grid grid-cols-2 items-start gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {kpis.map((kpi, i) => (
        <KpiCard key={kpi.label} kpi={kpi} index={i} />
      ))}
    </div>
  );
}
