import { supportX, type SupportType } from "../model";
import { SpanDims, SupportGlyphs } from "./Supports";

interface Props {
  spans_m: number[];
  supports: SupportType[];
}

// Balkvy: det statiska systemet med stöd, fack och mått.
export function BeamDiagram({ spans_m, supports }: Props) {
  const W = 480;
  const x0 = 34;
  const x1 = W - 34;
  const y = 70;
  const total = spans_m.reduce((s, L) => s + L, 0) || 1;
  const xs = supportX(spans_m).map((x) => x0 + (x / total) * (x1 - x0));
  const cant = spans_m.map((_, j) => supports[j] === "free" || supports[j + 1] === "free");
  return (
    <svg viewBox={`0 0 ${W} 150`} className="diagram" role="img" aria-label="Statiskt system">
      <rect x={x0} y={y - 18} width={x1 - x0} height={18} rx={2} className="beam" />
      <SupportGlyphs supports={supports} xs={xs} y={y} beamH={18} />
      <SpanDims xs={xs} spans_m={spans_m} y={136} cantilevers={cant} />
    </svg>
  );
}
