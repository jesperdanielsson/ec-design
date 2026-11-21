// Moment- och tvärkraftsdiagram under balken.
// Moment ritas på dragen sida (positivt moment nedåt), som i svensk handräkning.

export interface ForceSeries {
  label: string;
  values: number[];
  /** Extra klass, t.ex. "fd-faint" för en jämförelsekurva. */
  className?: string;
  /** Fyll ytan mot nollinjen: "pos" bara där värdet är positivt, "neg" bara där det är negativt.
   * Max- och min-kurvan i en omhyllning fylls var på sin sida, så att ytorna inte överlappar. */
  fill?: boolean | "pos" | "neg";
  dashed?: boolean;
  /** false: visas inte i förklaringen (t.ex. min-kurvan i en omhyllning). */
  legend?: boolean;
}

interface Props {
  x: number[];
  series: ForceSeries[];
  span_m: number;
  /** Stödens lägen i m: ritas som tunna lodlinjer. */
  supports_x?: number[];
  unit: string;
  /** true: positivt värde ritas nedåt (moment). */
  downPositive?: boolean;
  title: string;
  /** Storhet: bestämmer färgen. Moment rött, tvärkraft blått, nedböjning grönt. */
  quantity: "M" | "V" | "w";
  annotate?: { x: number; value: number; label: string }[];
}

const clamp = (vals: number[], side: boolean | "pos" | "neg") =>
  side === "pos" ? vals.map((v) => Math.max(v, 0)) : side === "neg" ? vals.map((v) => Math.min(v, 0)) : vals;

const fmt = (v: number, d = 1) => v.toLocaleString("sv-SE", { maximumFractionDigits: d });

export function ForceDiagram({ x, series, span_m, supports_x = [], unit, downPositive = false, title, quantity, annotate = [] }: Props) {
  const W = 480;
  const H = 150;
  const x0 = 34;
  const x1 = W - 16;
  const all = series.flatMap((s) => s.values);
  if (!all.length) return null;
  const vMax = Math.max(1e-9, ...all.map(Math.abs));
  const hasNeg = all.some((v) => v < -1e-6);
  const hasPos = all.some((v) => v > 1e-6);
  // Nollinjen hamnar mitt i om diagrammet har båda tecknen, annars i kanten.
  const yZero = hasNeg && hasPos ? H / 2 : (hasPos !== downPositive ? H - 26 : 22);
  const scale = (hasNeg && hasPos ? H / 2 - 24 : H - 52) / vMax;
  const sx = (v: number) => x0 + (v / span_m) * (x1 - x0);
  const sy = (v: number) => yZero + (downPositive ? 1 : -1) * v * scale;
  const path = (vals: number[]) => vals.map((v, i) => `${i ? "L" : "M"}${sx(x[i]).toFixed(1)},${sy(v).toFixed(1)}`).join(" ");

  return (
    <figure className="chart-figure">
      <svg viewBox={`0 0 ${W} ${H}`} className={`diagram force-diagram fd-${quantity}`} role="img" aria-label={title}>
        <text x={8} y={yZero + 4} className="fd-title">
          {title}
        </text>
        {supports_x.map((xs, i) => (
          <line key={i} x1={sx(xs)} x2={sx(xs)} y1={6} y2={H - 6} className="fd-support" />
        ))}
        <line x1={x0} x2={x1} y1={yZero} y2={yZero} className="fd-axis" />
        {series.map((s) => (
          <g key={s.label} className={s.className}>
            {s.fill && <path d={`${path(clamp(s.values, s.fill))} L${sx(x[x.length - 1])},${yZero} L${sx(x[0])},${yZero} Z`} className="fd-fill" />}
            <path d={path(s.values)} className={`fd-line${s.dashed ? " dashed" : ""}`} />
          </g>
        ))}
        {annotate.map((a, i) => (
          <g key={i} className="fd-note">
            <circle cx={sx(a.x)} cy={sy(a.value)} r={3} />
            <text
              x={Math.min(Math.max(sx(a.x), x0 + 70), x1 - 70)}
              y={sy(a.value) + ((downPositive ? a.value >= 0 : a.value < 0) ? 16 : -8)}
              textAnchor="middle"
            >
              {a.label} = {fmt(a.value)} {unit}
            </text>
          </g>
        ))}
      </svg>
      {series.filter((s) => s.legend !== false).length > 1 && (
        <figcaption className={`legend fd-${quantity}`}>
          {series.filter((s) => s.legend !== false).map((s) => (
            <span key={s.label} className="legend-item">
              <span className={`legend-swatch fd-swatch ${s.className ?? ""}${s.dashed ? " dashed" : ""}`} />
              {s.label}
            </span>
          ))}
        </figcaption>
      )}
    </figure>
  );
}
