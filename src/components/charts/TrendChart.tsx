import { useMemo } from 'react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Card } from '../ui/Card';
import { useFilters } from '../../context/FiltersContext';
import { CHART_AXIS_TICK, CHART_TOOLTIP_STYLE } from '../../lib/palette';

const VISIBLE_MONTHS = 12;

export function TrendChart() {
  const { filteredEvents } = useFilters();

  const { data, hiddenOlderCount } = useMemo(() => {
    const buckets = new Map<string, number>();
    for (const e of filteredEvents) {
      if (!e.eventDate) continue;
      const key = `${e.eventDate.getFullYear()}-${String(e.eventDate.getMonth() + 1).padStart(2, '0')}`;
      buckets.set(key, (buckets.get(key) ?? 0) + 1);
    }
    const sorted = [...buckets.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([month, count]) => ({ month, count }));

    // A handful of records carry clearly stray dates (years off from the rest
    // of the dataset); windowing to the most recent months keeps the chart
    // readable instead of one outlier stretching the whole axis flat.
    const visible = sorted.slice(-VISIBLE_MONTHS);
    const hiddenOlderCount = sorted.slice(0, -VISIBLE_MONTHS).reduce((sum, b) => sum + b.count, 0);
    return { data: visible, hiddenOlderCount };
  }, [filteredEvents]);

  return (
    <Card
      title="تطور عدد الحوادث عبر الزمن"
      subtitle={
        hiddenOlderCount > 0
          ? `حسب الشهر · آخر ${VISIBLE_MONTHS} شهرًا (${hiddenOlderCount} حادث أقدم غير معروض)`
          : 'حسب الشهر'
      }
    >
      <ResponsiveContainer width="100%" height="100%" minHeight={240}>
        <AreaChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.55} />
              <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="trendStroke" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#22d3ee" />
              <stop offset="100%" stopColor="#818cf8" />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
          <XAxis dataKey="month" tick={CHART_AXIS_TICK} axisLine={{ stroke: 'rgba(255,255,255,0.08)' }} tickLine={false} />
          <YAxis tick={CHART_AXIS_TICK} allowDecimals={false} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={CHART_TOOLTIP_STYLE} labelStyle={{ color: '#e7ecf5' }} cursor={{ stroke: 'rgba(255,255,255,0.15)' }} />
          <Area
            type="monotone"
            dataKey="count"
            stroke="url(#trendStroke)"
            strokeWidth={2.5}
            fill="url(#trendFill)"
            dot={{ r: 3, strokeWidth: 0, fill: '#22d3ee' }}
            activeDot={{ r: 5, strokeWidth: 2, stroke: '#0a0f1a' }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </Card>
  );
}
