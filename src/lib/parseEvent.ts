import type { ParsedDetails, RawEvent } from '../api/types';
import { matchGovernorate, type Governorate } from '../data/governorates';

export interface ParsedEvent extends RawEvent {
  parsed: ParsedDetails;
  governorate: Governorate | null;
  eventDate: Date | null;
}

function asRecord(v: unknown): Record<string, unknown> {
  return typeof v === 'object' && v !== null ? (v as Record<string, unknown>) : {};
}

function str(v: unknown): string {
  return typeof v === 'string' ? v : '';
}

/** The pipeline that produces `details` sometimes sends counts as numbers, sometimes as numeric strings — both are accepted. */
function num(v: unknown): number | null {
  if (typeof v === 'number' && Number.isFinite(v)) return v;
  if (typeof v === 'string' && v.trim() !== '' && Number.isFinite(Number(v))) return Number(v);
  return null;
}

/**
 * The API's `details` blob comes in two shapes depending on which NLP pipeline
 * run produced it: a flat "event_details"-style object, or that same object
 * wrapped under `{ event_details, people_details }` alongside a richer people
 * list. Both are normalized to ParsedDetails here.
 *
 * The API itself is inconsistent about whether `details` is sent as a JSON
 * string or already parsed into an object — both are accepted here.
 */
export function parseDetails(rawDetails: unknown): ParsedDetails {
  const empty: ParsedDetails = {
    title: '',
    description: '',
    keywords: [],
    source: '',
    locationAddress: '',
    locationArea: '',
    confidence: null,
    verificationStatus: null,
    reportedBy: null,
    verifiedBy: null,
    eventDatetime: null,
    facts: {},
    people: [],
    raw: {},
  };

  let parsed: unknown;
  if (typeof rawDetails === 'string') {
    try {
      parsed = JSON.parse(rawDetails);
    } catch {
      return empty;
    }
  } else if (rawDetails && typeof rawDetails === 'object') {
    parsed = rawDetails;
  } else {
    return empty;
  }
  const root = asRecord(parsed);
  const flat = asRecord(root.event_details ?? root);
  const peopleDetails = asRecord(root.people_details);

  // The extraction pipeline emits عنوان/كلمات_مفتاحية at the top level, not
  // nested under الوصف (an earlier pipeline version did) — fall back to `flat`
  // itself so both shapes work.
  const desc = asRecord(flat['الوصف'] ?? flat);
  const location = asRecord(flat['الموقع']);
  const classification = asRecord(flat['التصنيف']);
  const facts = asRecord(flat['تفاصيل_الحادث']);
  const timestamps = asRecord(flat['الطوابع_الزمنية']);
  const parties = asRecord(flat['الأطراف']);
  const audit = asRecord(flat['التدقيق']);
  const drivers = Array.isArray(parties['السائقون']) ? (parties['السائقون'] as unknown[]) : [];

  const peopleFromPartiesList = drivers.map((d) => {
    const r = asRecord(d);
    return { name: str(r['الاسم']) || undefined, license: str(r['الرخصة']) || undefined };
  });

  const peopleList = Array.isArray(peopleDetails.people) ? (peopleDetails.people as unknown[]) : [];
  const peopleFromDetailsList = peopleList.map((p) => {
    const r = asRecord(p);
    return {
      name: str(r.name) || undefined,
      license: str(r.cin) || undefined,
      gender: str(r.gender) || undefined,
      ageRange: str(r.age_range) || undefined,
      occupation: str(r.occupation) || undefined,
      roleDetail: str(r.role_detail) || undefined,
      injuryType: str(r.injury_type) || undefined,
    };
  });

  return {
    title: str(desc['عنوان']),
    description: str(desc['تفاصيل']),
    keywords: Array.isArray(desc['كلمات_مفتاحية']) ? (desc['كلمات_مفتاحية'] as string[]) : [],
    source: str(flat['المصدر']),
    locationAddress: str(location['العنوان']),
    locationArea: str(location['المنطقة']),
    confidence: num(classification['نسبة_الثقة']),
    verificationStatus: str(audit['حالة_التحقق']) || null,
    reportedBy: str(audit['تم_الإبلاغ_من']) || null,
    verifiedBy: str(audit['تم_التحقق_من']) || null,
    eventDatetime: str(timestamps['وقت_الحدث']) || null,
    facts: {
      نوع_الحادث: str(facts['نوع_الحادث']),
      حالة_الطريق: str(facts['حالة_الطريق']),
      عدد_الوفيات: num(facts['عدد_الوفيات']) ?? 0,
      عدد_الإصابات: num(facts['عدد_الإصابات']) ?? 0,
      عدد_المركبات: num(facts['عدد_المركبات']) ?? 0,
      مواد_خطرة_متسربة: Boolean(facts['مواد_خطرة_متسربة']),
    },
    people: peopleFromDetailsList.length > 0 ? peopleFromDetailsList : peopleFromPartiesList,
    raw: root,
  };
}

export function parseEvent(raw: RawEvent): ParsedEvent {
  const parsed = parseDetails(raw.details);
  const governorate = matchGovernorate(
    raw.region,
    parsed.locationArea,
    parsed.locationAddress,
    raw.source,
    raw.target,
  );
  const dateSource = parsed.eventDatetime ?? raw.created_at;
  const eventDate = dateSource ? new Date(dateSource) : null;

  return {
    ...raw,
    parsed,
    governorate,
    eventDate: eventDate && !Number.isNaN(eventDate.getTime()) ? eventDate : null,
  };
}

export function parseEvents(raw: RawEvent[]): ParsedEvent[] {
  return raw.map(parseEvent);
}
