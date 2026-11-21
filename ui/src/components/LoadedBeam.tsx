import type { ResolvedCase } from "../api";
import { supportX, type SupportType } from "../model";
import { SpanDims, SupportGlyphs } from "./Supports";

interface Props {
  spans_m: number[];
  supports: SupportType[];
  cases: ResolvedCase[];
  highlight?: string | null;
}

const fmt = (v: number, d = 2) => v.toLocaleString("sv-SE", { maximumFractionDigits: d });

/** Färgklass för ett lastfall: permanenta i grått/blått, variabla i egna färger. */
export function caseColor(cases: { kind: string }[], index: number): string {
  const kind = cases[index]?.kind;
  const sameKind = cases.slice(0, index).filter((c) => c.kind === kind).length;
  return kind === "permanent" ? `lc-g${sameKind % 2}` : `lc-q${sameKind % 4}`;
}

// Balken med alla lastfall, ett band per lastfall ovanför balken.
// Utbredda laster ritas med höjd efter storlek, punktlaster som en pil. Uppåtriktad last
// (t.ex. vindsug) ritas med pilar uppåt.
export function LoadedBeam({ spans_m, supports, cases, highlight }: Props) {
  const W = 480;
  const x0 = 34;
  const x1 = W - 16;
  const span_m = spans_m.reduce((s, L) => s + L, 0) || 1;
  const sx = (x: number) => x0 + (x / span_m) * (x1 - x0);
  const xsSup = supportX(spans_m).map(sx);
  const cant = spans_m.map((_, j) => supports[j] === "free" || supports[j + 1] === "free");
  const qMax = Math.max(1e-9, ...cases.flatMap((c) => c.loads.map((l) => Math.abs(l.q ?? 0))));
  const height = (q: number) => 14 + (16 * Math.abs(q)) / qMax;
  // Bandens höjd: utbredda laster staplas på varandra, punktlaster behöver 40 px.
  const bands = cases.map((c) => {
    const udl = c.loads.filter((l) => l.type !== "point").reduce((s, l) => s + height(l.q ?? 0), 0);
    const pt = c.loads.some((l) => l.type === "point") ? 40 : 0;
    return Math.max(udl, pt) + 10;
  });
  const top = 6;
  const yBeam = top + bands.reduce((s, b) => s + b, 0) + 10;
  const H = yBeam + 72;

  let yCursor = top;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="diagram loaded-beam" role="img" aria-label="Laster på balken">
      <defs>
        <marker id="lb-arrow" viewBox="0 0 10 10" refX="5" refY="9" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
          <path d="M0,0 L10,0 L5,10 z" fill="context-stroke" />
        </marker>
      </defs>
      {cases.map((c, i) => {
        yCursor += bands[i];
        const yBase = yCursor - 4;
        const dim = highlight && highlight !== c.id;
        let stack = 0;
        return (
          <g key={c.id} className={`lb-case ${caseColor(cases, i)}${dim ? " dim" : ""}`}>
            <line x1={x0} x2={x1} y1={yBase} y2={yBase} className="lb-base" />
            <text x={4} y={yBase - 3} className="lb-id">
              {c.id}
            </text>
            {c.loads.map((l, j) => {
              if (l.type === "point") {
                const x = sx(l.a ?? 0);
                const up = (l.P ?? 0) < 0;
                const anchor = x > (x0 + x1) / 2 ? "end" : "start";
                return (
                  <g key={j}>
                    <line x1={x} x2={x} y1={up ? yBase : yBase - 36} y2={up ? yBase - 36 : yBase} markerEnd="url(#lb-arrow)" className="lb-arrow strong" />
                    <text x={x + (anchor === "start" ? 5 : -5)} y={yBase - 26} textAnchor={anchor} className="lb-label">
                      {fmt(l.P ?? 0)} kN
                    </text>
                  </g>
                );
              }
              const a = l.a ?? 0;
              const b = l.b ?? span_m;
              const q = l.q ?? 0;
              const h = height(q);
              const yb = yBase - stack;
              stack += h;
              const xa = sx(a);
              const xb = sx(b);
              const n = Math.max(2, Math.round((xb - xa) / 26));
              const up = q < 0;
              return (
                <g key={j}>
                  <rect x={xa} y={yb - h} width={xb - xa} height={h} className="lb-area" />
                  {Array.from({ length: n + 1 }, (_, k) => {
                    const x = xa + ((xb - xa) * k) / n;
                    return (
                      <line key={k} x1={x} x2={x} y1={up ? yb : yb - h} y2={up ? yb - h : yb} markerEnd="url(#lb-arrow)" className="lb-arrow" />
                    );
                  })}
                  <text x={(xa + xb) / 2} y={yb - h / 2 + 4} textAnchor="middle" className="lb-label halo">
                    {fmt(q)} kN/m{l.text ? ` (${l.text.toLowerCase()})` : ""}
                  </text>
                </g>
              );
            })}
          </g>
        );
      })}
      <rect x={x0} y={yBeam - 7} width={x1 - x0} height={14} rx={3} className="beam" />
      <SupportGlyphs supports={supports} xs={xsSup} y={yBeam + 7} beamH={14} size={8} />
      <SpanDims xs={xsSup} spans_m={spans_m} y={H - 8} cantilevers={cant} />
    </svg>
  );
}
