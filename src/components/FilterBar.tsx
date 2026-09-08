import { useMemo, type ReactNode } from 'react';
import { useFilters } from '../context/FiltersContext';
import { GOVERNORATES } from '../data/governorates';
import { severityTone, statusTone, verificationTone } from '../lib/severity';
import { formatNumber } from '../lib/format';
import { countGrouped } from '../lib/arabicText';
import { MultiSelectDropdown } from './ui/MultiSelectDropdown';

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
    toggleRegion,
    toggleDelegation,
    toggleImada,
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
  const regions = useMemo(
    () => countGrouped(allEvents.map((e) => e.region).filter(Boolean)).map(([name]) => name),
    [allEvents],
  );
  const delegations = useMemo(
    () =>
      countGrouped(allEvents.map((e) => e.parsed.locationDelegation).filter(Boolean)).map(([name]) => name),
    [allEvents],
  );
  const imadas = useMemo(
    () => countGrouped(allEvents.map((e) => e.parsed.locationImada).filter(Boolean)).map(([name]) => name),
    [allEvents],
  );

  return (
    <div className="rounded-3xl border border-white/8 bg-white/[0.03] p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="grid flex-1 items-start gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <FilterGroup label="الولاية">
            <MultiSelectDropdown options={governorateOptions} active={filters.governorates} onToggle={toggleGovernorate} />
          </FilterGroup>
          {regions.length > 0 && (
            <FilterGroup label="المنطقة">
              <MultiSelectDropdown options={regions} active={filters.regions} onToggle={toggleRegion} />
            </FilterGroup>
          )}
          <FilterGroup label="درجة الخطورة">
            <MultiSelectDropdown options={severities} active={filters.severities} onToggle={toggleSeverity} toneFor={severityTone} />
          </FilterGroup>
          <FilterGroup label="حالة الحدث">
            <MultiSelectDropdown options={statuses} active={filters.statuses} onToggle={toggleStatus} toneFor={statusTone} />
          </FilterGroup>
          {subCategories.length > 1 && (
            <FilterGroup label="سبب/نوع الحادث">
              <MultiSelectDropdown options={subCategories} active={filters.subCategories} onToggle={toggleSubCategory} />
            </FilterGroup>
          )}
          {verifications.length > 0 && (
            <FilterGroup label="حالة التحقق">
              <MultiSelectDropdown
                options={verifications}
                active={filters.verifications}
                onToggle={toggleVerification}
                toneFor={verificationTone}
              />
            </FilterGroup>
          )}
          {delegations.length > 0 && (
            <FilterGroup label="المعتمدية">
              <MultiSelectDropdown options={delegations} active={filters.delegations} onToggle={toggleDelegation} />
            </FilterGroup>
          )}
          {imadas.length > 0 && (
            <FilterGroup label="العمادة">
              <MultiSelectDropdown options={imadas} active={filters.imadas} onToggle={toggleImada} />
            </FilterGroup>
          )}
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
    </div>
  );
}
