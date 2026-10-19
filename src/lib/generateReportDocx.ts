import {
  AlignmentType,
  BorderStyle,
  Document,
  HeadingLevel,
  Packer,
  Paragraph,
  Table,
  TableCell,
  TableRow,
  TextRun,
  WidthType,
} from 'docx';
import { saveAs } from 'file-saver';
import type { CountRow, ReportData, TimeBucketRow } from './reportData';
import { formatNumber } from './format';

const FONT = 'Arial'; // widely available, renders Arabic correctly across platforms
const CELL_BORDER = { style: BorderStyle.SINGLE, size: 2, color: 'CCCCCC' };
const CELL_BORDERS = { top: CELL_BORDER, bottom: CELL_BORDER, left: CELL_BORDER, right: CELL_BORDER };

function heading(text: string) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    alignment: AlignmentType.RIGHT,
    bidirectional: true,
    spacing: { before: 300, after: 120 },
    children: [new TextRun({ text, font: FONT, bold: true })],
  });
}

function para(text: string, opts: { bold?: boolean; size?: number } = {}) {
  return new Paragraph({
    alignment: AlignmentType.RIGHT,
    bidirectional: true,
    spacing: { after: 80 },
    children: [new TextRun({ text, font: FONT, bold: opts.bold, size: opts.size })],
  });
}

function cell(text: string, opts: { header?: boolean; width?: number } = {}) {
  return new TableCell({
    borders: CELL_BORDERS,
    width: opts.width ? { size: opts.width, type: WidthType.PERCENTAGE } : undefined,
    shading: opts.header ? { fill: 'E8ECF3' } : undefined,
    children: [
      new Paragraph({
        alignment: AlignmentType.RIGHT,
        bidirectional: true,
        children: [new TextRun({ text, font: FONT, bold: opts.header, size: 20 })],
      }),
    ],
  });
}

function countTable(rows: CountRow[], nameHeader: string, countHeader = 'العدد'): (Table | Paragraph)[] {
  if (rows.length === 0) return [para('لا توجد بيانات (لا قيم أكبر من صفر)', { size: 18 })];
  return [
    new Table({
      width: { size: 100, type: WidthType.PERCENTAGE },
      rows: [
        new TableRow({ children: [cell(nameHeader, { header: true, width: 70 }), cell(countHeader, { header: true, width: 30 })] }),
        ...rows.map(
          (r) => new TableRow({ children: [cell(r.name), cell(formatNumber(r.count))] }),
        ),
      ],
    }),
  ];
}

function locationSection(title: string, breakdown: ReportData['byLocationIncidents']): (Paragraph | Table)[] {
  return [
    heading(title),
    para('الإقليم', { bold: true, size: 18 }),
    ...countTable(breakdown.region, 'الإقليم'),
    para('المنطقة', { bold: true, size: 18 }),
    ...countTable(breakdown.area, 'المنطقة'),
    para('المعتمدية', { bold: true, size: 18 }),
    ...countTable(breakdown.delegation, 'المعتمدية'),
    para('العمادة', { bold: true, size: 18 }),
    ...countTable(breakdown.imada, 'العمادة'),
  ];
}

function timeTable(rows: TimeBucketRow[], firstColHeader: string): (Table | Paragraph)[] {
  if (rows.length === 0) return [para('لا توجد بيانات', { size: 18 })];
  return [
    new Table({
      width: { size: 100, type: WidthType.PERCENTAGE },
      rows: [
        new TableRow({
          children: [
            cell(firstColHeader, { header: true, width: 25 }),
            cell('عدد الحوادث', { header: true, width: 25 }),
            cell('عدد القتلى', { header: true, width: 25 }),
            cell('عدد الجرحى', { header: true, width: 25 }),
          ],
        }),
        ...rows.map(
          (r) =>
            new TableRow({
              children: [
                cell(r.label),
                cell(formatNumber(r.count)),
                cell(formatNumber(r.deaths)),
                cell(formatNumber(r.injuries)),
              ],
            }),
        ),
      ],
    }),
  ];
}

function combinationTable(matrix: ReportData['regionHourMatrix']): (Table | Paragraph)[] {
  if (matrix.length === 0) return [para('لا توجد بيانات كافية (يتطلب موقع وتوقيت محددين)', { size: 18 })];
  const hourCols = Array.from({ length: 24 }, (_, h) => h);
  return [
    new Table({
      width: { size: 100, type: WidthType.PERCENTAGE },
      rows: [
        new TableRow({
          children: [
            cell('الإقليم', { header: true, width: 10 }),
            ...hourCols.map((h) => cell(String(h), { header: true, width: 3.75 })),
          ],
        }),
        ...matrix.map(
          ({ region, hours }) =>
            new TableRow({
              children: [cell(region), ...hours.map((c) => cell(c > 0 ? formatNumber(c) : '-'))],
            }),
        ),
      ],
    }),
  ];
}

export async function generateReportDocx(data: ReportData) {
  const children: (Paragraph | Table)[] = [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      bidirectional: true,
      spacing: { after: 200 },
      children: [new TextRun({ text: 'تقرير أحداث محرك بحث حسب الفترة', font: FONT, bold: true, size: 32 })],
    }),
    para(`فترة زمنية: ${data.periodLabel}`, { bold: true }),

    heading('إحصائيات عامة'),
    ...countTable(
      [
        { name: 'عدد الحوادث', count: data.general.count },
        { name: 'عدد القتلى', count: data.general.deaths },
        { name: 'عدد الجرحى', count: data.general.injuries },
      ],
      'المؤشر',
    ),

    ...locationSection('توزيع الحوادث حسب المكان', data.byLocationIncidents),
    ...locationSection('توزيع القتلى حسب المكان', data.byLocationDeaths),
    ...locationSection('توزيع الجرحى حسب المكان', data.byLocationInjuries),

    heading('توزيع الحوادث حسب أنواع الطرقات'),
    ...countTable(data.byRoadType, 'نوع الطريق'),

    heading('توزيع الحوادث حسب الأسباب'),
    ...countTable(data.byCause, 'السبب'),

    heading('توزيع الحوادث حسب أيام الأسبوع'),
    ...timeTable(data.byDayOfWeek, 'اليوم'),

    heading('توزيع الحوادث حسب ساعات اليوم'),
    ...timeTable(data.byHourOfDay, 'الساعة'),

    heading('Combinaison (اليوم / الساعة / المنطقة)'),
    para('أعلى 10 أقاليم نشاطًا حسب ساعة اليوم', { size: 18 }),
    ...combinationTable(data.regionHourMatrix),

    heading('توزيع الحوادث حسب الأطراف المتداخلة'),
    ...(data.partyTypeCoverage < 1
      ? [
          para(
            `ملاحظة: بيانات نوع الطرف متوفرة لـ ${Math.round(data.partyTypeCoverage * 100)}% فقط من حوادث هذه الفترة (الحقل أُضيف لاحقًا للاستخراج الآلي؛ الحوادث الأقدم لا تحمله).`,
            { size: 16 },
          ),
        ]
      : []),
    ...countTable(data.byPartyType, 'نوع الطرف'),

    new Paragraph({
      alignment: AlignmentType.RIGHT,
      bidirectional: true,
      spacing: { before: 300 },
      children: [
        new TextRun({
          text: 'ملاحظة: يتم عرض النتائج فقط للقيم الأكبر من صفر.',
          font: FONT,
          italics: true,
          size: 18,
        }),
      ],
    }),
  ];

  const doc = new Document({
    sections: [{ children }],
  });

  const blob = await Packer.toBlob(doc);
  const stamp = new Date().toISOString().slice(0, 10);
  saveAs(blob, `تقرير_حوادث_المرور_${stamp}.docx`);
}
