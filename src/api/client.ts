import type {
  EventsPage,
  EventsParams,
  PeopleSearchParams,
  PeopleSearchResult,
  StatsSummary,
} from './types';

export const API_BASE = import.meta.env.VITE_API_BASE_URL;

async function getJson<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(path, API_BASE);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== '') url.searchParams.set(key, String(value));
    }
  }
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${url}`);
  return res.json() as Promise<T>;
}

export const api = {
  summary: () => getJson<StatsSummary>('/api/stats/summary'),

  categories: () => getJson<string[]>('/api/categories'),

  events: (params: EventsParams = {}) =>
    getJson<EventsPage>('/api/events', {
      limit: params.limit ?? 400,
      offset: params.offset ?? 0,
      category: params.category,
      sub_category: params.sub_category,
      region: params.region,
      search: params.search,
    }),

  peopleSearch: (params: PeopleSearchParams = {}) =>
    getJson<PeopleSearchResult>('/people/search', {
      query: params.query,
      cin: params.cin,
      region: params.region,
      category: params.category,
      status: params.status,
      severity: params.severity,
      limit: params.limit ?? 50,
      offset: params.offset ?? 0,
    }),
};
