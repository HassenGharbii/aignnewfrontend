import { TONE_CLASSES, TONE_DOT, type SeverityTone } from '../../lib/severity';

export function Badge({ label, tone }: { label: string; tone: SeverityTone }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium whitespace-nowrap ${TONE_CLASSES[tone]}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${TONE_DOT[tone]}`} />
      {label}
    </span>
  );
}
