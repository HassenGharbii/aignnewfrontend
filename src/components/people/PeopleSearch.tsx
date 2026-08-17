import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card } from '../ui/Card';
import { api } from '../../api/client';
import { useDebouncedValue } from '../../lib/useDebouncedValue';
import { formatDate, formatNumber, truncate } from '../../lib/format';
import type { PersonResult } from '../../api/types';
import { PersonModal } from './PersonModal';

export function PeopleSearch() {
  const [query, setQuery] = useState('');
  const [cin, setCin] = useState('');
  const [selected, setSelected] = useState<PersonResult | null>(null);

  const debouncedQuery = useDebouncedValue(query, 300);
  const debouncedCin = useDebouncedValue(cin, 300);

  const hasInput = debouncedQuery.trim() !== '' || debouncedCin.trim() !== '';

  const { data, isFetching } = useQuery({
    queryKey: ['people-search', debouncedQuery, debouncedCin],
    queryFn: () => api.peopleSearch({ query: debouncedQuery || undefined, cin: debouncedCin || undefined, limit: 25 }),
    enabled: hasInput,
  });

  return (
    <section id="people" className="scroll-mt-20">
      <Card title="البحث عن الأشخاص" subtitle="بالاسم أو رقم بطاقة التعريف الوطنية">
        <div className="flex flex-wrap gap-2.5">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="اسم الشخص…"
            className="min-w-[200px] flex-1 rounded-xl border border-white/8 bg-white/[0.02] px-3.5 py-2.5 text-sm text-slate-200 placeholder:text-slate-500 outline-none transition focus:border-cyan-500/50"
          />
          <input
            value={cin}
            onChange={(e) => setCin(e.target.value)}
            placeholder="رقم بطاقة التعريف الوطنية (CIN)…"
            className="min-w-[200px] flex-1 rounded-xl border border-white/8 bg-white/[0.02] px-3.5 py-2.5 text-sm text-slate-200 placeholder:text-slate-500 outline-none transition focus:border-cyan-500/50"
          />
        </div>

        <div className="mt-4">
          {!hasInput && (
            <p className="py-8 text-center text-sm text-slate-500">
              ابدأ الكتابة أعلاه لعرض الأشخاص المرتبطين بحوادث المرور وسجلّهم.
            </p>
          )}
          {hasInput && isFetching && <p className="py-8 text-center text-sm text-slate-400">جاري البحث…</p>}
          {hasInput && !isFetching && data && data.results.length === 0 && (
            <p className="py-8 text-center text-sm text-slate-500">لا توجد نتائج مطابقة</p>
          )}
          {hasInput && !isFetching && data && data.results.length > 0 && (
            <div className="grid items-start gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
              {data.results.map((p) => (
                <button
                  key={`${p.cin}-${p.name}`}
                  onClick={() => setSelected(p)}
                  className="rounded-xl border border-white/8 bg-white/[0.02] p-3.5 text-right transition hover:border-cyan-500/40 hover:bg-white/5"
                >
                  <div className="font-semibold text-slate-100">{p.name || 'غير معروف'}</div>
                  <div className="mt-1 text-xs text-slate-500">
                    {p.cin ? `CIN: ${p.cin}` : 'بدون CIN'} · {formatNumber(p.event_count)} حادث مرتبط
                  </div>
                  {p.history[0] && (
                    <div className="mt-1.5 text-xs text-slate-400">
                      {truncate(p.history[0].event_title, 50)} · {formatDate(p.history[0].event_datetime)}
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </Card>

      <PersonModal person={selected} onClose={() => setSelected(null)} />
    </section>
  );
}
