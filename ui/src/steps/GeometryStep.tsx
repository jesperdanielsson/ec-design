import { NumberField } from "../components/Field";
import { BeamDiagram } from "../components/BeamDiagram";
import { SectionView } from "../components/SectionView";
import { Beam3D } from "../components/Beam3D";
import { SYSTEMS, beamLength, supportLabel, systemKind, validSystem, type BeamInput, type SupportType, type SystemKind } from "../model";
import type { CoverResult, LoadsResult } from "../api";

interface Props {
  beam: BeamInput;
  update: (patch: Partial<BeamInput>) => void;
  cover?: CoverResult;
  result?: LoadsResult;
}

const END_LABEL: Record<SupportType, string> = {
  pinned: "Fritt upplag",
  fixed: "Fast inspänning",
  free: "Fri ände (konsol)",
};

export function GeometryStep({ beam, update, cover, result }: Props) {
  const coverTooBig = beam.cover_mm >= beam.h_mm / 2;
  const kind = systemKind(beam);
  const n = beam.spans_m.length;
  const L0 = Math.max(...beam.spans_m.filter((_, j) => !(beam.supports[j] === "free" || beam.supports[j + 1] === "free")), beam.spans_m[0]);
  const pick = (k: SystemKind) => update(SYSTEMS[k].make(Number.isFinite(L0) && L0 > 0 ? L0 : 6, Math.max(2, n)));
  const setSpan = (j: number, v: number) => update({ spans_m: beam.spans_m.map((L, i) => (i === j ? v : L)) });
  const setEnd = (i: number, v: SupportType) => update({ supports: beam.supports.map((s, k) => (k === i ? v : s)) });
  // Antal fack mellan stöden (konsoler räknas inte): lägg till eller ta bort ett inre fack.
  const setInnerSpans = (count: number) => {
    const c = Math.max(1, Math.min(8, Math.round(count)));
    const leftFree = beam.supports[0] === "free";
    const rightFree = beam.supports[n] === "free";
    const inner = beam.spans_m.slice(leftFree ? 1 : 0, rightFree ? n - 1 : n);
    const Lnew = inner[inner.length - 1] ?? 6;
    const spans = [...inner.slice(0, c), ...Array(Math.max(0, c - inner.length)).fill(Lnew)];
    update({
      spans_m: [...(leftFree ? [beam.spans_m[0]] : []), ...spans, ...(rightFree ? [beam.spans_m[n - 1]] : [])],
      supports: [beam.supports[0], ...Array((leftFree ? 1 : 0) + c + (rightFree ? 1 : 0) - 1).fill("pinned"), beam.supports[n]],
    });
  };
  const innerCount = n - (beam.supports[0] === "free" ? 1 : 0) - (beam.supports[n] === "free" ? 1 : 0);
  const valid = validSystem(beam);
  return (
    <div className="step-grid">
      <section className="card">
        <h2>Statiskt system</h2>
        <div className="system-picker" role="radiogroup" aria-label="Statiskt system">
          {(Object.keys(SYSTEMS) as SystemKind[]).map((k) => (
            <button key={k} className={`chip${kind === k ? " active" : ""}`} onClick={() => pick(k)} title={SYSTEMS[k].help} role="radio" aria-checked={kind === k}>
              {SYSTEMS[k].label}
            </button>
          ))}
        </div>
        <p className="muted small">{kind ? SYSTEMS[kind].help : "Eget system: välj stödtyp i varje ände och antal fack."}</p>

        <div className="row">
          <label className="field" title="Vänster ände (stöd A). Fri ände ger en konsol eller ett överhäng.">
            <span className="field-label">
              Vänster ände A<span className="help-dot" aria-hidden>?</span>
            </span>
            <select value={beam.supports[0]} onChange={(e) => setEnd(0, e.target.value as SupportType)}>
              {Object.entries(END_LABEL).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </label>
          <label className="field" title={`Höger ände (stöd ${supportLabel(n)}).`}>
            <span className="field-label">
              Höger ände {supportLabel(n)}
              <span className="help-dot" aria-hidden>?</span>
            </span>
            <select value={beam.supports[n]} onChange={(e) => setEnd(n, e.target.value as SupportType)}>
              {Object.entries(END_LABEL).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </label>
        </div>
        <NumberField
          label="Antal fack mellan stöd"
          unit="st"
          value={innerCount}
          min={1}
          help="Fler än ett fack ger en kontinuerlig balk med fritt upplagda mellanstöd. Konsoler i ändarna räknas inte."
          onChange={(v) => Number.isFinite(v) && setInnerSpans(v)}
        />
        <div className="span-list">
          {beam.spans_m.map((L, j) => {
            const cant = beam.supports[j] === "free" || beam.supports[j + 1] === "free";
            return (
              <NumberField
                key={j}
                label={`${cant ? "Konsol" : "Fack"} ${supportLabel(j)}–${supportLabel(j + 1)}`}
                symbol={`L_{${j + 1}}`}
                unit="m"
                step={0.1}
                value={L}
                help={
                  cant
                    ? "Konsolens längd från stödets centrum till den fria änden."
                    : "Teoretisk spännvidd mellan stödens centrum, EN 1992-1-1 5.3.2.2(1)."
                }
                onChange={(v) => setSpan(j, v)}
              />
            );
          })}
        </div>
        <p className="muted small">
          Total längd {beamLength(beam).toLocaleString("sv-SE", { maximumFractionDigits: 2 })} m. Lasternas lägen mäts från vänster ände A.
          {n > 1 && " Stödmoment räknas i stödets centrum, utan reduktion för upplagets bredd (5.3.2.2(3)–(4))."}
        </p>
        {!valid && <p className="warning">Balken är inte stabil: den behöver minst två upplag eller en inspänning.</p>}
        {result && valid && <p className="ok-note">{result.system.description}.</p>}

        <h2>Tvärsnitt</h2>
        <div className="row">
          <NumberField label="Bredd" symbol="b" unit="mm" step={10} value={beam.b_mm} onChange={(v) => update({ b_mm: v })} />
          <NumberField label="Höjd" symbol="h" unit="mm" step={10} value={beam.h_mm} onChange={(v) => update({ h_mm: v })} />
        </div>

        <h2>Täckande betongskikt</h2>
        <NumberField
          label="Täckskikt"
          symbol="c_{nom}"
          unit="mm"
          value={beam.cover_mm}
          help="Täckskikt till yttersta armeringen (normalt bygeln). c_nom = c_min + Δc_dev, EN 1992-1-1 4.4.1. Krävt värde räknas fram i steget Material."
          onChange={(v) => update({ cover_mm: v })}
        />
        {cover && beam.cover_mm < cover.cnom && (
          <p className="warning">
            Krävt täckskikt för {beam.exposure.join(" + ")} ({beam.life}) är c<sub>nom</sub> = {cover.cnom} mm.{" "}
            <button className="btn ghost small" onClick={() => update({ cover_mm: cover.cnom })}>
              Använd {cover.cnom} mm
            </button>
          </p>
        )}
        {cover && beam.cover_mm >= cover.cnom && (
          <p className="ok-note">
            Uppfyller kravet c<sub>nom</sub> = {cover.cnom} mm för {beam.exposure.join(" + ")} ({beam.life}).
          </p>
        )}
        {coverTooBig && <p className="warning">Täckskiktet är större än halva höjden.</p>}
      </section>

      <section className="card visual">
        <h2>Balkvy</h2>
        <BeamDiagram spans_m={beam.spans_m} supports={beam.supports} />
        <div className="visual-row">
          <div>
            <h2>Tvärsnitt</h2>
            <SectionView b_mm={beam.b_mm} h_mm={beam.h_mm} cover_mm={beam.cover_mm} />
          </div>
          <div className="grow">
            <h2>3D</h2>
            <Beam3D span_m={beamLength(beam)} b_mm={beam.b_mm} h_mm={beam.h_mm} cover_mm={beam.cover_mm} />
          </div>
        </div>
      </section>
    </div>
  );
}
