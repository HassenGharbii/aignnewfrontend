import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import type { RawEvent } from '../api/types';
import { parseEvents, type ParsedEvent } from '../lib/parseEvent';
import { isSameCategory } from '../lib/arabicText';
import { useDebouncedValue } from '../lib/useDebouncedValue';

const EVENTS_PAGE_LIMIT = 500;

/** This dashboard is dedicated to traffic incidents — every fetch is scoped to this main category. */
const TRAFFIC_CATEGORY = 'أحداث مرورية';

/**
 * Fetches every page for one filter combination by walking `offset` forward
 * by however many rows actually came back — the API doesn't reliably honor
 * the requested `limit`, so `total_pages` (computed server-side off its own,
 * possibly much smaller, effective page size) can't be used to derive the
 * next offset. Stops once `total_items` rows have been collected or a page
 * comes back empty; the iteration cap is just a guard against a runaway
 * loop if `total_items` is ever wrong.
 */
async function fetchAllPages(params: {
  category?: string;
  search?: string;
  sub_category?: string;
}): Promise<RawEvent[]> {
  const results: RawEvent[] = [];
  let offset = 0;
  let totalItems = Infinity;

  for (let i = 0; i < 2000 && offset < totalItems; i++) {
    const page = await api.events({ ...params, limit: EVENTS_PAGE_LIMIT, offset });
    totalItems = page.total_items;
    if (page.data.length === 0) break;
    results.push(...page.data);
    offset += page.data.length;
  }

  return results;
}

/**
 * The API takes one value per filter param, but sub-category picking allows
 * multiple selections — so each selected value becomes its own request, run
 * in parallel and merged/deduped by id. إقليم/المنطقة/المعتمدية/العمادة are all
 * filtered client-side only (see filteredEvents below), not fetched per-value.
 */
async function fetchFilteredEvents(search: string, subCategories: string[]): Promise<RawEvent[]> {
  const subCategoryOptions = subCategories.length > 0 ? subCategories : [undefined];

  const requests = subCategoryOptions.map((sub_category) =>
    fetchAllPages({ category: TRAFFIC_CATEGORY, search: search || undefined, sub_category }),
  );

  const pages = await Promise.all(requests);
  const byId = new Map<number, RawEvent>();
  for (const page of pages) for (const event of page) byId.set(event.id, event);
  return [...byId.values()];
}

export interface FiltersState {
  search: string;
  policeRegions: Set<string>; // الإقليم (police operational region)
  policeDistricts: Set<string>; // المنطقة (police operational district)
  delegations: Set<string>; // المعتمدية
  imadas: Set<string>; // العمادة
  severities: Set<string>;
  statuses: Set<string>;
  subCategories: Set<string>;
  verifications: Set<string>;
  dateFrom: string; // yyyy-mm-dd
  dateTo: string;
}

const EMPTY_FILTERS: FiltersState = {
  search: '',
  policeRegions: new Set(),
  policeDistricts: new Set(),
  delegations: new Set(),
  imadas: new Set(),
  severities: new Set(),
  statuses: new Set(),
  subCategories: new Set(),
  verifications: new Set(),
  dateFrom: '',
  dateTo: '',
};

interface FiltersContextValue {
  filters: FiltersState;
  setSearch: (v: string) => void;
  togglePoliceRegion: (v: string) => void;
  togglePoliceDistrict: (v: string) => void;
  toggleDelegation: (v: string) => void;
  toggleImada: (v: string) => void;
  toggleSeverity: (v: string) => void;
  toggleStatus: (v: string) => void;
  toggleSubCategory: (v: string) => void;
  toggleVerification: (v: string) => void;
  setDateRange: (from: string, to: string) => void;
  clearFilters: () => void;
  hasActiveFilters: boolean;
  allEvents: ParsedEvent[];
  filteredEvents: ParsedEvent[];
  /** Grand total of traffic-category events, independent of any active filters. */
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
  const [filters, setFilters] = useState<FiltersState>(EMPTY_FILTERS);

  const debouncedSearch = useDebouncedValue(filters.search.trim(), 300);
  const subCategoryKey = useMemo(() => [...filters.subCategories].sort(), [filters.subCategories]);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['events', debouncedSearch, subCategoryKey],
    queryFn: () => fetchFilteredEvents(debouncedSearch, subCategoryKey),
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
      if (filters.policeRegions.size > 0) {
        if (!e.policeRegion || !filters.policeRegions.has(e.policeRegion)) return false;
      }
      if (filters.policeDistricts.size > 0) {
        if (!e.policeDistrict || !filters.policeDistricts.has(e.policeDistrict)) return false;
      }
      if (filters.delegations.size > 0) {
        if (
          !e.parsed.locationDelegation ||
          ![...filters.delegations].some((v) => isSameCategory(v, e.parsed.locationDelegation))
        )
          return false;
      }
      if (filters.imadas.size > 0) {
        if (
          !e.parsed.locationImada ||
          ![...filters.imadas].some((v) => isSameCategory(v, e.parsed.locationImada))
        )
          return false;
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
          e.policeRegion,
          e.policeDistrict,
          e.parsed.description,
          e.event_summary,
          e.parsed.reportedBy,
          e.parsed.verifiedBy,
          e.parsed.source,
          e.parsed.locationDelegation,
          e.parsed.locationImada,
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
    togglePoliceRegion: (v) => setFilters((f) => ({ ...f, policeRegions: toggleInSet(f.policeRegions, v) })),
    togglePoliceDistrict: (v) => setFilters((f) => ({ ...f, policeDistricts: toggleInSet(f.policeDistricts, v) })),
    toggleDelegation: (v) => setFilters((f) => ({ ...f, delegations: toggleInSet(f.delegations, v) })),
    toggleImada: (v) => setFilters((f) => ({ ...f, imadas: toggleInSet(f.imadas, v) })),
    toggleSeverity: (v) => setFilters((f) => ({ ...f, severities: toggleInSet(f.severities, v) })),
    toggleStatus: (v) => setFilters((f) => ({ ...f, statuses: toggleInSet(f.statuses, v) })),
    toggleSubCategory: (v) => setFilters((f) => ({ ...f, subCategories: toggleInSet(f.subCategories, v) })),
    toggleVerification: (v) => setFilters((f) => ({ ...f, verifications: toggleInSet(f.verifications, v) })),
    setDateRange: (from, to) => setFilters((f) => ({ ...f, dateFrom: from, dateTo: to })),
    clearFilters: () => setFilters(EMPTY_FILTERS),
    hasActiveFilters:
      filters.search !== '' ||
      filters.policeRegions.size > 0 ||
      filters.policeDistricts.size > 0 ||
      filters.delegations.size > 0 ||
      filters.imadas.size > 0 ||
      filters.severities.size > 0 ||
      filters.statuses.size > 0 ||
      filters.subCategories.size > 0 ||
      filters.verifications.size > 0 ||
      filters.dateFrom !== '' ||
      filters.dateTo !== '',
    allEvents,
    filteredEvents,
    totalEventsCount:
      summary?.events_by_category.find((c) => isSameCategory(c.category, TRAFFIC_CATEGORY))?.count ??
      allEvents.length,
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
