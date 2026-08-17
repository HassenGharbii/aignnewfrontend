import { useMemo } from 'react';
import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet';
import { Card } from '../ui/Card';
import { useFilters } from '../../context/FiltersContext';
import { GOVERNORATES } from '../../data/governorates';
import { severityTone, TONE_HEX } from '../../lib/severity';
import { formatNumber } from '../../lib/format';
import type { ParsedEvent } from '../../lib/parseEvent';

interface GovStat {
  ar: string;
  fr: string;
  lat: number;
  lon: number;
  count: number;
  deaths: number;
  injuries: number;
  dominantTone: 'danger' | 'warning' | 'success' | 'neutral';
}

function aggregate(events: ParsedEvent[]): GovStat[] {
  const byGov = new Map<string, ParsedEvent[]>();
  for (const e of events) {
    if (!e.governorate) continue;
    const list = byGov.get(e.governorate.ar) ?? [];
    list.push(e);
    byGov.set(e.governorate.ar, list);
  }

  return GOVERNORATES.map((g) => {
    const list = byGov.get(g.ar) ?? [];
    let deaths = 0;
    let injuries = 0;
    const toneCounts: Record<string, number> = { danger: 0, warning: 0, success: 0, neutral: 0 };
    for (const e of list) {
      deaths += e.parsed.facts.عدد_الوفيات ?? 0;
      injuries += e.parsed.facts.عدد_الإصابات ?? 0;
      toneCounts[severityTone(e.severity)] += 1;
    }
    const dominantTone = (Object.entries(toneCounts).sort((a, b) => b[1] - a[1])[0]?.[0] ??
      'neutral') as GovStat['dominantTone'];
    return { ar: g.ar, fr: g.fr, lat: g.lat, lon: g.lon, count: list.length, deaths, injuries, dominantTone };
  }).filter((g) => g.count > 0);
}

function radiusFor(count: number, max: number): number {
  if (max <= 0) return 6;
  const min = 8;
  const maxR = 34;
  return min + (maxR - min) * Math.sqrt(count / max);
}

export function TunisiaMap() {
  const { filteredEvents, filters, setGovernorate } = useFilters();

  const stats = useMemo(() => aggregate(filteredEvents), [filteredEvents]);
  const maxCount = useMemo(() => Math.max(1, ...stats.map((s) => s.count)), [stats]);
  const unmatchedCount = useMemo(
    () => filteredEvents.filter((e) => !e.governorate).length,
    [filteredEvents],
  );

  return (
    <section id="map" className="scroll-mt-20">
      <Card
        title="التوزيع الجغرافي للحوادث"
        subtitle="اضغط دائرة الولاية للتصفية"
        action={
          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2.5 sm:flex">
              {(['danger', 'warning', 'success'] as const).map((tone) => (
                <span key={tone} className="flex items-center gap-1 text-[11px] text-slate-500">
                  <span className="h-2 w-2 rounded-full" style={{ background: TONE_HEX[tone] }} />
                  {tone === 'danger' ? 'مرتفعة' : tone === 'warning' ? 'متوسطة' : 'منخفضة'}
                </span>
              ))}
            </div>
            {unmatchedCount > 0 && (
              <span className="text-[11px] text-slate-500">{formatNumber(unmatchedCount)} حادث بدون موقع محدد</span>
            )}
          </div>
        }
      >
        <div className="h-[440px] overflow-hidden rounded-2xl ring-1 ring-white/8" dir="ltr">
          <MapContainer
            center={[34.4, 9.5]}
            zoom={6.3}
            scrollWheelZoom
            style={{ height: '100%', width: '100%' }}
          >
            <TileLayer
              attribution='&copy; OpenStreetMap contributors &copy; CARTO'
              url={import.meta.env.VITE_MAP_TILE_URL}
            />
            {stats.map((s) => {
              const isFiltered = filters.governorates.size > 0;
              const isActive = filters.governorates.has(s.ar);
              return (
                <CircleMarker
                  key={s.ar}
                  center={[s.lat, s.lon]}
                  radius={radiusFor(s.count, maxCount)}
                  pathOptions={{
                    color: isActive ? '#22d3ee' : TONE_HEX[s.dominantTone],
                    weight: isActive ? 3 : 1.5,
                    fillColor: TONE_HEX[s.dominantTone],
                    fillOpacity: isFiltered && !isActive ? 0.15 : 0.55,
                  }}
                  eventHandlers={{
                    click: () => setGovernorate(isActive ? null : s.ar),
                  }}
                >
                  <Popup>
                    <div className="min-w-[190px] text-sm">
                      <div className="flex items-center gap-2">
                        <span className="h-2.5 w-2.5 rounded-full" style={{ background: TONE_HEX[s.dominantTone] }} />
                        <span className="font-bold text-slate-100">{s.ar}</span>
                      </div>
                      <div className="mt-0.5 text-xs text-slate-400">{s.fr}</div>
                      <div className="mt-2.5 grid grid-cols-3 items-start gap-1.5 text-center">
                        <div className="rounded-lg bg-white/5 py-1.5">
                          <div className="text-sm font-bold text-cyan-300">{formatNumber(s.count)}</div>
                          <div className="text-[10px] text-slate-500">حوادث</div>
                        </div>
                        <div className="rounded-lg bg-white/5 py-1.5">
                          <div className="text-sm font-bold text-rose-400">{formatNumber(s.deaths)}</div>
                          <div className="text-[10px] text-slate-500">قتلى</div>
                        </div>
                        <div className="rounded-lg bg-white/5 py-1.5">
                          <div className="text-sm font-bold text-amber-400">{formatNumber(s.injuries)}</div>
                          <div className="text-[10px] text-slate-500">جرحى</div>
                        </div>
                      </div>
                      <button
                        onClick={() => {
                          setGovernorate(s.ar);
                          document.getElementById('events')?.scrollIntoView({ behavior: 'smooth' });
                        }}
                        className="mt-2.5 w-full rounded-lg bg-cyan-500/15 px-2 py-1.5 text-xs font-medium text-cyan-300 transition hover:bg-cyan-500/25"
                      >
                        عرض الحوادث ←
                      </button>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}
          </MapContainer>
        </div>
        <p className="mt-2 text-[11px] text-slate-500">
          حجم الدائرة يعكس عدد الحوادث، واللون يعكس الخطورة الغالبة بالولاية · عدد الولايات المتأثرة: {stats.length}
        </p>
      </Card>
    </section>
  );
}
