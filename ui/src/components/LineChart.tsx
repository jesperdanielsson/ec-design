// Enkelt linjediagram i SVG med valfri logaritmisk tidsaxel.
// Används för hållfasthet över tid, kryptal och krympning i materialsteget.

export interface Series {
  label: string;
  points: [number, number][];
  className?: string; // "curve", "curve-2", "curve-3"
  dashed?: boolean;
}

export interface Marker {
  x?: number;
  y?: number;
  label: string;
}

interface Props {
  series: Series[];
  xLabel: string;
  yLabel: string;
  logX?: boolean;
  xTicks?: { value: number; label: string }[];
  yMax?: number;
  markers?: Marker[];
  ariaLabel: string;
}

const fmt = (v: number) => v.toLocaleString("sv-SE", { maximumFractionDigits: 2 });

// Ett "jämnt" steg (1, 2, 2,5 eller 5 · 10^n) så att axeln får 3–5 runda värden.
function niceStep(v: number): number {
  if (v <= 0) return 1;
  const p = Math.pow(10, Math.floor(Math.log10(v)));
  for (const m of [1, 2, 2.5, 5, 10]) if (m * p >= v) return m * p;
  return 10 * p;
}

export function LineChart({ series, xLabel, yLabel, logX = false, xTicks, yMax, markers = [], ariaLabel }: Props) {
  const W = 440;
  const H = 250;
  const pad = { l: 52, r: 18, t: 18, b: 42 };
  const all = series.flatMap((s) => s.points);
  if (!all.length) return null;
  const xs = all.map(([x]) => x).filter((x) => !logX || x > 0);
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  const yStep = niceStep((yMax ?? Math.max(...all.map(([, y]) => y)) * 1.05) / 4);
  const yTop = yMax ?? yStep * Math.ceil((Math.max(...all.map(([, y]) => y)) * 1.05) / yStep);
  const tx = (x: number) => (logX ? Math.log10(Math.max(x, xMin)) : x);
  const sx = (x: number) => pad.l + ((tx(x) - tx(xMin)) / (tx(xMax) - tx(xMin) || 1)) * (W - pad.l - pad.r);
  const sy = (y: number) => H - pad.b - (y / yTop) * (H - pad.t - pad.b);
  const path = (pts: [number, number][]) =>
    pts
      .filter(([x]) => !logX || x > 0)
      .map(([x, y], i) => `${i ? "L" : "M"}${sx(x).toFixed(1)},${sy(y).toFixed(1)}`)
      .join(" ");
  const yTicks = Array.from({ length: Math.round(yTop / yStep) + 1 }, (_, i) => i * yStep);
  const ticks = (xTicks ?? []).filter((t) => t.value >= xMin && t.value <= xMax);

  return (
    <figure className="chart-figure">
      <svg viewBox={`0 0 ${W} ${H}`} className="diagram chart" role="img" aria-label={ariaLabel}>
        <g className="grid">
          {yTicks.map((v) => (
            <g key={v}>
              <line x1={sx(xMin)} x2={sx(xMax)} y1={sy(v)} y2={sy(v)} />
              <text x={pad.l - 8} y={sy(v) + 4} textAnchor="end">
                {fmt(v)}
              </text>
            </g>
          ))}
          {ticks.map((t) => (
            <g key={t.value}>
              <line x1={sx(t.value)} x2={sx(t.value)} y1={sy(0)} y2={sy(yTop)} />
              <text x={sx(t.value)} y={H - pad.b + 16} textAnchor="middle">
                {t.label}
              </text>
            </g>
          ))}
        </g>
        <text x={(W + pad.l) / 2} y={H - 6} textAnchor="middle" className="axis-label">
          {xLabel}
        </text>
        <text x={14} y={H / 2} textAnchor="middle" transform={`rotate(-90 14 ${H / 2})`} className="axis-label">
          {yLabel}
        </text>
        {markers.map((m, i) =>
          m.x !== undefined ? (
            <g key={i}>
              <line className="marker" x1={sx(m.x)} x2={sx(m.x)} y1={sy(0)} y2={sy(yTop)} />
              <text x={sx(m.x) + 4} y={pad.t + 10} className="small">
                {m.label}
              </text>
            </g>
          ) : m.y !== undefined ? (
            <g key={i}>
              <line className="marker" x1={sx(xMin)} x2={sx(xMax)} y1={sy(m.y)} y2={sy(m.y)} />
              <text x={sx(xMax) - 4} y={sy(m.y) - 6} textAnchor="end" className="small">
                {m.label}
              </text>
            </g>
          ) : null,
        )}
        {series.map((s) => (
          <path key={s.label} d={path(s.points)} className={`${s.className ?? "curve"}${s.dashed ? " dashed" : ""}`} />
        ))}
      </svg>
      {series.length > 1 && (
        <figcaption className="legend">
          {series.map((s) => (
            <span key={s.label} className="legend-item">
              <span className={`legend-swatch ${s.className ?? "curve"}${s.dashed ? " dashed" : ""}`} />
              {s.label}
            </span>
          ))}
        </figcaption>
      )}
    </figure>
  );
}

// Tidsaxel i dygn med etiketter som en konstruktör känner igen.
export const TIME_TICKS = [
  { value: 1, label: "1 d" },
  { value: 7, label: "7 d" },
  { value: 28, label: "28 d" },
  { value: 90, label: "3 mån" },
  { value: 365, label: "1 år" },
  { value: 3650, label: "10 år" },
  { value: 25550, label: "70 år" },
];
