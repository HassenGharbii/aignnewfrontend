import { useMemo, useState } from 'react';
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from '@tanstack/react-table';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { useFilters } from '../../context/FiltersContext';
import type { ParsedEvent } from '../../lib/parseEvent';
import { formatDate, formatNumber, truncate } from '../../lib/format';
import { severityTone, statusTone } from '../../lib/severity';
import { downloadCsv } from '../../lib/exportCsv';
import { EventDetailModal } from './EventDetailModal';

const columnHelper = createColumnHelper<ParsedEvent>();

const columns = [
  columnHelper.accessor((e) => e.eventDate?.getTime() ?? 0, {
    id: 'date',
    header: 'التاريخ',
    cell: (ctx) => formatDate(ctx.row.original.eventDate),
  }),
  columnHelper.accessor('event_title', {
    header: 'الحادث',
    cell: (ctx) => {
      const pending = ctx.row.original.parsed.verificationStatus?.includes('انتظار');
      return (
        <span className="inline-flex items-center gap-1.5">
          {pending && (
            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400" title="قيد التحقق" />
          )}
          <span className="font-medium text-slate-200">
            {truncate(ctx.getValue() || ctx.row.original.event_summary, 56)}
          </span>
        </span>
      );
    },
  }),
  columnHelper.accessor((e) => e.governorate?.ar ?? e.region, {
    id: 'region',
    header: 'المنطقة',
  }),
  columnHelper.accessor('sub_category', {
    header: 'السبب/النوع',
    cell: (ctx) => (ctx.getValue() ? truncate(ctx.getValue() as string, 30) : '—'),
  }),
  columnHelper.accessor('severity', {
    header: 'الخطورة',
    cell: (ctx) => <Badge label={ctx.getValue()} tone={severityTone(ctx.getValue())} />,
  }),
  columnHelper.accessor('event_status', {
    header: 'الحالة',
    cell: (ctx) => <Badge label={ctx.getValue()} tone={statusTone(ctx.getValue())} />,
  }),
  columnHelper.accessor('priority', {
    header: 'الأولوية',
    cell: (ctx) => (ctx.getValue() ? ctx.getValue() : '—'),
  }),
  columnHelper.accessor((e) => e.parsed.facts.عدد_الوفيات ?? 0, {
    id: 'deaths',
    header: 'قتلى',
    cell: (ctx) => formatNumber(ctx.getValue()),
  }),
  columnHelper.accessor((e) => e.parsed.facts.عدد_الإصابات ?? 0, {
    id: 'injuries',
    header: 'جرحى',
    cell: (ctx) => formatNumber(ctx.getValue()),
  }),
];

function exportEvents(events: ParsedEvent[]) {
  const header = ['التاريخ', 'العنوان', 'المنطقة', 'السبب/النوع', 'الخطورة', 'الحالة', 'الأولوية', 'قتلى', 'جرحى', 'مركبات'];
  const rows = events.map((e) => [
    formatDate(e.eventDate),
    e.event_title || e.event_summary,
    e.governorate?.ar ?? e.region,
    e.sub_category ?? '',
    e.severity,
    e.event_status,
    e.priority,
    String(e.parsed.facts.عدد_الوفيات ?? 0),
    String(e.parsed.facts.عدد_الإصابات ?? 0),
    String(e.parsed.facts.عدد_المركبات ?? 0),
  ]);
  downloadCsv(`حوادث_المرور_${events.length}.csv`, header, rows);
}

export function EventsTable() {
  const { filteredEvents, isLoading, isError } = useFilters();
  const [sorting, setSorting] = useState<SortingState>([{ id: 'date', desc: true }]);
  const [selected, setSelected] = useState<ParsedEvent | null>(null);

  const data = useMemo(() => filteredEvents, [filteredEvents]);

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 10 } },
  });

  return (
    <section id="events" className="scroll-mt-20">
      <Card
        title={`سجل الحوادث (${formatNumber(filteredEvents.length)})`}
        subtitle="اضغط على أي صف لعرض التفاصيل الكاملة"
        action={
          filteredEvents.length > 0 && (
            <button
              onClick={() => exportEvents(filteredEvents)}
              className="flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.02] px-3 py-1.5 text-xs text-slate-300 transition hover:border-cyan-500/40 hover:text-cyan-300"
            >
              ⬇ تصدير CSV
            </button>
          )
        }
      >
        {isLoading && <p className="py-10 text-center text-sm text-slate-400">جاري التحميل…</p>}
        {isError && (
          <p className="py-10 text-center text-sm text-rose-400">
            تعذّر الاتصال بالـ API على localhost:9911 — تأكد من تشغيله.
          </p>
        )}
        {!isLoading && !isError && (
          <>
            <div className="overflow-x-auto rounded-2xl">
              <table className="w-full text-right text-xs">
                <thead>
                  <tr className="text-slate-500">
                    {table.getHeaderGroups().map((hg) =>
                      hg.headers.map((header) => (
                        <th
                          key={header.id}
                          onClick={header.column.getToggleSortingHandler()}
                          className="cursor-pointer select-none whitespace-nowrap border-b border-white/8 bg-white/[0.02] px-3 py-3 text-[11px] font-semibold uppercase tracking-wide hover:text-slate-300"
                        >
                          <span className="inline-flex items-center gap-1">
                            {flexRender(header.column.columnDef.header, header.getContext())}
                            <span className="text-cyan-400">
                              {header.column.getIsSorted() === 'asc' && '▲'}
                              {header.column.getIsSorted() === 'desc' && '▼'}
                            </span>
                          </span>
                        </th>
                      )),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {table.getRowModel().rows.map((row, i) => (
                    <tr
                      key={row.id}
                      onClick={() => setSelected(row.original)}
                      className={`cursor-pointer border-b border-white/6 transition hover:bg-cyan-500/[0.06] ${
                        i % 2 === 1 ? 'bg-white/[0.015]' : ''
                      }`}
                    >
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="px-3 py-3 text-slate-300">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {table.getRowModel().rows.length === 0 && (
                <p className="py-10 text-center text-sm text-slate-500">لا توجد حوادث مطابقة للتصفية الحالية</p>
              )}
            </div>

            <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
              <div>
                صفحة <span className="font-semibold text-slate-200">{table.getState().pagination.pageIndex + 1}</span> من{' '}
                {Math.max(1, table.getPageCount())}
              </div>
              <div className="flex gap-1.5">
                <button
                  onClick={() => table.previousPage()}
                  disabled={!table.getCanPreviousPage()}
                  className="rounded-lg border border-white/10 px-3 py-1.5 transition hover:border-white/20 hover:text-white disabled:opacity-30"
                >
                  السابق
                </button>
                <button
                  onClick={() => table.nextPage()}
                  disabled={!table.getCanNextPage()}
                  className="rounded-lg border border-white/10 px-3 py-1.5 transition hover:border-white/20 hover:text-white disabled:opacity-30"
                >
                  التالي
                </button>
              </div>
            </div>
          </>
        )}
      </Card>

      <EventDetailModal event={selected} onClose={() => setSelected(null)} />
    </section>
  );
}
