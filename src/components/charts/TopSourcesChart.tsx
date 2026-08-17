import { useMemo } from 'react';
import { Card } from '../ui/Card';
import { useFilters } from '../../context/FiltersContext';
import { truncate, formatNumber } from '../../lib/format';
import { countGrouped } from '../../lib/arabicText';

export function TopSourcesChart() {
  const { filteredEvents, filters, setSearch } = useFilters();

  const rows = useMemo(() => {
    const names = filteredEvents.map((e) => e.parsed.reportedBy).filter((n): n is string => Boolean(n));
    return countGrouped(names).slice(0, 10);
  }, [filteredEvents]);

  const max = Math.max(1, ...rows.map(([, c]) => c));

  if (rows.length === 0) {
    return (
      <Card title="أكثر مراكز الإبلاغ نشاطًا">
        <p className="py-6 text-center text-xs text-slate-500">لا توجد بيانات كافية عن مصدر البلاغ</p>
      </Card>
    );
  }

  return (
    <Card title="أكثر مراكز الإبلاغ نشاطًا" subtitle="اضغط عنصرًا للبحث عنه في السجل">
      <div className="flex flex-col gap-2">
        {rows.map(([name, count], i) => {
          const isActive = filters.search === name;
          return (
            <button
              key={name}
              onClick={() => setSearch(isActive ? '' : name)}
              className={`flex items-center gap-3 rounded-lg px-1.5 py-1 text-right transition hover:bg-white/5 ${
                isActive ? 'bg-white/8 ring-1 ring-cyan-500/30' : ''
              }`}
            >
              <span className="w-4 shrink-0 text-[11px] font-bold text-slate-500">{i + 1}</span>
              <span className="flex-1 truncate text-xs text-slate-300">{truncate(name, 38)}</span>
              <div className="h-1.5 w-16 shrink-0 overflow-hidden rounded-full bg-white/5">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-indigo-400"
                  style={{ width: `${(count / max) * 100}%` }}
                />
              </div>
              <span className="w-6 shrink-0 text-right text-xs font-semibold text-slate-400">
                {formatNumber(count)}
              </span>
            </button>
          );
        })}
      </div>
    </Card>
  );
}
