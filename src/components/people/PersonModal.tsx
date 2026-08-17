import { Modal } from '../ui/Modal';
import { Badge } from '../ui/Badge';
import type { PersonResult } from '../../api/types';
import { formatDateTime } from '../../lib/format';
import { severityTone } from '../../lib/severity';

function InfoBox({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2">
      <div className="text-[11px] text-slate-500">{label}</div>
      <div className={`mt-0.5 text-sm font-semibold ${highlight ? 'text-cyan-300' : 'text-slate-100'}`}>{value}</div>
    </div>
  );
}

export function PersonModal({ person, onClose }: { person: PersonResult | null; onClose: () => void }) {
  if (!person) return <Modal open={false} onClose={onClose} title="" />;

  const extraFields: Array<[string, string | null]> = [
    ['اللقب', person.nickname],
    ['الهاتف', person.phone],
    ['العنوان', person.address],
    ['المهنة', person.occupation],
    ['السجل العدلي', person.criminal_record],
  ];
  const presentExtras = extraFields.filter(([, v]) => Boolean(v)) as Array<[string, string]>;

  return (
    <Modal open={Boolean(person)} onClose={onClose} title={person.name || 'شخص غير معروف'}>
      <div className="space-y-4">
        <div className="grid grid-cols-2 items-start gap-2 sm:grid-cols-4">
          <InfoBox label="CIN" value={person.cin || '—'} />
          <InfoBox
            label="الجنس"
            value={person.gender === 'male' ? 'ذكر' : person.gender === 'female' ? 'أنثى' : '—'}
          />
          <InfoBox label="الفئة العمرية" value={person.age_range || '—'} />
          <InfoBox label="عدد الحوادث" value={String(person.event_count)} highlight />
        </div>

        {presentExtras.length > 0 && (
          <div className="grid grid-cols-2 items-start gap-2 sm:grid-cols-4">
            {presentExtras.map(([label, value]) => (
              <InfoBox key={label} label={label} value={value} />
            ))}
          </div>
        )}

        {person.risk_level && person.risk_level !== 'unknown' && (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
            مستوى الخطورة: {person.risk_level}
          </div>
        )}

        <div>
          <div className="mb-2 text-xs font-medium text-slate-400">سجل الحوادث المرتبطة</div>
          <div className="space-y-2">
            {person.history.map((h) => (
              <div key={h.record_id} className="rounded-xl border border-white/8 bg-white/[0.02] p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-slate-100">{h.event_title}</span>
                  <Badge label={h.event_severity} tone={severityTone(h.event_severity)} />
                  <span className="text-[11px] text-slate-500">
                    {formatDateTime(h.event_datetime)} · {h.event_region}
                  </span>
                </div>
                {h.role_detail && <div className="mt-1 text-xs text-slate-400">الدور: {h.role_detail}</div>}
                <p className="mt-1.5 text-xs leading-relaxed text-slate-300">{h.event_summary}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Modal>
  );
}
