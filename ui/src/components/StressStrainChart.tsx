interface Props {
  curve: [number, number][];
  fcd: number;
  epsC2: number;
  epsCu2: number;
}

// σ–ε-diagram för betong (parabel-rektangel, EN 1992-1-1 figur 3.3).
export function StressStrainChart({ curve, fcd, epsC2, epsCu2 }: Props) {
  const W = 420;
  const H = 240;
  const pad = { l: 48, r: 16, t: 16, b: 40 };
  const xMax = Math.max(4, Math.ceil(epsCu2));
  const yMax = Math.ceil((fcd * 1.15) / 5) * 5;
  const sx = (e: number) => pad.l + (e / xMax) * (W - pad.l - pad.r);
  const sy = (s: number) => H - pad.b - (s / yMax) * (H - pad.t - pad.b);
  const d = curve.map(([e, s], i) => `${i ? "L" : "M"}${sx(e).toFixed(1)},${sy(s).toFixed(1)}`).join(" ");
  const fmt = (v: number) => v.toLocaleString("sv-SE", { maximumFractionDigits: 2 });
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="diagram chart" role="img" aria-label="Spänning–töjning">
      <g className="grid">
        {Array.from({ length: xMax + 1 }, (_, i) => (
          <g key={i}>
            <line x1={sx(i)} x2={sx(i)} y1={sy(0)} y2={sy(yMax)} />
            <text x={sx(i)} y={H - pad.b + 16} textAnchor="middle">
              {i}
            </text>
          </g>
        ))}
        {[0, yMax / 2, yMax].map((v) => (
          <g key={v}>
            <line x1={sx(0)} x2={sx(xMax)} y1={sy(v)} y2={sy(v)} />
            <text x={pad.l - 8} y={sy(v) + 4} textAnchor="end">
              {v}
            </text>
          </g>
        ))}
      </g>
      <text x={(W + pad.l) / 2} y={H - 6} textAnchor="middle" className="axis-label">
        ε<tspan baselineShift="sub" fontSize="9">c</tspan> (‰)
      </text>
      <text x={14} y={H / 2} textAnchor="middle" transform={`rotate(-90 14 ${H / 2})`} className="axis-label">
        σ<tspan baselineShift="sub" fontSize="9">c</tspan> (MPa)
      </text>
      <line className="marker" x1={sx(epsC2)} x2={sx(epsC2)} y1={sy(0)} y2={sy(fcd)} />
      <line className="marker" x1={sx(epsCu2)} x2={sx(epsCu2)} y1={sy(0)} y2={sy(fcd)} />
      <path d={d} className="curve" />
      <text x={sx(epsC2)} y={sy(fcd) - 8} textAnchor="middle" className="small">
        ε<tspan baselineShift="sub" fontSize="8">c2</tspan> = {fmt(epsC2)} ‰
      </text>
      <text x={sx(epsCu2)} y={sy(fcd) - 8} textAnchor="end" className="small">
        ε<tspan baselineShift="sub" fontSize="8">cu2</tspan> = {fmt(epsCu2)} ‰
      </text>
      <text x={sx(xMax) - 4} y={sy(fcd) + 16} textAnchor="end" className="small">
        f<tspan baselineShift="sub" fontSize="8">cd</tspan> = {fmt(fcd)} MPa
      </text>
    </svg>
  );
}
