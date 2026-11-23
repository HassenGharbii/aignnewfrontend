import ExcelJS from 'exceljs';
import { saveAs } from 'file-saver';
import type { ParsedEvent } from './parseEvent';
import type { CountRow, ReportData } from './reportData';
import { formatDate } from './format';

function styleHeaderRow(row: ExcelJS.Row) {
  row.font = { bold: true };
  row.eachCell((c) => {
    c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE8ECF3' } };
    c.alignment = { horizontal: 'right' };
  });
}

function addEventsSheet(workbook: ExcelJS.Workbook, events: ParsedEvent[]) {
  const sheet = workbook.addWorksheet('الأحداث', { views: [{ rightToLeft: true }] });
  sheet.columns = [
    { header: 'التاريخ', key: 'date', width: 14 },
    { header: 'العنوان', key: 'title', width: 40 },
    { header: 'الولاية', key: 'gov', width: 14 },
    { header: 'المنطقة', key: 'area', width: 16 },
    { header: 'المعتمدية', key: 'delegation', width: 16 },
    { header: 'العمادة', key: 'imada', width: 16 },
    { header: 'السبب/النوع', key: 'sub', width: 30 },
    { header: 'الخطورة', key: 'severity', width: 12 },
    { header: 'الحالة', key: 'status', width: 12 },
    { header: 'نوع الحادث', key: 'incidentType', width: 24 },
    { header: 'نوع الطريق', key: 'roadType', width: 20 },
    { header: 'حالة الطريق', key: 'roadCondition', width: 20 },
    { header: 'قتلى', key: 'deaths', width: 8 },
    { header: 'جرحى', key: 'injuries', width: 8 },
    { header: 'مركبات', key: 'vehicles', width: 8 },
    { header: 'مواد خطرة', key: 'hazmat', width: 10 },
    { header: 'أنواع الأطراف', key: 'parties', width: 30 },
    { header: 'السائقون', key: 'drivers', width: 30 },
    { header: 'كلمات مفتاحية', key: 'keywords', width: 30 },
    { header: 'المصدر', key: 'source', width: 20 },
    { header: 'النص الأصلي', key: 'summary', width: 60 },
  ];
  styleHeaderRow(sheet.getRow(1));

  for (const e of events) {
    sheet.addRow({
      date: formatDate(e.eventDate),
      title: e.event_title || e.event_summary,
      gov: e.governorate?.ar ?? e.region,
      area: e.parsed.locationArea,
      delegation: e.parsed.locationDelegation,
      imada: e.parsed.locationImada,
      sub: e.sub_category ?? '',
      severity: e.severity,
      status: e.event_status,
      incidentType: e.parsed.facts.نوع_الحادث ?? '',
      roadType: e.parsed.facts.نوع_الطريق ?? '',
      roadCondition: e.parsed.facts.حالة_الطريق ?? '',
      deaths: e.parsed.facts.عدد_الوفيات ?? 0,
      injuries: e.parsed.facts.عدد_الإصابات ?? 0,
      vehicles: e.parsed.facts.عدد_المركبات ?? 0,
      hazmat: e.parsed.facts.مواد_خطرة_متسربة ? 'نعم' : 'لا',
      parties: e.parsed.partyTypes.join('، '),
      drivers: e.parsed.people.map((p) => p.name).filter(Boolean).join('، '),
      keywords: e.parsed.keywords.join('، '),
      source: e.source,
      summary: e.event_summary,
    });
  }

  for (const row of sheet.getRows(2, sheet.rowCount) ?? []) {
    row.eachCell((c) => {
      c.alignment = { horizontal: 'right', wrapText: true, vertical: 'top' };
    });
  }
}

function addCountSheet(workbook: ExcelJS.Workbook, name: string, nameHeader: string, rows: CountRow[]) {
  const sheet = workbook.addWorksheet(name, { views: [{ rightToLeft: true }] });
  sheet.columns = [
    { header: nameHeader, key: 'name', width: 30 },
    { header: 'العدد', key: 'count', width: 12 },
  ];
  styleHeaderRow(sheet.getRow(1));
  for (const r of rows) sheet.addRow(r);
}

function addSummarySheet(workbook: ExcelJS.Workbook, data: ReportData) {
  const sheet = workbook.addWorksheet('ملخص', { views: [{ rightToLeft: true }] });
  sheet.columns = [
    { header: 'المؤشر', key: 'name', width: 30 },
    { header: 'القيمة', key: 'value', width: 16 },
  ];
  styleHeaderRow(sheet.getRow(1));
  sheet.addRow({ name: 'الفترة الزمنية', value: data.periodLabel });
  sheet.addRow({ name: 'عدد الحوادث', value: data.general.count });
  sheet.addRow({ name: 'عدد القتلى', value: data.general.deaths });
  sheet.addRow({ name: 'عدد الجرحى', value: data.general.injuries });
}

export async function generateReportExcel(events: ParsedEvent[], data: ReportData) {
  const workbook = new ExcelJS.Workbook();
  workbook.creator = 'لوحة مراقبة حوادث المرور';
  workbook.created = new Date();

  addSummarySheet(workbook, data);
  addEventsSheet(workbook, events);
  addCountSheet(workbook, 'حسب الولاية', 'الإقليم', data.byLocationIncidents.region);
  addCountSheet(workbook, 'حسب السبب', 'السبب', data.byCause);
  addCountSheet(workbook, 'حسب نوع الطريق', 'نوع الطريق', data.byRoadType);
  addCountSheet(workbook, 'حسب نوع الطرف', 'نوع الطرف', data.byPartyType);

  const buffer = await workbook.xlsx.writeBuffer();
  const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
  const stamp = new Date().toISOString().slice(0, 10);
  saveAs(blob, `بيانات_حوادث_المرور_${stamp}.xlsx`);
}
