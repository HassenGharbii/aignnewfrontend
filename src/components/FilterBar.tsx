import { useMemo, type ReactNode } from 'react';
import { useFilters } from '../context/FiltersContext';
import { GOVERNORATES } from '../data/governorates';
import { severityTone, statusTone, verificationTone, TONE_CLASSES } from '../lib/severity';
import { formatNumber } from '../lib/format';
import { countGrouped } from '../lib/arabicText';

function PillGroup({
  options,
  active,
  onToggle,
  toneFor,
}: {
  options: string[];
  active: Set<string>;
  onToggle: (v: string) => void;
  toneFor?: (v: string) => keyof typeof TONE_CLASSES;
}) {
  if (options.length === 0) return <span className="text-xs text-slate-600">—</span>;
  return (
    <div className="flex flex-wrap items-start gap-1.5">
      {options.map((opt) => {
        const isActive = active.has(opt);
        const tone = toneFor ? toneFor(opt) : 'neutral';
        return (
          <button
            key={opt}
            title={opt}
            onClick={() => onToggle(opt)}
            className={`max-w-[220px] truncate rounded-full border px-2.5 py-1 text-xs font-medium whitespace-nowrap transition ${
              isActive
                ? TONE_CLASSES[tone]
                : 'border-white/8 bg-white/[0.02] text-slate-400 hover:border-white/15 hover:text-slate-200'
            }`}
          >
            {opt}
          </button>
        );
      })}
    </div>
  );
}

function FilterGroup({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      {children}
    </div>
  );
}

export function FilterBar() {
  const {
    filters,
    toggleGovernorate,
    toggleSeverity,
    toggleStatus,
    toggleSubCategory,
    toggleVerification,
    setDateRange,
    clearFilters,
    hasActiveFilters,
    allEvents,
    filteredEvents,
    totalEventsCount,
  } = useFilters();

  const severities = useMemo(
    () => countGrouped(allEvents.map((e) => e.severity).filter(Boolean)).map(([name]) => name),
    [allEvents],
  );
  const statuses = useMemo(
    () => countGrouped(allEvents.map((e) => e.event_status).filter(Boolean)).map(([name]) => name),
    [allEvents],
  );
  const subCategories = useMemo(
    () =>
      countGrouped(allEvents.map((e) => e.sub_category).filter((v): v is string => Boolean(v))).map(
        ([name]) => name,
      ),
    [allEvents],
  );
  const verifications = useMemo(
    () =>
      countGrouped(
        allEvents.map((e) => e.parsed.verificationStatus).filter((v): v is string => Boolean(v)),
      ).map(([name]) => name),
    [allEvents],
  );
  const activeGovernorates = useMemo(
    () => new Set([...allEvents].map((e) => e.governorate?.ar).filter((v): v is string => Boolean(v))),
    [allEvents],
  );
  const governorateOptions = GOVERNORATES.filter((g) => activeGovernorates.has(g.ar)).map((g) => g.ar);

  return (
    <div className="rounded-3xl border border-white/8 bg-white/[0.03] p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="grid flex-1 items-start gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <FilterGroup label="الولاية">
            <div className="max-h-20 overflow-y-auto pe-1">
              <PillGroup options={governorateOptions} active={filters.governorates} onToggle={toggleGovernorate} />
            </div>
          </FilterGroup>
          <FilterGroup label="درجة الخطورة">
            <PillGroup options={severities} active={filters.severities} onToggle={toggleSeverity} toneFor={severityTone} />
          </FilterGroup>
          <FilterGroup label="حالة الحدث">
            <PillGroup options={statuses} active={filters.statuses} onToggle={toggleStatus} toneFor={statusTone} />
          </FilterGroup>
          <FilterGroup label="من تاريخ - إلى تاريخ">
            <div className="flex items-center gap-1.5">
              <input
                type="date"
                value={filters.dateFrom}
                onChange={(e) => setDateRange(e.target.value, filters.dateTo)}
                className="w-full rounded-lg border border-white/8 bg-white/[0.02] px-2 py-1.5 text-xs text-slate-200 outline-none transition focus:border-cyan-500/50"
              />
              <input
                type="date"
                value={filters.dateTo}
                onChange={(e) => setDateRange(filters.dateFrom, e.target.value)}
                className="w-full rounded-lg border border-white/8 bg-white/[0.02] px-2 py-1.5 text-xs text-slate-200 outline-none transition focus:border-cyan-500/50"
              />
            </div>
          </FilterGroup>
        </div>

        <div className="flex flex-col items-end gap-2">
          <div className="rounded-full bg-white/5 px-3 py-1.5 text-xs text-slate-400">
            <span className="font-bold text-cyan-300">{formatNumber(filteredEvents.length)}</span> /{' '}
            {formatNumber(totalEventsCount)}
          </div>
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="flex items-center gap-1 rounded-full border border-white/10 px-3 py-1 text-xs text-slate-300 transition hover:border-rose-400/40 hover:bg-rose-500/10 hover:text-rose-300"
            >
              ✕ مسح التصفية
            </button>
          )}
        </div>
      </div>

      {(subCategories.length > 1 || verifications.length > 0) && (
        <div className="mt-4 grid items-start gap-4 border-t border-white/8 pt-4 sm:grid-cols-2">
          {subCategories.length > 1 && (
            <FilterGroup label="سبب/نوع الحادث">
              <PillGroup options={subCategories} active={filters.subCategories} onToggle={toggleSubCategory} />
            </FilterGroup>
          )}
          {verifications.length > 0 && (
            <FilterGroup label="حالة التحقق">
              <PillGroup
                options={verifications}
                active={filters.verifications}
                onToggle={toggleVerification}
                toneFor={verificationTone}
              />
            </FilterGroup>
          )}
        </div>
      )}
    </div>
  );
}
