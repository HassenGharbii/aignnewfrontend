import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import type { RawEvent } from '../api/types';
import { parseEvents, type ParsedEvent } from '../lib/parseEvent';
import { isSameCategory } from '../lib/arabicText';
import { useDebouncedValue } from '../lib/useDebouncedValue';

const EVENTS_PAGE_LIMIT = 500;

/** Fetches every page for one filter combination, following `total_pages` instead of trusting a single page. */
async function fetchAllPages(params: { search?: string; region?: string; sub_category?: string }): Promise<RawEvent[]> {
  const first = await api.events({ ...params, limit: EVENTS_PAGE_LIMIT, offset: 0 });
  const extraPages = Math.max(0, first.total_pages - 1);
  if (extraPages === 0) return first.data;

  const rest = await Promise.all(
    Array.from({ length: extraPages }, (_, i) =>
      api.events({ ...params, limit: EVENTS_PAGE_LIMIT, offset: (i + 1) * EVENTS_PAGE_LIMIT }).then((p) => p.data),
    ),
  );
  return [first.data, ...rest].flat();
}

/**
 * The API takes one value per filter param, but governorate/sub-category
 * pickers allow multiple selections — so each combination of selected values
 * (cartesian product across the multi-select fields) becomes its own request,
 * run in parallel and merged/deduped by id. Empty selections mean "no filter
 * for that field" and contribute a single `undefined` slot to the product.
 */
async function fetchFilteredEvents(search: string, regions: string[], subCategories: string[]): Promise<RawEvent[]> {
  const regionOptions = regions.length > 0 ? regions : [undefined];
  const subCategoryOptions = subCategories.length > 0 ? subCategories : [undefined];

  const requests: Promise<RawEvent[]>[] = [];
  for (const region of regionOptions) {
    for (const sub_category of subCategoryOptions) {
      requests.push(fetchAllPages({ search: search || undefined, region, sub_category }));
    }
  }

  const pages = await Promise.all(requests);
  const byId = new Map<number, RawEvent>();
  for (const page of pages) for (const event of page) byId.set(event.id, event);
  return [...byId.values()];
}

export interface FiltersState {
  search: string;
  governorates: Set<string>; // Governorate.ar
  severities: Set<string>;
  statuses: Set<string>;
  subCategories: Set<string>;
  verifications: Set<string>;
  dateFrom: string; // yyyy-mm-dd
  dateTo: string;
}

const EMPTY_FILTERS: FiltersState = {
  search: '',
  governorates: new Set(),
  severities: new Set(),
  statuses: new Set(),
  subCategories: new Set(),
  verifications: new Set(),
  dateFrom: '',
  dateTo: '',
};

/** yyyy-mm-dd for one calendar day ago — the default lower bound so the dashboard opens on the last day of activity. */
function yesterdayDateString(): string {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().slice(0, 10);
}

interface FiltersContextValue {
  filters: FiltersState;
  setSearch: (v: string) => void;
  toggleGovernorate: (ar: string) => void;
  setGovernorate: (ar: string | null) => void;
  toggleSeverity: (v: string) => void;
  toggleStatus: (v: string) => void;
  toggleSubCategory: (v: string) => void;
  toggleVerification: (v: string) => void;
  setDateRange: (from: string, to: string) => void;
  clearFilters: () => void;
  hasActiveFilters: boolean;
  allEvents: ParsedEvent[];
  filteredEvents: ParsedEvent[];
  /** Grand total across the whole dataset, independent of any active filters. */
  totalEventsCount: number;
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
}

const FiltersContext = createContext<FiltersContextValue | null>(null);

function toggleInSet(set: Set<string>, value: string): Set<string> {
  const next = new Set(set);
  if (next.has(value)) next.delete(value);
  else next.add(value);
  return next;
}

export function FiltersProvider({ children }: { children: ReactNode }) {
  const [filters, setFilters] = useState<FiltersState>(() => ({
    ...EMPTY_FILTERS,
    dateFrom: yesterdayDateString(),
  }));

  const debouncedSearch = useDebouncedValue(filters.search.trim(), 300);
  const regionKey = useMemo(() => [...filters.governorates].sort(), [filters.governorates]);
  const subCategoryKey = useMemo(() => [...filters.subCategories].sort(), [filters.subCategories]);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['events', debouncedSearch, regionKey, subCategoryKey],
    queryFn: () => fetchFilteredEvents(debouncedSearch, regionKey, subCategoryKey),
  });

  // Unaffected by filters — pulled once from the stats endpoint so headline
  // counts don't shrink to whatever the current filtered fetch happens to hold.
  const { data: summary } = useQuery({
    queryKey: ['summary'],
    queryFn: api.summary,
    staleTime: 5 * 60 * 1000,
  });

  const allEvents = useMemo(() => (data ? parseEvents(data) : []), [data]);

  const filteredEvents = useMemo(() => {
    const search = filters.search.trim().toLowerCase();
    const from = filters.dateFrom ? new Date(filters.dateFrom) : null;
    const to = filters.dateTo ? new Date(filters.dateTo) : null;

    return allEvents.filter((e) => {
      if (filters.governorates.size > 0) {
        if (!e.governorate || !filters.governorates.has(e.governorate.ar)) return false;
      }
      if (filters.severities.size > 0 && ![...filters.severities].some((v) => isSameCategory(v, e.severity)))
        return false;
      if (filters.statuses.size > 0 && ![...filters.statuses].some((v) => isSameCategory(v, e.event_status)))
        return false;
      if (filters.subCategories.size > 0) {
        if (!e.sub_category || ![...filters.subCategories].some((v) => isSameCategory(v, e.sub_category!)))
          return false;
      }
      if (filters.verifications.size > 0) {
        if (
          !e.parsed.verificationStatus ||
          ![...filters.verifications].some((v) => isSameCategory(v, e.parsed.verificationStatus!))
        )
          return false;
      }
      if (from && e.eventDate && e.eventDate < from) return false;
      if (to && e.eventDate && e.eventDate > to) return false;
      if (search) {
        const haystack = [
          e.event_title,
          e.region,
          e.parsed.description,
          e.event_summary,
          e.parsed.reportedBy,
          e.parsed.verifiedBy,
          e.parsed.source,
          ...e.parsed.keywords,
        ]
          .join(' ')
          .toLowerCase();
        if (!haystack.includes(search)) return false;
      }
      return true;
    });
  }, [allEvents, filters]);

  const value: FiltersContextValue = {
    filters,
    setSearch: (v) => setFilters((f) => ({ ...f, search: v })),
    toggleGovernorate: (ar) => setFilters((f) => ({ ...f, governorates: toggleInSet(f.governorates, ar) })),
    setGovernorate: (ar) =>
      setFilters((f) => ({ ...f, governorates: ar ? new Set([ar]) : new Set() })),
    toggleSeverity: (v) => setFilters((f) => ({ ...f, severities: toggleInSet(f.severities, v) })),
    toggleStatus: (v) => setFilters((f) => ({ ...f, statuses: toggleInSet(f.statuses, v) })),
    toggleSubCategory: (v) => setFilters((f) => ({ ...f, subCategories: toggleInSet(f.subCategories, v) })),
    toggleVerification: (v) => setFilters((f) => ({ ...f, verifications: toggleInSet(f.verifications, v) })),
    setDateRange: (from, to) => setFilters((f) => ({ ...f, dateFrom: from, dateTo: to })),
    clearFilters: () => setFilters(EMPTY_FILTERS),
    hasActiveFilters:
      filters.search !== '' ||
      filters.governorates.size > 0 ||
      filters.severities.size > 0 ||
      filters.statuses.size > 0 ||
      filters.subCategories.size > 0 ||
      filters.verifications.size > 0 ||
      filters.dateFrom !== '' ||
      filters.dateTo !== '',
    allEvents,
    filteredEvents,
    totalEventsCount: summary?.total_events ?? allEvents.length,
    isLoading,
    isError,
    refetch,
  };

  return <FiltersContext.Provider value={value}>{children}</FiltersContext.Provider>;
}

export function useFilters(): FiltersContextValue {
  const ctx = useContext(FiltersContext);
  if (!ctx) throw new Error('useFilters must be used within FiltersProvider');
  return ctx;
}
