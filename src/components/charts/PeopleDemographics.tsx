import { useMemo } from 'react';
import { Card } from '../ui/Card';
import { ProgressRows } from '../ui/ProgressRows';
import { useFilters } from '../../context/FiltersContext';

const GENDER_LABELS: Record<string, string> = { male: 'ذكر', female: 'أنثى', unknown: 'غير معروف' };
const GENDER_COLORS: Record<string, string> = { male: '#38bdf8', female: '#f472b6', unknown: '#94a3b8' };

const AGE_LABELS: Record<string, string> = {
  adult: 'بالغ',
  child: 'طفل',
  teen: 'شاب/يافع',
  senior: 'مسن',
  unknown: 'غير معروف',
};
const AGE_COLORS: Record<string, string> = {
  adult: '#818cf8',
  child: '#fbbf24',
  teen: '#34d399',
  senior: '#a78bfa',
  unknown: '#94a3b8',
};

const INJURY_LABELS: Record<string, string> = {
  none: 'دون إصابة',
  minor: 'إصابة طفيفة',
  moderate: 'إصابة متوسطة',
  severe: 'إصابة بالغة',
  fatal: 'وفاة',
  unknown: 'غير معروف',
};
const INJURY_COLORS: Record<string, string> = {
  none: '#34d399',
  minor: '#fbbf24',
  moderate: '#fb923c',
  severe: '#fb7185',
  fatal: '#f43f5e',
  unknown: '#94a3b8',
};

function counts(values: string[]): [string, number][] {
  const map = new Map<string, number>();
  for (const v of values) map.set(v, (map.get(v) ?? 0) + 1);
  return [...map.entries()].sort((a, b) => b[1] - a[1]);
}

export function PeopleDemographics() {
  const { filteredEvents } = useFilters();

  const people = useMemo(() => filteredEvents.flatMap((e) => e.parsed.people), [filteredEvents]);
  const withDemographics = useMemo(() => people.filter((p) => p.gender), [people]);
  const coveredEvents = useMemo(
    () => filteredEvents.filter((e) => e.parsed.people.some((p) => p.gender)).length,
    [filteredEvents],
  );

  const genderRows = useMemo(
    () => counts(withDemographics.map((p) => p.gender!)),
    [withDemographics],
  );
  const ageRows = useMemo(() => counts(withDemographics.map((p) => p.ageRange ?? 'unknown')), [withDemographics]);
  const injuryRows = useMemo(
    () => counts(withDemographics.map((p) => p.injuryType ?? 'unknown')),
    [withDemographics],
  );

  if (withDemographics.length === 0) {
    return (
      <Card title="الأطراف المتورطة في الحوادث">
        <p className="py-6 text-center text-xs text-slate-500">لا توجد بيانات تفصيلية كافية عن الأطراف</p>
      </Card>
    );
  }

  return (
    <Card
      title="الأطراف المتورطة في الحوادث"
      subtitle={`بيانات تفصيلية متوفرة عن ${coveredEvents} من ${filteredEvents.length} حادثة · ${withDemographics.length} شخص`}
    >
      <div className="grid items-start gap-5 sm:grid-cols-3">
        <div>
          <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">الجنس</div>
          <ProgressRows
            rows={genderRows}
            colorFor={(name) => GENDER_COLORS[name] ?? '#94a3b8'}
            labelFor={(name) => GENDER_LABELS[name] ?? name}
          />
        </div>
        <div>
          <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">الفئة العمرية</div>
          <ProgressRows
            rows={ageRows}
            colorFor={(name) => AGE_COLORS[name] ?? '#94a3b8'}
            labelFor={(name) => AGE_LABELS[name] ?? name}
          />
        </div>
        <div>
          <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">شدة الإصابة</div>
          <ProgressRows
            rows={injuryRows}
            colorFor={(name) => INJURY_COLORS[name] ?? '#94a3b8'}
            labelFor={(name) => INJURY_LABELS[name] ?? name}
          />
        </div>
      </div>
    </Card>
  );
}
