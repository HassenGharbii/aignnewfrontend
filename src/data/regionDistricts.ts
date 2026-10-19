/** الإقليم -> المنطقة hierarchy used by the reporting units in the source
 * feed's source/target fields (e.g. "منطقة تونس", "إقليم تطاوين" are literal
 * values seen there) — this is the police operational structure, distinct
 * from the 24 official governorates in src/data/governorates.ts. */
export const REGION_TO_DISTRICTS: Record<string, string[]> = {
  'إقليم أريانة': ['منطقة أريانة', 'منطقة حدائق المنزه', 'منطقة المنيهلة', 'منطقة التضامن'],
  'إقليم تونس': ['منطقة تونس'],
  'إقليم بن عروس': ['منطقة بن عروس', 'منطقة فوشانة'],
  'إقليم بنزرت': ['منطقة بنزرت', 'منطقة ماطر'],
  'إقليم نابل': ['منطقة نابل', 'منطقة قرمبالية', 'منطقة م تميم'],
  'إقليم باجة': ['منطقة باجة', 'منطقة مجاز الباب', 'منطقة طبربة'],
  'إقليم جندوبة': ['منطقة جندوبة', 'منطقة طبرقة', 'منطقة غار الدماء'],
  'إقليم الكاف': ['منطقة الكاف', 'منطقة تاجروين'],
  'إقليم سليانة': ['منطقة سليانة', 'منطقة قعفور'],
  'إقليم زغوان': ['منطقة زغوان', 'منطقة الفحص'],
  'إقليم القيروان': ['منطقة القيروان', 'منطقة حفوز', 'منطقة بوحجلة'],
  'إقليم القصرين': ['منطقة القصرين', 'منطقة تالة', 'منطقة فريانة', 'منطقة سبيطلة'],
  'إقليم سيدي بوزيد': ['منطقة سيدي بوزيد', 'منطقة الرقاب'],
  'إقليم سوسة': ['منطقة سوسة', 'منطقة مساكن', 'منطقة النفيضة'],
  'إقليم المنستير': ['منطقة المنستير', 'منطقة طبلبة', 'منطقة الجم'],
  'إقليم المهدية': ['منطقة المهدية', 'منطقة المحرس', 'منطقة جبناينة'],
  'إقليم صفاقس': ['منطقة صفاقس'],
  'إقليم قابس': ['منطقة قابس', 'منطقة مارث'],
  'إقليم مدنين': ['منطقة مدنين', 'منطقة بنقردان', 'منطقة رمادة'],
  'إقليم قبلي': ['منطقة قبلي', 'منطقة دوز'],
  'إقليم توزر': ['منطقة توزر الشمالية', 'منطقة توزر الجنوبية'],
  'إقليم قفصة': ['منطقة قفصة', 'منطقة قصر قفصة', 'منطقة المتلوي'],
};

export const ALL_DISTRICTS: string[] = Object.values(REGION_TO_DISTRICTS).flat();

const DISTRICT_TO_REGION: Record<string, string> = Object.fromEntries(
  Object.entries(REGION_TO_DISTRICTS).flatMap(([region, districts]) => districts.map((d) => [d, region])),
);

/** Best-effort match of free-text candidates (source/target/location fields)
 * against the fixed district list, checked in the given priority order. */
export function matchDistrict(...texts: Array<string | null | undefined>): string | null {
  for (const text of texts) {
    if (!text) continue;
    for (const district of ALL_DISTRICTS) {
      if (text.includes(district)) return district;
    }
  }
  return null;
}

export function regionForDistrict(district: string): string | null {
  return DISTRICT_TO_REGION[district] ?? null;
}
