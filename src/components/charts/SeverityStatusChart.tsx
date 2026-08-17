import { useMemo } from 'react';
import { Card } from '../ui/Card';
import { ProgressRows } from '../ui/ProgressRows';
import { useFilters } from '../../context/FiltersContext';
import { severityTone, statusTone, verificationTone, TONE_HEX } from '../../lib/severity';
import { countGrouped } from '../../lib/arabicText';

function useCounts(values: string[]) {
  return useMemo(() => countGrouped(values), [values]);
}

export function SeverityStatusChart() {
  const { filteredEvents, filters, toggleSeverity, toggleStatus, toggleVerification } = useFilters();

  const severityRows = useCounts(filteredEvents.map((e) => e.severity));
  const statusRows = useCounts(filteredEvents.map((e) => e.event_status));
  const verificationRows = useCounts(
    filteredEvents.map((e) => e.parsed.verificationStatus).filter((v): v is string => Boolean(v)),
  );

  return (
    <Card title="الخطورة والحالة والتحقق" subtitle="اضغط صفًا للتصفية">
      <div className="flex flex-col gap-5">
        <div>
          <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">درجة الخطورة</div>
          <ProgressRows
            rows={severityRows}
            active={filters.severities}
            onToggle={toggleSeverity}
            colorFor={(name) => TONE_HEX[severityTone(name)]}
          />
        </div>
        <div className="h-px bg-white/8" />
        <div>
          <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">حالة الحدث</div>
          <ProgressRows
            rows={statusRows}
            active={filters.statuses}
            onToggle={toggleStatus}
            colorFor={(name) => TONE_HEX[statusTone(name)]}
          />
        </div>
        {verificationRows.length > 0 && (
          <>
            <div className="h-px bg-white/8" />
            <div>
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                حالة التحقق من البلاغ
              </div>
              <ProgressRows
                rows={verificationRows}
                active={filters.verifications}
                onToggle={toggleVerification}
                colorFor={(name) => TONE_HEX[verificationTone(name)]}
              />
            </div>
          </>
        )}
      </div>
    </Card>
  );
}
