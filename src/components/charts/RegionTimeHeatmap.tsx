import { useMemo, useState } from 'react';
import { Card } from '../ui/Card';
import { useFilters } from '../../context/FiltersContext';

type Mode = 'hour' | 'day';

const DAY_ORDER = [1, 2, 3, 4, 5, 6, 0];
const DAY_LABELS: Record<number, string> = {
  1: 'الاثنين',
  2: 'الثلاثاء',
  3: 'الأربعاء',
  4: 'الخميس',
  5: 'الجمعة',
  6: 'السبت',
  0: 'الأحد',
};

const TOP_N_REGIONS = 10;

/** Heatmap: top governorates (rows) x hour-of-day or day-of-week (columns),
 * cell intensity = incident count — surfaces "which region peaks when"
 * patterns that the separate GovernorateBarChart/TimingChart can't show on
 * their own since each only aggregates one dimension at a time. */
export function RegionTimeHeatmap() {
  const { filteredEvents } = useFilters();
  const [mode, setMode] = useState<Mode>('hour');

  const withTimeAndRegion = useMemo(
    () => filteredEvents.filter((e) => e.eventDate && e.governorate),
    [filteredEvents],
  );

  const topRegions = useMemo(() => {
    const counts = new Map<string, number>();
    for (const e of withTimeAndRegion) {
      counts.set(e.governorate!.ar, (counts.get(e.governorate!.ar) ?? 0) + 1);
    }
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, TOP_N_REGIONS)
      .map(([name]) => name);
  }, [withTimeAndRegion]);

  const columns = mode === 'hour' ? Array.from({ length: 24 }, (_, h) => h) : DAY_ORDER;

  const { matrix, max, peak } = useMemo(() => {
    const m = new Map<string, Map<number, number>>();
    for (const region of topRegions) m.set(region, new Map());
    let maxVal = 0;
    let peakCell: { region: string; col: number } | null = null;
    for (const e of withTimeAndRegion) {
      const region = e.governorate!.ar;
      const row = m.get(region);
      if (!row) continue; // outside top N
      const col = mode === 'hour' ? e.eventDate!.getHours() : e.eventDate!.getDay();
      const next = (row.get(col) ?? 0) + 1;
      row.set(col, next);
      if (next > maxVal) {
        maxVal = next;
        peakCell = { region, col };
      }
    }
    return { matrix: m, max: maxVal, peak: peakCell };
  }, [withTimeAndRegion, topRegions, mode]);

  function cellColor(count: number): string {
    if (count === 0 || max === 0) return 'rgba(255,255,255,0.03)';
    const intensity = count / max;
    return `rgba(34, 211, 238, ${0.12 + intensity * 0.78})`;
  }

  const peakLabel =
    peak && mode === 'hour'
      ? `${peak.region} · الساعة ${peak.col}:00`
      : peak
        ? `${peak.region} · ${DAY_LABELS[peak.col]}`
        : '—';

  return (
    <Card
      title="أعلى الولايات نشاطًا حسب الوقت"
      subtitle={`أعلى ${TOP_N_REGIONS} ولايات · الذروة: ${peakLabel}`}
      action={
        <div className="flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.02] p-0.5 text-xs">
          <button
            onClick={() => setMode('hour')}
            className={`rounded-full px-2.5 py-1 transition ${
              mode === 'hour' ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            حسب الساعة
          </button>
          <button
            onClick={() => setMode('day')}
            className={`rounded-full px-2.5 py-1 transition ${
              mode === 'day' ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            حسب اليوم
          </button>
        </div>
      }
    >
      {topRegions.length === 0 ? (
        <p className="py-10 text-center text-sm text-slate-500">لا توجد بيانات موقع/توقيت كافية</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-separate" style={{ borderSpacing: 3 }}>
            <thead>
              <tr>
                <th className="sticky right-0 z-10 bg-[#0b1120] px-2 text-right text-[10px] font-semibold text-slate-500">
                  الولاية
                </th>
                {columns.map((c) => (
                  <th key={c} className="min-w-[24px] px-0.5 text-center text-[9px] font-medium text-slate-500">
                    {mode === 'hour' ? (c % 3 === 0 ? c : '') : DAY_LABELS[c].slice(0, 3)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {topRegions.map((region) => (
                <tr key={region}>
                  <td className="sticky right-0 z-10 max-w-[110px] truncate bg-[#0b1120] px-2 py-1 text-right text-[11px] font-medium text-slate-300">
                    {region}
                  </td>
                  {columns.map((c) => {
                    const count = matrix.get(region)?.get(c) ?? 0;
                    return (
                      <td key={c} className="p-0">
                        <div
                          title={`${region} · ${mode === 'hour' ? `الساعة ${c}:00` : DAY_LABELS[c]} · ${count} حادث`}
                          className="h-5 w-full rounded-[3px]"
                          style={{ background: cellColor(count) }}
                        />
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
