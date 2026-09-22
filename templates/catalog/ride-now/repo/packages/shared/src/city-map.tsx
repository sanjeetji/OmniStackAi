"use client";

import { useMemo, useRef, type MouseEvent } from "react";
import type { LatLng } from "./types.ts";

/**
 * A stylised map of Bengaluru drawn as SVG: lakes, parks, arterial roads and neighbourhood labels
 * from real coordinates, with no map tiles or API keys (so every preview works offline). Swap in
 * Google Maps or Mapbox later by replacing this component; the props stay the same.
 *
 * Colours come from CSS variables so each app can theme it:
 *   --map-land --map-water --map-park --map-road --map-road-major --map-label --map-route
 *   --map-pickup --map-drop --map-car --map-zone
 */

export interface MapMarker extends LatLng {
  id: string;
  kind: "pickup" | "drop" | "car" | "dot";
  heading?: number;
  label?: string;
  tone?: "default" | "busy" | "muted";
}

export interface MapZone extends LatLng {
  id: string;
  radiusKm: number;
  label?: string;
  surge?: number;
}

export interface CityMapProps {
  markers?: MapMarker[];
  route?: [LatLng, LatLng] | null;
  zones?: MapZone[];
  /** Points to keep in view; defaults to the markers. */
  focus?: LatLng[];
  onPick?: (point: LatLng) => void;
  className?: string;
  showLabels?: boolean;
  ariaLabel?: string;
}

const CITY: LatLng = { lat: 12.9716, lng: 77.5946 };
const KM_PER_DEG_LAT = 110.574;
const KM_PER_DEG_LNG = 111.32 * Math.cos((CITY.lat * Math.PI) / 180);

const LAKES: [number, number, number, number][] = [
  // lat, lng, radius-x km, radius-y km
  [13.045, 77.592, 0.55, 0.9], [12.983, 77.62, 0.45, 0.35], [12.934, 77.67, 1.6, 0.8], [12.939, 77.743, 1.0, 0.6],
  [12.909, 77.615, 0.5, 0.45], [13.009, 77.574, 0.3, 0.25], [12.923, 77.64, 0.45, 0.4], [13.068, 77.629, 0.5, 0.4],
  [12.848, 77.576, 0.6, 0.45], [13.001, 77.706, 0.5, 0.4],
];
const PARKS: [number, number, number, number][] = [[12.9763, 77.5929, 0.75, 0.9], [12.9507, 77.5848, 0.6, 0.55], [13.0068, 77.5917, 0.35, 0.3]];
const MAJOR_ROADS: [number, number][][] = [
  // Outer Ring Road (approximate)
  [[13.036, 77.59], [13.043, 77.626], [13.02, 77.647], [13.003, 77.678], [12.969, 77.701], [12.955, 77.701], [12.925, 77.678], [12.917, 77.638], [12.917, 77.605], [12.914, 77.575], [12.927, 77.535], [12.96, 77.518], [13.0, 77.52], [13.03, 77.542], [13.036, 77.59]],
  // Hosur Road to Electronic City
  [[12.958, 77.604], [12.935, 77.613], [12.917, 77.623], [12.89, 77.64], [12.845, 77.66], [12.8, 77.685]],
  // Bellary Road to the airport
  [[12.99, 77.585], [13.036, 77.59], [13.08, 77.598], [13.14, 77.62], [13.198, 77.707]],
  // Old Airport Road to Whitefield
  [[12.973, 77.61], [12.96, 77.648], [12.957, 77.7], [12.97, 77.73], [12.985, 77.75]],
  // Mysore Road
  [[12.965, 77.575], [12.955, 77.54], [12.94, 77.5]],
  // Tumkur Road
  [[12.99, 77.575], [13.025, 77.55], [13.05, 77.51]],
];
const MINOR_ROADS: [number, number][][] = [
  [[12.975, 77.607], [12.975, 77.64], [12.972, 77.66]], // MG Road / Indiranagar
  [[12.935, 77.624], [12.935, 77.66], [12.93, 77.69]], // Koramangala to Bellandur
  [[12.91, 77.69], [12.925, 77.68], [12.95, 77.66]], // Sarjapur Road
  [[12.95, 77.6], [12.92, 77.6], [12.89, 77.6], [12.85, 77.595]], // Bannerghatta Road
  [[12.925, 77.585], [12.95, 77.585], [12.975, 77.59]], // Jayanagar to the centre
  [[13.0, 77.57], [13.01, 77.595], [13.047, 77.621]], // Malleshwaram to Manyata
  [[12.98, 77.57], [12.98, 77.55], [12.985, 77.52]],
];
const LABELS: [string, number, number][] = [
  ["MG Road", 12.9756, 77.6066], ["Koramangala", 12.9352, 77.6245], ["Indiranagar", 12.9719, 77.6412], ["Whitefield", 12.9855, 77.731],
  ["Electronic City", 12.8452, 77.6602], ["HSR Layout", 12.9121, 77.6446], ["Jayanagar", 12.925, 77.5838], ["Hebbal", 13.0358, 77.597],
  ["Marathahalli", 12.9569, 77.7011], ["Majestic", 12.9784, 77.569], ["Malleshwaram", 13.0035, 77.5693], ["Bellandur", 12.926, 77.6762],
  ["BTM Layout", 12.9166, 77.6101], ["Yeshwanthpur", 13.0232, 77.55], ["KR Puram", 13.0003, 77.678], ["Airport", 13.1986, 77.7066],
  ["JP Nagar", 12.9063, 77.5857], ["Manyata", 13.0474, 77.6214], ["Domlur", 12.961, 77.6387], ["Banashankari", 12.9153, 77.5736],
];

/** Project to a local plane in km (x east, y south) around the city centre. */
function project(p: LatLng): { x: number; y: number } {
  return { x: (p.lng - CITY.lng) * KM_PER_DEG_LNG, y: (CITY.lat - p.lat) * KM_PER_DEG_LAT };
}

function unproject(x: number, y: number): LatLng {
  return { lat: CITY.lat - y / KM_PER_DEG_LAT, lng: CITY.lng + x / KM_PER_DEG_LNG };
}

function fit(points: LatLng[]): { x: number; y: number; w: number; h: number } {
  const ASPECT = 4 / 3;
  if (points.length === 0) return { x: -9, y: -6.75, w: 18, h: 13.5 };
  const xs = points.map((p) => project(p).x);
  const ys = points.map((p) => project(p).y);
  let minX = Math.min(...xs);
  let maxX = Math.max(...xs);
  let minY = Math.min(...ys);
  let maxY = Math.max(...ys);
  const pad = Math.max(1.2, Math.max(maxX - minX, maxY - minY) * 0.22);
  minX -= pad;
  maxX += pad;
  minY -= pad;
  maxY += pad;
  let w = Math.max(maxX - minX, 4);
  let h = Math.max(maxY - minY, 3);
  if (w / h > ASPECT) h = w / ASPECT;
  else w = h * ASPECT;
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;
  return { x: cx - w / 2, y: cy - h / 2, w, h };
}

const path = (points: [number, number][]) =>
  points.map(([lat, lng], i) => {
    const { x, y } = project({ lat, lng });
    return `${i === 0 ? "M" : "L"}${x.toFixed(3)} ${y.toFixed(3)}`;
  }).join(" ");

export function CityMap({ markers = [], route = null, zones = [], focus, onPick, className, showLabels = true, ariaLabel = "Map" }: CityMapProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const keep = focus ?? [...markers, ...(route ?? [])];
  const view = useMemo(() => fit(keep), [JSON.stringify(keep.map((p) => [p.lat.toFixed(3), p.lng.toFixed(3)]))]); // eslint-disable-line react-hooks/exhaustive-deps
  const unit = view.w / 100; // one hundredth of the view width, for sizes that should not scale with zoom

  function handleClick(event: MouseEvent<SVGSVGElement>) {
    if (!onPick || !svgRef.current) return;
    const svg = svgRef.current;
    const point = svg.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    const matrix = svg.getScreenCTM();
    if (!matrix) return;
    const local = point.matrixTransform(matrix.inverse());
    onPick(unproject(local.x, local.y));
  }

  const routePath = route
    ? (() => {
        const a = project(route[0]);
        const b = project(route[1]);
        const mx = (a.x + b.x) / 2 - (b.y - a.y) * 0.18;
        const my = (a.y + b.y) / 2 + (b.x - a.x) * 0.18;
        return `M${a.x} ${a.y} Q${mx} ${my} ${b.x} ${b.y}`;
      })()
    : null;

  return (
    <svg
      ref={svgRef}
      viewBox={`${view.x} ${view.y} ${view.w} ${view.h}`}
      className={className}
      role="img"
      aria-label={ariaLabel}
      onClick={handleClick}
      style={{ background: "var(--map-land, #EEF1EC)", cursor: onPick ? "crosshair" : "default", display: "block", width: "100%", height: "100%" }}
      preserveAspectRatio="xMidYMid slice"
    >
      <g>
        {PARKS.map(([lat, lng, rx, ry], i) => {
          const { x, y } = project({ lat, lng });
          return <ellipse key={`p${i}`} cx={x} cy={y} rx={rx} ry={ry} fill="var(--map-park, #D5E8CF)" />;
        })}
        {LAKES.map(([lat, lng, rx, ry], i) => {
          const { x, y } = project({ lat, lng });
          return <ellipse key={`l${i}`} cx={x} cy={y} rx={rx} ry={ry} fill="var(--map-water, #BFDDF2)" />;
        })}
        {MINOR_ROADS.map((r, i) => (
          <path key={`m${i}`} d={path(r)} fill="none" stroke="var(--map-road, #FFFFFF)" strokeWidth={unit * 0.9} strokeLinecap="round" strokeLinejoin="round" />
        ))}
        {MAJOR_ROADS.map((r, i) => (
          <path key={`r${i}`} d={path(r)} fill="none" stroke="var(--map-road-major, #FFE8A6)" strokeWidth={unit * 1.6} strokeLinecap="round" strokeLinejoin="round" />
        ))}
        {zones.map((zone) => {
          const { x, y } = project(zone);
          return (
            <g key={zone.id}>
              <circle cx={x} cy={y} r={zone.radiusKm} fill="var(--map-zone, rgba(245,158,11,0.14))" stroke="var(--map-zone-stroke, rgba(245,158,11,0.6))" strokeWidth={unit * 0.35} strokeDasharray={`${unit * 1.2} ${unit * 0.8}`} />
              {zone.surge && zone.surge > 1 ? (
                <text x={x} y={y - zone.radiusKm - unit * 0.8} textAnchor="middle" fontSize={unit * 3} fontWeight={700} fill="var(--map-zone-text, #B45309)">
                  {`${zone.label ?? ""} ${zone.surge.toFixed(2)}×`.trim()}
                </text>
              ) : null}
            </g>
          );
        })}
        {showLabels
          ? LABELS.map(([label, lat, lng]) => {
              const { x, y } = project({ lat, lng });
              return (
                <text key={label} x={x} y={y} textAnchor="middle" fontSize={unit * 2.4} fill="var(--map-label, #6B7280)" style={{ pointerEvents: "none", fontWeight: 500 }}>
                  {label}
                </text>
              );
            })
          : null}
        {routePath ? (
          <>
            <path d={routePath} fill="none" stroke="var(--map-route-halo, #FFFFFF)" strokeWidth={unit * 2.2} strokeLinecap="round" />
            <path d={routePath} fill="none" stroke="var(--map-route, #0B1B2B)" strokeWidth={unit * 1.1} strokeLinecap="round" />
          </>
        ) : null}
        {markers.map((marker) => (
          <Marker key={marker.id} marker={marker} unit={unit} />
        ))}
      </g>
    </svg>
  );
}

function Marker({ marker, unit }: { marker: MapMarker; unit: number }) {
  const { x, y } = project(marker);
  const move = { transform: `translate(${x}px, ${y}px)`, transition: "transform 1.4s linear" } as const;
  if (marker.kind === "car") {
    const color = marker.tone === "busy" ? "var(--map-car-busy, #F59E0B)" : marker.tone === "muted" ? "var(--map-car-muted, #9CA3AF)" : "var(--map-car, #0B1B2B)";
    return (
      <g style={move}>
        <g transform={`rotate(${marker.heading ?? 0}) scale(${unit})`}>
          <rect x={-1.1} y={-2} width={2.2} height={4} rx={0.8} fill={color} stroke="#fff" strokeWidth={0.35} />
          <rect x={-0.75} y={-1.25} width={1.5} height={0.9} rx={0.3} fill="#fff" opacity={0.85} />
        </g>
        {marker.label ? <MarkerLabel text={marker.label} unit={unit} /> : null}
      </g>
    );
  }
  if (marker.kind === "dot") {
    return (
      <g style={move}>
        <circle r={unit * 1.1} fill="var(--map-car, #0B1B2B)" stroke="#fff" strokeWidth={unit * 0.4} />
        {marker.label ? <MarkerLabel text={marker.label} unit={unit} /> : null}
      </g>
    );
  }
  const color = marker.kind === "pickup" ? "var(--map-pickup, #16A34A)" : "var(--map-drop, #DC2626)";
  return (
    <g style={{ transform: `translate(${x}px, ${y}px)` }}>
      <circle r={unit * 3.2} fill={color} opacity={0.16} />
      {marker.kind === "pickup" ? (
        <circle r={unit * 1.4} fill={color} stroke="#fff" strokeWidth={unit * 0.55} />
      ) : (
        <rect x={-unit * 1.3} y={-unit * 1.3} width={unit * 2.6} height={unit * 2.6} fill={color} stroke="#fff" strokeWidth={unit * 0.55} />
      )}
      {marker.label ? <MarkerLabel text={marker.label} unit={unit} /> : null}
    </g>
  );
}

function MarkerLabel({ text, unit }: { text: string; unit: number }) {
  const width = Math.min(40, text.length * 1.45 + 3) * unit;
  return (
    <g transform={`translate(0 ${-unit * 5})`} style={{ pointerEvents: "none" }}>
      <rect x={-width / 2} y={-unit * 2.4} width={width} height={unit * 3.6} rx={unit * 1.2} fill="var(--map-label-bg, #0B1B2B)" />
      <text textAnchor="middle" y={unit * 0.35} fontSize={unit * 2.1} fontWeight={600} fill="var(--map-label-fg, #FFFFFF)">
        {text.length > 26 ? `${text.slice(0, 25)}…` : text}
      </text>
    </g>
  );
}
