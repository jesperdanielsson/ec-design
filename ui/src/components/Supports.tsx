import type { SupportType } from "../model";
import { supportLabel } from "../model";

const fmt = (v: number) => v.toLocaleString("sv-SE", { maximumFractionDigits: 2 });

interface Props {
  supports: SupportType[];
  /** Stödens lägen i pixlar. */
  xs: number[];
  /** Balkens underkant (y i pixlar) där upplagen sitter. */
  y: number;
  /** Balkens höjd i pixlar, för inspänningens vägg. */
  beamH: number;
  size?: number;
}

// Stöd ritade som i en handräkning: fast lager (triangel), rullager (triangel med hjul),
// fast inspänning (vägg med skraffering), fri ände (inget). Beteckning A, B, C … under.
export function SupportGlyphs({ supports, xs, y, beamH, size = 10 }: Props) {
  const firstPinned = supports.findIndex((s) => s === "pinned");
  return (
    <g>
      {supports.map((s, i) => {
        const x = xs[i];
        const label = (
          <text x={x} y={y + size * 2 + 22} textAnchor="middle" className="support-label">
            {supportLabel(i)}
          </text>
        );
        if (s === "free") {
          return (
            <g key={i}>
              <text x={x} y={y + 16} textAnchor="middle" className="small">
                {supportLabel(i)}
              </text>
            </g>
          );
        }
        if (s === "fixed") {
          const left = i === 0;
          const wx = left ? x - 2 : x + 2;
          const top = y - beamH - 12;
          const bot = y + 12;
          const dir = left ? -1 : 1;
          return (
            <g key={i}>
              <line x1={wx} x2={wx} y1={top} y2={bot} className="support wall" />
              {Array.from({ length: 6 }, (_, k) => {
                const yy = top + 4 + (k * (bot - top - 4)) / 6;
                return <line key={k} x1={wx} x2={wx + dir * 8} y1={yy} y2={yy + 7} className="support hatch" />;
              })}
              <text x={x} y={y + size * 2 + 22} textAnchor="middle" className="support-label">
                {supportLabel(i)}
              </text>
            </g>
          );
        }
        const roller = i !== firstPinned;
        return (
          <g key={i}>
            <path d={`M${x},${y} l-${size},${size * 1.7} h${size * 2} z`} className="support" />
            {roller ? (
              <>
                <circle cx={x - size * 0.55} cy={y + size * 1.7 + 4} r={2.5} className="support" />
                <circle cx={x + size * 0.55} cy={y + size * 1.7 + 4} r={2.5} className="support" />
              </>
            ) : (
              <line x1={x - size - 3} x2={x + size + 3} y1={y + size * 1.7 + 2} y2={y + size * 1.7 + 2} className="support" />
            )}
            {label}
          </g>
        );
      })}
    </g>
  );
}

/** Måttlinjer per fack under balken. */
export function SpanDims({ xs, spans_m, y, cantilevers }: { xs: number[]; spans_m: number[]; y: number; cantilevers?: boolean[] }) {
  return (
    <g className="dim">
      {spans_m.map((L, j) => (
        <g key={j}>
          <line x1={xs[j]} x2={xs[j + 1]} y1={y} y2={y} />
          <line x1={xs[j]} x2={xs[j]} y1={y - 6} y2={y + 6} />
          <line x1={xs[j + 1]} x2={xs[j + 1]} y1={y - 6} y2={y + 6} />
          <text x={(xs[j] + xs[j + 1]) / 2} y={y - 4} textAnchor="middle">
            {spans_m.length > 1 ? `L${j + 1}` : "L"} = {fmt(L)} m{cantilevers?.[j] ? " (konsol)" : ""}
          </text>
        </g>
      ))}
    </g>
  );
}
