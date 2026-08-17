import { useMemo } from 'react';
import { Card } from '../ui/Card';
import { useFilters } from '../../context/FiltersContext';
import { countGrouped } from '../../lib/arabicText';

const MIN_SIZE = 11;
const MAX_SIZE = 20;

export function KeywordCloud() {
  const { filteredEvents, filters, setSearch } = useFilters();

  const keywords = useMemo(() => {
    const all = filteredEvents.flatMap((e) => e.parsed.keywords.map((k) => k.trim()).filter(Boolean));
    return countGrouped(all).slice(0, 18);
  }, [filteredEvents]);

  const max = Math.max(1, ...keywords.map(([, c]) => c));
  const min = Math.min(...keywords.map(([, c]) => c), max);

  if (keywords.length === 0) {
    return (
      <Card title="أكثر الكلمات تكرارًا في البلاغات">
        <p className="py-6 text-center text-xs text-slate-500">لا توجد كلمات مفتاحية مستخرجة</p>
      </Card>
    );
  }

  return (
    <Card title="أكثر الكلمات تكرارًا في البلاغات" subtitle="اضغط كلمة للبحث عنها">
      <div className="flex flex-wrap items-start gap-2">
        {keywords.map(([word, count]) => {
          const ratio = max === min ? 1 : (count - min) / (max - min);
          const size = MIN_SIZE + ratio * (MAX_SIZE - MIN_SIZE);
          const isActive = filters.search === word;
          return (
            <button
              key={word}
              onClick={() => setSearch(isActive ? '' : word)}
              style={{ fontSize: `${size}px` }}
              className={`rounded-full border px-3 py-1 font-medium transition ${
                isActive
                  ? 'border-cyan-500/50 bg-cyan-500/15 text-cyan-300'
                  : 'border-white/8 bg-white/[0.02] text-slate-300 hover:border-white/20 hover:text-white'
              }`}
              title={`${count} مرة`}
            >
              {word}
            </button>
          );
        })}
      </div>
    </Card>
  );
}
