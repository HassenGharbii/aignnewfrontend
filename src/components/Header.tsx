import { useFilters } from '../context/FiltersContext';
import { formatNumber } from '../lib/format';

const SECTIONS: Array<{ id: string; label: string }> = [
  { id: 'overview', label: 'نظرة عامة' },
  { id: 'charts', label: 'التحليلات' },
  { id: 'map', label: 'الخريطة' },
  { id: 'events', label: 'الحوادث' },
  { id: 'people', label: 'البحث عن أشخاص' },
];

function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

export function Header() {
  const { filters, setSearch, isLoading, refetch, totalEventsCount } = useFilters();

  return (
    <header className="sticky top-0 z-40 border-b border-white/5 bg-[var(--color-bg)]/85 backdrop-blur-xl">
      <div className="flex w-full flex-wrap items-center gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <img
            src="/garde-nationale-logo.png"
            alt="شعار الحرس الوطني"
            className="h-10 w-10 shrink-0 object-contain"
          />
          <div>
            <h1 className="text-sm font-bold tracking-tight text-slate-100 sm:text-base">
              لوحة مراقبة حوادث المرور
            </h1>
            <p className="text-[11px] text-slate-500">
              {totalEventsCount > 0 ? (
                <>
                  <span className="font-semibold text-cyan-400">{formatNumber(totalEventsCount)}</span> حادث
                  مسجّل · الجمهورية التونسية
                </>
              ) : (
                'الجمهورية التونسية'
              )}
            </p>
          </div>
        </div>

        <nav className="order-3 flex flex-1 flex-wrap items-center gap-1 rounded-full bg-white/5 p-1 sm:order-2 sm:w-fit">
          {SECTIONS.map((s) => (
            <button
              key={s.id}
              onClick={() => scrollTo(s.id)}
              className="rounded-full px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:bg-white/10 hover:text-white"
            >
              {s.label}
            </button>
          ))}
        </nav>

        <div className="order-2 flex items-center gap-2 sm:order-3 sm:ms-auto">
          <div className="relative">
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-500"
            >
              <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
              <path d="M21 21l-3.5-3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <input
              value={filters.search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="بحث في الحوادث…"
              className="w-40 rounded-full border border-white/10 bg-white/5 py-1.5 ps-9 pe-3 text-xs text-slate-200 placeholder:text-slate-500 outline-none transition focus:border-cyan-500/50 focus:bg-white/8 sm:w-60"
            />
          </div>
          <button
            onClick={() => refetch()}
            className="flex h-8 w-8 items-center justify-center rounded-full border border-white/10 bg-white/5 text-slate-300 transition hover:border-cyan-500/40 hover:text-cyan-300"
            title="تحديث البيانات"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              className={isLoading ? 'animate-spin' : ''}
            >
              <path
                d="M4 4v6h6M20 20v-6h-6M5.5 9A7.5 7.5 0 0 1 19 8m-.5 7A7.5 7.5 0 0 1 5 16"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>
      </div>
    </header>
  );
}
