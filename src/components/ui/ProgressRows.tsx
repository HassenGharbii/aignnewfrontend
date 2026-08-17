import { motion } from 'framer-motion';
import { formatNumber } from '../../lib/format';

export function ProgressRows({
  rows,
  active,
  onToggle,
  colorFor,
  labelFor,
}: {
  rows: [string, number][];
  active?: Set<string>;
  onToggle?: (v: string) => void;
  colorFor: (name: string, index: number) => string;
  labelFor?: (name: string) => string;
}) {
  const max = Math.max(1, ...rows.map(([, c]) => c));

  return (
    <div className="flex flex-col gap-2.5">
      {rows.map(([name, count], i) => {
        const isActive = active?.has(name) ?? false;
        const isDimmed = (active?.size ?? 0) > 0 && !isActive;
        const color = colorFor(name, i);
        const Wrapper = onToggle ? 'button' : 'div';
        return (
          <Wrapper
            key={name}
            onClick={onToggle ? () => onToggle(name) : undefined}
            className={`group text-right transition ${isDimmed ? 'opacity-40' : ''}`}
          >
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className="font-medium text-slate-300 group-hover:text-white">
                {labelFor ? labelFor(name) : name}
              </span>
              <span className="font-bold text-slate-200">{formatNumber(count)}</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-white/5">
              <motion.div
                className="h-full rounded-full"
                style={{ background: color, boxShadow: isActive ? `0 0 12px ${color}` : undefined }}
                initial={{ width: 0 }}
                animate={{ width: `${(count / max) * 100}%` }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
              />
            </div>
          </Wrapper>
        );
      })}
    </div>
  );
}
