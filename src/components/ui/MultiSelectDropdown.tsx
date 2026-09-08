import { useEffect, useRef, useState } from 'react';

/** A checkbox-list dropdown for filters with too many distinct values to show
 * as a wall of pills (e.g. المعتمدية/العمادة) — multi-select, same Set<string>
 * toggle contract as PillGroup elsewhere in FilterBar. */
export function MultiSelectDropdown({
  label,
  options,
  active,
  onToggle,
}: {
  label: string;
  options: string[];
  active: Set<string>;
  onToggle: (v: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  if (options.length === 0) return <span className="text-xs text-slate-600">—</span>;

  const filtered = query.trim()
    ? options.filter((o) => o.toLowerCase().includes(query.trim().toLowerCase()))
    : options;

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`flex w-full items-center justify-between gap-2 rounded-xl border px-3 py-2 text-xs font-medium transition ${
          active.size > 0
            ? 'border-cyan-500/40 bg-cyan-500/10 text-cyan-300'
            : 'border-white/8 bg-white/[0.02] text-slate-300 hover:border-white/15'
        }`}
      >
        <span className="truncate">{active.size > 0 ? `${label} (${active.size})` : label}</span>
        <span className={`shrink-0 text-[10px] transition-transform ${open ? 'rotate-180' : ''}`}>▾</span>
      </button>

      {open && (
        <div className="absolute z-20 mt-1.5 max-h-64 w-64 overflow-hidden rounded-xl border border-white/10 bg-[#0c1220] shadow-xl shadow-black/40">
          {options.length > 8 && (
            <div className="border-b border-white/8 p-2">
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="بحث…"
                className="w-full rounded-lg border border-white/8 bg-white/[0.03] px-2.5 py-1.5 text-xs text-slate-200 placeholder:text-slate-500 outline-none focus:border-cyan-500/50"
              />
            </div>
          )}
          <div className="max-h-52 overflow-y-auto p-1.5">
            {filtered.length === 0 && (
              <p className="px-2 py-3 text-center text-xs text-slate-500">لا توجد نتائج</p>
            )}
            {filtered.map((opt) => (
              <label
                key={opt}
                className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-slate-300 hover:bg-white/5"
              >
                <input
                  type="checkbox"
                  checked={active.has(opt)}
                  onChange={() => onToggle(opt)}
                  className="h-3.5 w-3.5 shrink-0 rounded border-white/20 bg-white/5 text-cyan-500 focus:ring-0 focus:ring-offset-0"
                />
                <span className="truncate">{opt}</span>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
