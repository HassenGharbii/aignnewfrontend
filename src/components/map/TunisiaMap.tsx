import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { Feature, FeatureCollection, Geometry } from 'geojson';
import type { Layer, Path } from 'leaflet';
import { CircleMarker, GeoJSON, MapContainer, Pane, Popup } from 'react-leaflet';
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

type GovernorateBorders = FeatureCollection<Geometry, { ar: string }>;

/** The 24 governorate borders, served from public/ so the map needs no tile server or internet access.
 * Built from geoBoundaries TUN ADM1 (simplified), which is OpenStreetMap data under the ODbL. */
const BORDERS_URL = `${import.meta.env.BASE_URL}geo/tunisia-governorates.geojson`;
const BORDERS_ATTRIBUTION = '&copy; OpenStreetMap contributors · geoBoundaries';
const BORDER_COLOR = '#24304a'; // --color-border
const BORDER_HOVER_COLOR = '#cbd5e1';

/** Sequential ramp, one hue (the dashboard cyan): dark = few incidents, bright = many. */
const COUNT_RAMP = ['#083344', '#155e75', '#0e7490', '#0891b2', '#22d3ee'];

interface CountClass {
  from: number;
  to: number;
  color: string;
}

/**
 * Up to five classes holding roughly the same number of governorates each.
 * Counts are heavily skewed toward Greater Tunis, so equal-width ranges would
 * paint nearly every other governorate the same darkest shade.
 */
function countClasses(counts: number[]): CountClass[] {
  const sorted = counts.filter((c) => c > 0).sort((a, b) => a - b);
  if (sorted.length === 0) return [];
  const bounds = [
    ...new Set(
      Array.from({ length: COUNT_RAMP.length }, (_, k) => sorted[Math.ceil(((k + 1) * sorted.length) / COUNT_RAMP.length) - 1]),
    ),
  ];
  return bounds.map((to, i) => ({
    from: i === 0 ? sorted[0] : bounds[i - 1] + 1,
    to,
    // Spread fewer classes across the whole ramp so the brightest step always means "most".
    color: COUNT_RAMP[bounds.length === 1 ? COUNT_RAMP.length - 1 : Math.round((i * (COUNT_RAMP.length - 1)) / (bounds.length - 1))],
  }));
}

/** The governorate fill already encodes the count, so the dot only marks the dominant severity at a fixed size. */
const SEVERITY_DOT_RADIUS = 7;

/** Mainland Tunisia plus Djerba and the Kerkennah islands, padded slightly. */
const TUNISIA_BOUNDS: [[number, number], [number, number]] = [
  [30.1, 7.4],
  [37.6, 11.7],
];

export function TunisiaMap() {
  const { filteredEvents } = useFilters();

  const stats = useMemo(() => aggregate(filteredEvents), [filteredEvents]);
  const unmatchedCount = useMemo(
    () => filteredEvents.filter((e) => !e.governorate).length,
    [filteredEvents],
  );

  const { data: borders } = useQuery({
    queryKey: ['tunisia-governorate-borders'],
    queryFn: async (): Promise<GovernorateBorders> => {
      const res = await fetch(BORDERS_URL);
      if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${BORDERS_URL}`);
      return res.json() as Promise<GovernorateBorders>;
    },
    staleTime: Infinity,
  });

  const countByGov = useMemo(() => new Map(stats.map((s) => [s.ar, s.count])), [stats]);
  const classes = useMemo(() => countClasses(stats.map((s) => s.count)), [stats]);

  const bordersLayer = useMemo(() => {
    if (!borders) return null;
    const styleFor = (feature?: Feature<Geometry, { ar: string }>) => {
      const count = (feature && countByGov.get(feature.properties.ar)) ?? 0;
      const color = classes.find((c) => count <= c.to)?.color;
      return {
        color: BORDER_COLOR,
        weight: 1,
        fillColor: color ?? 'transparent',
        fillOpacity: count > 0 && color ? 0.85 : 0,
      };
    };
    const onEachFeature = (feature: Feature<Geometry, { ar: string }>, layer: Layer) => {
      const count = countByGov.get(feature.properties.ar) ?? 0;
      layer.bindTooltip(`${feature.properties.ar} · ${formatNumber(count)} حادث`, { sticky: true, direction: 'top' });
      layer.on({
        mouseover: () => (layer as Path).setStyle({ color: BORDER_HOVER_COLOR, weight: 2 }),
        mouseout: () => (layer as Path).setStyle(styleFor(feature)),
      });
    };
    // react-leaflet's GeoJSON doesn't restyle on prop changes, so the key forces a rebuild when the counts change.
    const key = stats.map((s) => `${s.ar}:${s.count}`).join('|');
    return (
      <GeoJSON key={key} data={borders} style={styleFor} onEachFeature={onEachFeature} attribution={BORDERS_ATTRIBUTION} />
    );
  }, [borders, countByGov, classes, stats]);

  return (
    <section id="map" className="scroll-mt-20">
      <Card
        title="التوزيع الجغرافي للحوادث"
        subtitle="عرض جغرافي — للتصفية حسب الموقع استخدم الإقليم/المنطقة أعلاه"
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
            bounds={TUNISIA_BOUNDS}
            zoomSnap={0.25}
            scrollWheelZoom
            style={{ height: '100%', width: '100%' }}
          >
            {/* Below the default overlay pane (z-index 400), so the severity circles stay clickable on top. */}
            <Pane name="governorate-borders" style={{ zIndex: 350 }}>
              {bordersLayer}
            </Pane>
            {stats.map((s) => (
              <CircleMarker
                key={s.ar}
                center={[s.lat, s.lon]}
                radius={SEVERITY_DOT_RADIUS}
                pathOptions={{
                  color: '#0a0f1a', // surface-coloured ring separates the dot from the governorate fill
                  weight: 2,
                  fillColor: TONE_HEX[s.dominantTone],
                  fillOpacity: 0.95,
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
                  </div>
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>
        {classes.length > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[11px] text-slate-400">
            <span className="text-slate-500">عدد الحوادث بالولاية:</span>
            {classes.map((c) => (
              <span key={c.color} className="flex items-center gap-1.5">
                <span className="h-2.5 w-4 rounded-sm" style={{ background: c.color }} />
                <bdi dir="ltr">
                  {c.from === c.to ? formatNumber(c.from) : `${formatNumber(c.from)}–${formatNumber(c.to)}`}
                </bdi>
              </span>
            ))}
          </div>
        )}
        <p className="mt-2 text-[11px] text-slate-500">
          لون الولاية يعكس عدد الحوادث، ولون النقطة يعكس الخطورة الغالبة (اضغط للتفاصيل) · عدد الولايات المتأثرة:{' '}
          {stats.length}
        </p>
      </Card>
    </section>
  );
}
