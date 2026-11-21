interface Props {
  b_mm: number;
  h_mm: number;
  cover_mm: number;
}

// Tvärsnittsvy i skala, med täckskikt och exempelarmering.
// Armeringen är bara illustration tills armeringsinmatningen byggs.
export function SectionView({ b_mm, h_mm, cover_mm }: Props) {
  const maxW = 220;
  const maxH = 300;
  const s = Math.min(maxW / b_mm, maxH / h_mm);
  const w = b_mm * s;
  const h = h_mm * s;
  const ox = 60;
  const oy = 20;
  const c = cover_mm * s;
  const barR = Math.max(4, 8 * s);
  const n = 3;
  const bottom = Array.from({ length: n }, (_, i) => ox + c + barR + ((w - 2 * c - 2 * barR) * i) / (n - 1));
  return (
    <svg viewBox={`0 0 ${w + 120} ${h + 70}`} className="diagram section" role="img" aria-label="Tvärsnitt">
      <rect x={ox} y={oy} width={w} height={h} className="concrete" />
      <rect x={ox + c} y={oy + c} width={w - 2 * c} height={h - 2 * c} className="cover-line" />
      {bottom.map((x, i) => (
        <circle key={`b${i}`} cx={x} cy={oy + h - c - barR} r={barR} className="bar" />
      ))}
      {[bottom[0], bottom[n - 1]].map((x, i) => (
        <circle key={`t${i}`} cx={x} cy={oy + c + barR * 0.8} r={barR * 0.8} className="bar" />
      ))}
      <g className="dim">
        <line x1={ox} x2={ox + w} y1={oy + h + 25} y2={oy + h + 25} />
        <text x={ox + w / 2} y={oy + h + 45} textAnchor="middle">
          b = {b_mm} mm
        </text>
        <line x1={ox - 25} x2={ox - 25} y1={oy} y2={oy + h} />
        <text x={ox - 32} y={oy + h / 2} textAnchor="middle" transform={`rotate(-90 ${ox - 32} ${oy + h / 2})`}>
          h = {h_mm} mm
        </text>
        <text x={ox + w + 8} y={oy + h - c / 2 + 4} className="small">
          c = {cover_mm}
        </text>
      </g>
    </svg>
  );
}
