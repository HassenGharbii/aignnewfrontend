import { useMemo } from 'react';
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Card } from '../ui/Card';
import { useFilters } from '../../context/FiltersContext';
import { CHART_AXIS_TICK, CHART_TOOLTIP_STYLE } from '../../lib/palette';

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

export function TimingChart() {
  const { filteredEvents } = useFilters();

  const withTime = useMemo(() => filteredEvents.filter((e) => e.eventDate), [filteredEvents]);

  const hourData = useMemo(() => {
    const buckets = new Array(24).fill(0);
    for (const e of withTime) buckets[e.eventDate!.getHours()] += 1;
    return buckets.map((count, hour) => ({ hour: `${hour}`, count }));
  }, [withTime]);

  const dayData = useMemo(() => {
    const buckets = new Map<number, number>();
    for (const e of withTime) buckets.set(e.eventDate!.getDay(), (buckets.get(e.eventDate!.getDay()) ?? 0) + 1);
    return DAY_ORDER.map((d) => ({ day: DAY_LABELS[d], count: buckets.get(d) ?? 0 }));
  }, [withTime]);

  const peakHour = useMemo(() => {
    const max = Math.max(...hourData.map((h) => h.count));
    const hit = hourData.find((h) => h.count === max);
    return hit && max > 0 ? `${hit.hour}:00` : '—';
  }, [hourData]);

  return (
    <Card title="التوزيع الزمني للحوادث" subtitle={`ساعة الذروة: ${peakHour} · بيانات ${withTime.length} حادث`}>
      <div className="grid flex-1 gap-4 sm:grid-cols-2">
        <div className="flex flex-col">
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">حسب ساعة اليوم</div>
          <ResponsiveContainer width="100%" height="100%" minHeight={200}>
            <BarChart data={hourData} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
              <XAxis dataKey="hour" tick={CHART_AXIS_TICK} interval={2} axisLine={false} tickLine={false} />
              <YAxis tick={CHART_AXIS_TICK} allowDecimals={false} axisLine={false} tickLine={false} />
              <Tooltip
                cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                contentStyle={CHART_TOOLTIP_STYLE}
                labelFormatter={(h) => `الساعة ${h}:00`}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={16} fill="#fbbf24" opacity={0.85} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="flex flex-col">
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">حسب أيام الأسبوع</div>
          <ResponsiveContainer width="100%" height="100%" minHeight={200}>
            <BarChart data={dayData} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
              <XAxis dataKey="day" tick={{ ...CHART_AXIS_TICK, fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={CHART_AXIS_TICK} allowDecimals={false} axisLine={false} tickLine={false} />
              <Tooltip cursor={{ fill: 'rgba(255,255,255,0.04)' }} contentStyle={CHART_TOOLTIP_STYLE} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={28} fill="#a78bfa" opacity={0.85} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </Card>
  );
}
