import { useMemo, useState } from 'react';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { useFilters } from '../context/FiltersContext';
import { severityTone } from '../lib/severity';
import { formatRelativeTime, truncate } from '../lib/format';
import type { ParsedEvent } from '../lib/parseEvent';
import { EventDetailModal } from './table/EventDetailModal';

export function RecentActivityTicker() {
  const { filteredEvents } = useFilters();
  const [selected, setSelected] = useState<ParsedEvent | null>(null);

  const recent = useMemo(
    () =>
      [...filteredEvents]
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 10),
    [filteredEvents],
  );

  if (recent.length === 0) return null;

  return (
    <Card title="آخر البلاغات الواردة" subtitle="مرتبة حسب وقت التسجيل في النظام">
      <div className="flex items-start gap-3 overflow-x-auto pb-1">
        {recent.map((e) => (
          <button
            key={e.id}
            onClick={() => setSelected(e)}
            className="flex w-64 shrink-0 flex-col gap-1.5 rounded-xl border border-white/8 bg-white/[0.02] p-3 text-right transition hover:border-cyan-500/40 hover:bg-white/5"
          >
            <div className="flex items-center justify-between">
              <Badge label={e.severity} tone={severityTone(e.severity)} />
              <span className="text-[11px] text-slate-500">{formatRelativeTime(e.created_at)}</span>
            </div>
            <div className="text-sm font-medium text-slate-200">
              {truncate(e.event_title || e.event_summary, 56)}
            </div>
            <div className="text-[11px] text-slate-500">{e.governorate?.ar ?? e.region}</div>
          </button>
        ))}
      </div>

      <EventDetailModal event={selected} onClose={() => setSelected(null)} />
    </Card>
  );
}
