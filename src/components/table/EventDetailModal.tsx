import { Modal } from '../ui/Modal';
import { Badge } from '../ui/Badge';
import type { ParsedEvent } from '../../lib/parseEvent';
import { formatDateTime, formatNumber } from '../../lib/format';
import { severityTone, statusTone, verificationTone } from '../../lib/severity';

const GENDER_LABELS: Record<string, string> = { male: 'ذكر', female: 'أنثى' };
const AGE_LABELS: Record<string, string> = { adult: 'بالغ', child: 'طفل', teen: 'يافع', senior: 'مسن' };
const INJURY_LABELS: Record<string, string> = {
  none: 'دون إصابة',
  minor: 'إصابة طفيفة',
  moderate: 'إصابة متوسطة',
  severe: 'إصابة بالغة',
  fatal: 'وفاة',
};

function Fact({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2">
      <div className="text-[11px] text-slate-500">{label}</div>
      <div className="mt-0.5 text-sm font-semibold text-slate-100">{value}</div>
    </div>
  );
}

export function EventDetailModal({ event, onClose }: { event: ParsedEvent | null; onClose: () => void }) {
  if (!event) return <Modal open={false} onClose={onClose} title="" />;

  const { parsed } = event;
  const facts = parsed.facts;

  return (
    <Modal open={Boolean(event)} onClose={onClose} title={event.event_title || parsed.title || 'تفاصيل الحادث'}>
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge label={event.severity} tone={severityTone(event.severity)} />
          <Badge label={event.event_status} tone={statusTone(event.event_status)} />
          {parsed.verificationStatus && (
            <Badge label={parsed.verificationStatus} tone={verificationTone(parsed.verificationStatus)} />
          )}
          {event.priority && (
            <span className="rounded-full border border-white/10 px-2.5 py-1 text-xs text-slate-300">
              الأولوية {event.priority}
            </span>
          )}
          {event.sub_category && (
            <span className="rounded-full border border-white/10 px-2.5 py-1 text-xs text-slate-300">
              {event.sub_category}
            </span>
          )}
          <span className="text-xs text-slate-500">
            {formatDateTime(event.eventDate)} · {event.governorate?.ar ?? event.region}
          </span>
        </div>

        {parsed.description && (
          <p className="rounded-xl bg-white/5 p-3 text-sm leading-relaxed text-slate-200">{parsed.description}</p>
        )}

        <div className="grid grid-cols-2 items-start gap-2 sm:grid-cols-4">
          <Fact label="نوع الحادث" value={facts.نوع_الحادث || '—'} />
          <Fact label="عدد القتلى" value={formatNumber(facts.عدد_الوفيات ?? 0)} />
          <Fact label="عدد الجرحى" value={formatNumber(facts.عدد_الإصابات ?? 0)} />
          <Fact label="عدد المركبات" value={formatNumber(facts.عدد_المركبات ?? 0)} />
        </div>

        {facts.مواد_خطرة_متسربة && (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
            ⚠ تسرّب مواد خطرة في هذا الحادث
          </div>
        )}

        {parsed.people.length > 0 && (
          <div>
            <div className="mb-1.5 text-xs font-medium text-slate-400">الأطراف المتورطة</div>
            <div className="flex flex-wrap items-start gap-2">
              {parsed.people.map((p, i) => {
                const extra = [
                  p.roleDetail,
                  p.gender && (GENDER_LABELS[p.gender] ?? p.gender),
                  p.ageRange && (AGE_LABELS[p.ageRange] ?? p.ageRange),
                  p.injuryType && (INJURY_LABELS[p.injuryType] ?? p.injuryType),
                  p.occupation,
                ].filter(Boolean);
                return (
                  <div
                    key={i}
                    className="rounded-lg border border-white/8 bg-white/[0.02] px-2.5 py-1.5 text-xs text-slate-300"
                  >
                    <div className="font-medium text-slate-200">
                      {p.name || 'غير معروف'}
                      {p.license && <span className="text-slate-500"> · رخصة {p.license}</span>}
                    </div>
                    {extra.length > 0 && <div className="mt-0.5 text-slate-500">{extra.join(' · ')}</div>}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {parsed.keywords.length > 0 && (
          <div className="flex flex-wrap items-start gap-1.5">
            {parsed.keywords.map((k) => (
              <span key={k} className="rounded-full bg-cyan-500/10 px-2 py-0.5 text-[11px] text-cyan-300">
                #{k}
              </span>
            ))}
          </div>
        )}

        <details className="rounded-xl border border-white/8 p-3 text-sm text-slate-300">
          <summary className="cursor-pointer text-xs font-medium text-slate-400">النص الأصلي للبلاغ</summary>
          <p className="mt-2 leading-relaxed whitespace-pre-wrap">{event.event_summary}</p>
        </details>

        <div className="grid grid-cols-2 items-start gap-2 border-t border-white/8 pt-3 text-[11px] text-slate-500 sm:grid-cols-4">
          {parsed.reportedBy && (
            <div>
              <span className="text-slate-600">أُبلغ من: </span>
              {parsed.reportedBy}
            </div>
          )}
          {parsed.verifiedBy && (
            <div>
              <span className="text-slate-600">تحقق منه: </span>
              {parsed.verifiedBy}
            </div>
          )}
          <div>
            <span className="text-slate-600">تاريخ التسجيل: </span>
            {formatDateTime(event.created_at)}
          </div>
          {parsed.confidence !== null && (
            <div>
              <span className="text-slate-600">دقة التصنيف الآلي: </span>
              {(parsed.confidence * 100).toFixed(1)}%
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}
