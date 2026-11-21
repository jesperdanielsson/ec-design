import { useState } from "react";
import type { LoadsResult } from "../api";
import { CombinationDiagrams } from "../components/CombinationDiagrams";
import { Tex } from "../components/Tex";
import { beamLength, supportX, type BeamInput } from "../model";

interface Props {
  beam: BeamInput;
  update: (patch: Partial<BeamInput>) => void;
  result?: LoadsResult;
  error?: string;
}

function Toggle({ label, help, checked, disabled, onChange }: {
  label: string;
  help: string;
  checked: boolean;
  disabled?: boolean;
  onChange?: (v: boolean) => void;
}) {
  return (
    <label className={`toggle ${disabled ? "disabled" : ""}`}>
      <input type="checkbox" checked={checked} disabled={disabled} onChange={(e) => onChange?.(e.target.checked)} />
      <span className="switch" aria-hidden />
      <span>
        <span className="toggle-label">{label}</span>
        <span className="muted small block">{help}</span>
      </span>
    </label>
  );
}

const GROUPS = [
  { id: "uls", label: "Brottgräns", sub: "Ed" },
  { id: "characteristic", label: "Karakteristisk", sub: "Ek" },
  { id: "frequent", label: "Frekvent", sub: "Ek" },
  { id: "quasi_permanent", label: "Kvasipermanent", sub: "Ek" },
] as const;

const fmt = (v?: number | null, d = 1) =>
  v === undefined || v === null || !Number.isFinite(v) ? "–" : v.toLocaleString("sv-SE", { maximumFractionDigits: d });

const spansText = (ls: Record<string, number[]>) =>
  Object.entries(ls)
    .map(([id, sp]) => `${id} på fack ${sp.join(", ") || "inget"}`)
    .join("; ");

export function AnalysisStep({ beam, update, result, error }: Props) {
  const a = beam.analysis;
  const set = (patch: Partial<BeamInput["analysis"]>) => update({ analysis: { ...a, ...patch } });
  const [group, setGroup] = useState<(typeof GROUPS)[number]["id"]>("uls");
  const g = GROUPS.find((x) => x.id === group)!;
  const design = result?.design[group];
  const env = result?.diagrams[group];
  const span = beamLength(beam);
  const supX = supportX(beam.spans_m);
  const sls = group !== "uls";
  return (
    <div className="step-grid">
      <section className="card">
        <h2>Vad ska kontrolleras?</h2>
        <Toggle label="Brottgräns" help="Böjning och tvärkraft. Alltid på." checked disabled />
        <Toggle label="Nedböjning" help="EN 1992-1-1 7.4" checked={a.deflection} onChange={(v) => set({ deflection: v })} />
        <Toggle label="Krypning" help="Långtidseffekter, EN 1992-1-1 3.1.4" checked={a.creep} onChange={(v) => set({ creep: v })} />
        <Toggle
          label="Sprickanalys"
          help="Minimiarmering (7.3.2) och sprickbredd (7.3.4)"
          checked={a.cracking}
          onChange={(v) => set({ cracking: v })}
        />
        <h2>Så räknas snittkrafterna</h2>
        <ul className="muted small">
          <li>Linjärelastisk analys med konstant böjstyvhet (EN 1992-1-1 5.4), ingen momentomfördelning (5.5).</li>
          <li>Varje lastfall räknas för sig och kombineras i varje snitt med kombinationens faktorer.</li>
          {beam.spans_m.length > 1 && (
            <li>
              {result?.system.pattern
                ? "Variabel last placeras fack för fack där den verkar ogynnsamt (mönsterbelastning, 5.1.3). Permanent last ligger på alla fack med samma faktor."
                : "Mönsterbelastning är avstängd: variabel last ligger alltid på hela balken."}
            </li>
          )}
          <li>
            Nedböjningen gäller osprucket betongtvärsnitt med E<sub>cm</sub>, korttid
            {result?.system.EI ? ` (EI = ${fmt(result.system.EI / 1000, 1)} MNm²)` : ""}. Sprickor och krypning (7.4.3) kommer i
            bruksgränssteget.
          </li>
        </ul>
      </section>

      <section className="card visual">
        <h2>Snittkrafter{result ? `: ${result.system.description.toLowerCase()}` : ""}</h2>
        {error && <p className="warning">{error}</p>}
        <div className="tabs" role="tablist">
          {GROUPS.map((x) => (
            <button key={x.id} role="tab" aria-selected={group === x.id} className={`chip${group === x.id ? " active" : ""}`} onClick={() => setGroup(x.id)}>
              {x.label}
            </button>
          ))}
        </div>
        {design && env && result && (
          <>
            <table className="table">
              <thead>
                <tr>
                  <th>Fack</th>
                  <th className="num">
                    <Tex tex={`M_{${g.sub}}`} /> fält (kNm)
                  </th>
                  {sls && <th className="num">δ (mm)</th>}
                  {sls && <th className="num">L/δ</th>}
                  <th>Kombination och lastuppställning</th>
                </tr>
              </thead>
              <tbody>
                {design.spans.map((s) => (
                  <tr key={s.index}>
                    <td>
                      {s.cantilever ? "Konsol" : "Fack"} {s.index}
                      <span className="muted small block">L = {fmt(s.length, 2)} m</span>
                    </td>
                    <td className="num">{s.M.value > 1e-6 ? fmt(s.M.value) : "–"}</td>
                    {sls && <td className="num">{fmt(s.w?.value, 2)}</td>}
                    {sls && <td className="num">{s.L_over_w ? `L/${s.L_over_w}` : "–"}</td>}
                    <td className="muted small">
                      {((sls ? s.w : s.M)?.value ?? 0) > 1e-6 ? (sls ? s.combination_w : s.combination_M) : "Inget fältmoment (se stödmomentet)"}
                      {((sls ? s.w : s.M)?.value ?? 0) > 1e-6 && Object.keys((sls ? s.w : s.M)?.loaded_spans ?? {}).length > 0 && (
                        <span className="block">{spansText((sls ? s.w : s.M)!.loaded_spans)}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <table className="table">
              <thead>
                <tr>
                  <th>Stöd</th>
                  <th className="num">
                    <Tex tex={`M_{${g.sub}}`} /> stöd (kNm)
                  </th>
                  <th className="num">R max (kN)</th>
                  <th className="num">R min (kN)</th>
                  <th>Kombination</th>
                </tr>
              </thead>
              <tbody>
                {design.supports.map((s) => (
                  <tr key={s.label}>
                    <td>
                      {s.label}
                      <span className="muted small block">{s.type === "fixed" ? "Inspänning" : "Upplag"}</span>
                    </td>
                    <td className="num">{s.M < -1e-6 ? fmt(s.M) : "0"}</td>
                    <td className="num">{fmt(s.R_max)}</td>
                    <td className={`num${s.R_min < -1e-6 ? " warning-text" : ""}`}>{fmt(s.R_min)}</td>
                    <td className="muted small">{s.M < -1e-6 ? s.combination_M : s.combination_R}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="muted small">
              Moment ritas på dragen sida: fältmoment nedåt, stödmoment uppåt. Stödmoment räknas i stödets centrum. R min
              under noll betyder att stödet kan lyftas. Tabellerna sammanställer alla kombinationer och lastuppställningar i
              gruppen. Diagrammen nedan visar en kombination och en lastuppställning i taget.
            </p>
            <h2>Diagram per lastkombination</h2>
            <CombinationDiagrams
              key={group}
              result={result}
              span_m={span}
              supports_x={supX}
              group={group}
              initial={design.combination_M}
            />
            {result.warnings.map((w) => (
              <p key={w} className="warning">
                {w}
              </p>
            ))}
          </>
        )}
      </section>
    </div>
  );
}
