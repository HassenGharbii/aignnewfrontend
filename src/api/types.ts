export interface SubCategoryCount {
  sub_category: string;
  count: number;
}

export interface CategoryCount {
  category: string;
  count: number;
  sub_categories: SubCategoryCount[];
}

export interface RecentEvent {
  event_title: string;
  category: string;
  event_time: string | null;
  region: string;
}

export interface StatsSummary {
  total_events: number;
  events_by_category: CategoryCount[];
  recent_events: RecentEvent[];
}

export interface RawEvent {
  id: number;
  event_summary: string;
  event_summary_hash: string;
  event_time: string | null;
  source: string;
  target: string;
  category: string;
  sub_category: string | null;
  event_title: string;
  event_status: string;
  severity: string;
  priority: string;
  region: string;
  details: string;
  created_at: string;
  updated_at: string;
  classification_scores: unknown;
  sub_category_score: unknown;
}

export interface EventsPage {
  total_items: number;
  total_pages: number;
  current_page: number;
  data: RawEvent[];
}

export interface CategoryPage {
  category: string;
  total_items: number;
  total_pages: number;
  current_page: number;
  data: RawEvent[];
}

export interface PersonHistoryRecord {
  record_id: number;
  created_at: string;
  event_category: string;
  event_sub_category: string | null;
  event_region: string;
  event_severity: string;
  event_title: string;
  event_summary: string;
  event_datetime: string | null;
  event_location: string;
  source_text: string;
  person_status: string;
  legal_state: string;
  risk_level: string;
  role_detail: string;
  injury_type: string;
}

export interface PersonResult {
  cin: string;
  name: string;
  nickname: string | null;
  gender: string;
  age_range: string;
  phone: string | null;
  address: string | null;
  occupation: string | null;
  criminal_record: string | null;
  risk_level: string;
  event_count: number;
  last_seen: string;
  history: PersonHistoryRecord[];
}

export interface PeopleSearchResult {
  count: number;
  results: PersonResult[];
}

export interface PeopleSearchParams {
  query?: string;
  cin?: string;
  region?: string;
  category?: string;
  status?: string;
  severity?: string;
  limit?: number;
  offset?: number;
}

export interface EventsParams {
  limit?: number;
  offset?: number;
  category?: string;
  sub_category?: string;
  region?: string;
  search?: string;
}

/** Parsed shape of the nested `تفاصيل_الحادث` block inside RawEvent.details */
export interface IncidentFacts {
  نوع_الحادث: string;
  حالة_الطريق: string;
  عدد_الوفيات: number;
  عدد_الإصابات: number;
  عدد_المركبات: number;
  مواد_خطرة_متسربة: boolean;
}

export interface ParsedPerson {
  name?: string;
  license?: string;
  gender?: string;
  ageRange?: string;
  occupation?: string;
  roleDetail?: string;
  injuryType?: string;
}

export interface ParsedDetails {
  title: string;
  description: string;
  keywords: string[];
  source: string;
  locationAddress: string;
  locationArea: string;
  confidence: number | null;
  verificationStatus: string | null;
  reportedBy: string | null;
  verifiedBy: string | null;
  eventDatetime: string | null;
  facts: Partial<IncidentFacts>;
  people: ParsedPerson[];
  raw: Record<string, unknown>;
}
