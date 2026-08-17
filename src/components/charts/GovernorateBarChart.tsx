import { useMemo } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Card } from '../ui/Card';
import { useFilters } from '../../context/FiltersContext';
import { CHART_AXIS_TICK, CHART_TOOLTIP_STYLE } from '../../lib/palette';

function GovernorateTick({
  x = 0,
  y = 0,
  payload = { value: '' },
}: {
  x?: number;
  y?: number;
  payload?: { value: string };
}) {
  const words = payload.value.split(' ');
  return (
    <g transform={`translate(${x},${y})`}>
      {words.map((word, i) => (
        <text
          key={word}
          textAnchor="middle"
          dy={14 + i * 13}
          fill={CHART_AXIS_TICK.fill}
          fontSize={CHART_AXIS_TICK.fontSize}
        >
          {word}
        </text>
      ))}
    </g>
  );
}

export function GovernorateBarChart() {
  const { filteredEvents, filters, setGovernorate } = useFilters();

  const data = useMemo(() => {
    const counts = new Map<string, number>();
    for (const e of filteredEvents) {
      if (!e.governorate) continue;
      counts.set(e.governorate.ar, (counts.get(e.governorate.ar) ?? 0) + 1);
    }
    return [...counts.entries()]
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 12);
  }, [filteredEvents]);

  return (
    <Card title="عدد الحوادث حسب الولاية" subtitle="أعلى 12 ولاية · اضغط عمودًا للتصفية">
      <ResponsiveContainer width="100%" height="100%" minHeight={300}>
        <BarChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: -20 }}>
          <defs>
            <linearGradient id="govBarFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#22d3ee" />
              <stop offset="100%" stopColor="#6366f1" />
            </linearGradient>
            <linearGradient id="govBarFillActive" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#67e8f9" />
              <stop offset="100%" stopColor="#22d3ee" />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
          <XAxis
            dataKey="name"
            tick={<GovernorateTick />}
            interval={0}
            height={40}
            axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
            tickLine={false}
          />
          <YAxis tick={CHART_AXIS_TICK} allowDecimals={false} axisLine={false} tickLine={false} />
          <Tooltip cursor={{ fill: 'rgba(255,255,255,0.04)' }} contentStyle={CHART_TOOLTIP_STYLE} labelStyle={{ color: '#e7ecf5' }} />
          <Bar
            dataKey="count"
            radius={[8, 8, 0, 0]}
            cursor="pointer"
            maxBarSize={40}
            onClick={(entry) => {
              const name = (entry as unknown as { name: string }).name;
              setGovernorate(filters.governorates.has(name) ? null : name);
            }}
          >
            {data.map((d) => (
              <Cell
                key={d.name}
                fill={filters.governorates.has(d.name) ? 'url(#govBarFillActive)' : 'url(#govBarFill)'}
                opacity={filters.governorates.size === 0 || filters.governorates.has(d.name) ? 1 : 0.3}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}
