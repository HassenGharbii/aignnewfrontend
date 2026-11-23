import { useMemo } from 'react';
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import { Card } from '../ui/Card';
import { useFilters } from '../../context/FiltersContext';
import { truncate, formatNumber } from '../../lib/format';
import { PALETTE, CHART_TOOLTIP_STYLE } from '../../lib/palette';
import { countGrouped } from '../../lib/arabicText';
import { UNKNOWN_CAUSE } from '../../lib/causes';

export function CauseDonut() {
  const { filteredEvents, filters, toggleCause } = useFilters();

  const data = useMemo(() => {
    const total = filteredEvents.length || 1;
    // One accident can have several causes: each distinct cause counts once per
    // event, and percentages are of events, so they can add up past 100%.
    const grouped = countGrouped(
      filteredEvents.flatMap((e) => (e.causes.length > 0 ? [...new Set(e.causes)] : [UNKNOWN_CAUSE])),
    );
    const top = grouped.slice(0, PALETTE.length - 1);
    const otherCount = grouped.slice(PALETTE.length - 1).reduce((sum, [, count]) => sum + count, 0);
    const rows = otherCount > 0 ? [...top, ['أخرى', otherCount] as [string, number]] : top;
    return rows.map(([name, value]) => ({
      name,
      value,
      pct: Math.round((value / total) * 100),
    }));
  }, [filteredEvents]);

  return (
    <Card title="أسباب الحوادث" subtitle="قد يكون للحادث أكثر من سبب · اضغط عنصرًا للتصفية">
      <div className="flex flex-1 flex-col items-center justify-center gap-4 sm:flex-row">
        <ResponsiveContainer width="100%" height={220} className="max-w-[220px]">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius={58} outerRadius={95} paddingAngle={3} strokeWidth={0}>
              {data.map((d, i) => (
                <Cell
                  key={d.name}
                  fill={PALETTE[i % PALETTE.length]}
                  opacity={filters.causes.size === 0 || filters.causes.has(d.name) ? 1 : 0.25}
                />
              ))}
            </Pie>
            <Tooltip
              contentStyle={CHART_TOOLTIP_STYLE}
              formatter={(value, _name, entry) => [
                `${formatNumber(Number(value))} (${(entry.payload as { pct: number }).pct}%)`,
                (entry.payload as { name: string }).name,
              ]}
            />
          </PieChart>
        </ResponsiveContainer>

        <div className="flex w-full flex-1 flex-col gap-1.5">
          {data.map((d, i) => {
            const isOther = d.name === 'أخرى' || d.name === UNKNOWN_CAUSE;
            const isActive = !isOther && filters.causes.has(d.name);
            const isDimmed = !isOther && filters.causes.size > 0 && !isActive;
            return (
              <button
                key={d.name}
                onClick={isOther ? undefined : () => toggleCause(d.name)}
                disabled={isOther}
                className={`flex items-center gap-2 rounded-lg px-2 py-1.5 text-right transition ${
                  isOther ? 'cursor-default' : 'hover:bg-white/5'
                } ${isActive ? 'bg-white/8 ring-1 ring-white/15' : ''} ${isDimmed ? 'opacity-40' : ''}`}
              >
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ background: PALETTE[i % PALETTE.length] }}
                />
                <span className="flex-1 truncate text-xs text-slate-300">{truncate(d.name, 42)}</span>
                <span className="shrink-0 text-xs font-semibold text-slate-400">{d.pct}%</span>
              </button>
            );
          })}
        </div>
      </div>
    </Card>
  );
}
