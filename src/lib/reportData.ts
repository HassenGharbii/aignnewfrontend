import type { ParsedEvent } from './parseEvent';

export interface CountRow {
  name: string;
  count: number;
}

export interface LocationBreakdown {
  region: CountRow[]; // الإقليم
  area: CountRow[]; // المنطقة
  delegation: CountRow[]; // المعتمدية
  imada: CountRow[]; // العمادة
}

export interface TimeBucketRow {
  label: string;
  count: number;
  deaths: number;
  injuries: number;
}

export interface ReportData {
  periodLabel: string;
  totalEvents: number;
  general: { count: number; deaths: number; injuries: number };
  byLocationIncidents: LocationBreakdown;
  byLocationDeaths: LocationBreakdown;
  byLocationInjuries: LocationBreakdown;
  byRoadType: CountRow[];
  byCause: CountRow[];
  byDayOfWeek: TimeBucketRow[];
  byHourOfDay: TimeBucketRow[];
  byPartyType: CountRow[];
  regionHourMatrix: { region: string; hours: number[] }[];
  partyTypeCoverage: number; // fraction of events with at least one party type recorded
}

const DAY_ORDER = [1, 2, 3, 4, 5, 6, 0];
const DAY_LABELS: Record<number, string> = {
  1: 'الاثنين',
  2: 'الثلاثاء',
  3: 'الأربعاء',
  4: 'الخميس',
  5: 'الجمعة',
  6: 'السبت',
  0: 'الأحد',
};

/** Counts occurrences per key. Zero/empty keys are dropped and rows with a
 * zero result never appear — matches the source template's own rule: "عرض
 * النتائج فقط للقيم الأكبر من صفر". */
function countBy(events: ParsedEvent[], keyFn: (e: ParsedEvent) => string | null | undefined): CountRow[] {
  const counts = new Map<string, number>();
  for (const e of events) {
    const key = keyFn(e);
    if (!key) continue;
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count);
}

/** Sums a numeric field per key (e.g. deaths per governorate) instead of
 * counting events. */
function sumBy(
  events: ParsedEvent[],
  keyFn: (e: ParsedEvent) => string | null | undefined,
  valueFn: (e: ParsedEvent) => number,
): CountRow[] {
  const sums = new Map<string, number>();
  for (const e of events) {
    const key = keyFn(e);
    if (!key) continue;
    sums.set(key, (sums.get(key) ?? 0) + valueFn(e));
  }
  return [...sums.entries()]
    .map(([name, count]) => ({ name, count }))
    .filter((r) => r.count > 0)
    .sort((a, b) => b.count - a.count);
}

function locationBreakdown(events: ParsedEvent[], valueFn: (e: ParsedEvent) => number): LocationBreakdown {
  return {
    region: sumBy(events, (e) => e.policeRegion, valueFn),
    area: sumBy(events, (e) => e.parsed.locationArea, valueFn),
    delegation: sumBy(events, (e) => e.parsed.locationDelegation, valueFn),
    imada: sumBy(events, (e) => e.parsed.locationImada, valueFn),
  };
}

export function buildReportData(events: ParsedEvent[], periodLabel: string): ReportData {
  const deaths = events.reduce((sum, e) => sum + (e.parsed.facts.عدد_الوفيات ?? 0), 0);
  const injuries = events.reduce((sum, e) => sum + (e.parsed.facts.عدد_الإصابات ?? 0), 0);

  const withTime = events.filter((e) => e.eventDate);

  const byDayOfWeek: TimeBucketRow[] = DAY_ORDER.map((d) => {
    const bucket = withTime.filter((e) => e.eventDate!.getDay() === d);
    return {
      label: DAY_LABELS[d],
      count: bucket.length,
      deaths: bucket.reduce((s, e) => s + (e.parsed.facts.عدد_الوفيات ?? 0), 0),
      injuries: bucket.reduce((s, e) => s + (e.parsed.facts.عدد_الإصابات ?? 0), 0),
    };
  }).filter((r) => r.count > 0);

  const byHourOfDay: TimeBucketRow[] = Array.from({ length: 24 }, (_, h) => {
    const bucket = withTime.filter((e) => e.eventDate!.getHours() === h);
    return {
      label: `${h}:00`,
      count: bucket.length,
      deaths: bucket.reduce((s, e) => s + (e.parsed.facts.عدد_الوفيات ?? 0), 0),
      injuries: bucket.reduce((s, e) => s + (e.parsed.facts.عدد_الإصابات ?? 0), 0),
    };
  }).filter((r) => r.count > 0);

  const partyCounts = new Map<string, number>();
  let eventsWithPartyType = 0;
  for (const e of events) {
    if (e.parsed.partyTypes.length > 0) eventsWithPartyType += 1;
    for (const type of new Set(e.parsed.partyTypes)) {
      partyCounts.set(type, (partyCounts.get(type) ?? 0) + 1);
    }
  }
  const byPartyType = [...partyCounts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count);

  // Combination (day/hour/region): top أقاليم x hour-of-day. Uses policeRegion
  // (not governorate) to match the الإقليم/المنطقة vocabulary used everywhere
  // else in this report — the dashboard's RegionTimeHeatmap chart is a
  // separate, governorate-based view and isn't required to match this 1:1.
  const withTimeAndRegion = withTime.filter((e) => e.policeRegion);
  const regionCounts = countBy(withTimeAndRegion, (e) => e.policeRegion!).slice(0, 10);
  const regionHourMatrix = regionCounts.map(({ name }) => {
    const hours = new Array(24).fill(0);
    for (const e of withTimeAndRegion) {
      if (e.policeRegion === name) hours[e.eventDate!.getHours()] += 1;
    }
    return { region: name, hours };
  });

  return {
    periodLabel,
    totalEvents: events.length,
    general: { count: events.length, deaths, injuries },
    byLocationIncidents: locationBreakdown(events, () => 1),
    byLocationDeaths: locationBreakdown(events, (e) => e.parsed.facts.عدد_الوفيات ?? 0),
    byLocationInjuries: locationBreakdown(events, (e) => e.parsed.facts.عدد_الإصابات ?? 0),
    byRoadType: countBy(events, (e) => e.parsed.facts.نوع_الطريق),
    byCause: countBy(events, (e) => e.sub_category),
    byDayOfWeek,
    byHourOfDay,
    byPartyType,
    regionHourMatrix,
    partyTypeCoverage: events.length > 0 ? eventsWithPartyType / events.length : 0,
  };
}
