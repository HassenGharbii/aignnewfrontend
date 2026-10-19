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
  const { filteredEvents } = useFilters();

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
    <Card title="عدد الحوادث حسب الولاية" subtitle="أعلى 12 ولاية">
      <ResponsiveContainer width="100%" height="100%" minHeight={300}>
        <BarChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: -20 }}>
          <defs>
            <linearGradient id="govBarFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#22d3ee" />
              <stop offset="100%" stopColor="#6366f1" />
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
          <Bar dataKey="count" radius={[8, 8, 0, 0]} maxBarSize={40}>
            {data.map((d) => (
              <Cell key={d.name} fill="url(#govBarFill)" />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}
