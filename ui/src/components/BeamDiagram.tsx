interface Props {
  span_m: number;
  q_kNm?: number;
  label?: string;
}

// Balkvy: fritt upplagd balk med stöd, spännvidd och (valfritt) utbredd last.
export function BeamDiagram({ span_m, q_kNm, label }: Props) {
  const W = 440;
  const x0 = 30;
  const x1 = W - 30;
  const y = 110;
  const arrows = 10;
  // "q_k" ritas som q med nedsänkt k
  const [base, sub] = (label ?? "q").split("_");
  return (
    <svg viewBox={`0 0 ${W} 190`} className="diagram" role="img" aria-label="Balkvy">
      {q_kNm !== undefined && q_kNm > 0 && (
        <g className="load">
          <line x1={x0} x2={x1} y1={50} y2={50} />
          {Array.from({ length: arrows + 1 }, (_, i) => {
            const x = x0 + ((x1 - x0) * i) / arrows;
            return <line key={i} x1={x} x2={x} y1={50} y2={y - 14} markerEnd="url(#arrow)" />;
          })}
          <text x={(x0 + x1) / 2} y={38} textAnchor="middle">
            {base}
            {sub && (
              <tspan baselineShift="sub" fontSize="9">
                {sub}
              </tspan>
            )}{" "}
            = {q_kNm.toLocaleString("sv-SE")} kN/m
          </text>
        </g>
      )}
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="9" markerWidth="6" markerHeight="6" orient="auto">
          <path d="M0,0 L10,0 L5,10 z" className="arrow-head" />
        </marker>
      </defs>
      <rect x={x0} y={y - 10} width={x1 - x0} height={20} rx={3} className="beam" />
      {/* Stöd: fast lager vänster, rullager höger */}
      <path d={`M${x0},${y + 10} l-14,24 h28 z`} className="support" />
      <path d={`M${x1},${y + 10} l-14,22 h28 z`} className="support" />
      <circle cx={x1 - 8} cy={y + 37} r={3} className="support" />
      <circle cx={x1 + 8} cy={y + 37} r={3} className="support" />
      <g className="dim">
        <line x1={x0} x2={x1} y1={172} y2={172} />
        <line x1={x0} x2={x0} y1={164} y2={180} />
        <line x1={x1} x2={x1} y1={164} y2={180} />
        <text x={(x0 + x1) / 2} y={166} textAnchor="middle">
          L = {span_m.toLocaleString("sv-SE")} m
        </text>
      </g>
    </svg>
  );
}
