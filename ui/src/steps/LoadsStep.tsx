import { Fragment, useState } from "react";
import type { CombinationResult, LoadOptions, LoadsResult } from "../api";
import { NumberField } from "../components/Field";
import { CombinationDiagrams } from "../components/CombinationDiagrams";
import { LoadedBeam, caseColor } from "../components/LoadedBeam";
import { Tex } from "../components/Tex";
import { beamLength, newId, supportX, type BeamInput, type LoadCaseInput, type LoadInput, type LoadType } from "../model";

interface Props {
  beam: BeamInput;
  update: (patch: Partial<BeamInput>) => void;
  options?: LoadOptions;
  result?: LoadsResult;
  error?: string;
}

const fmt = (v: number | null | undefined, d = 2) =>
  v === null || v === undefined || !Number.isFinite(v) ? "–" : v.toLocaleString("sv-SE", { maximumFractionDigits: d });

const TYPE_LABEL: Record<LoadType, string> = {
  udl: "Utbredd, hela balken",
  partial: "Delutbredd",
  point: "Punktlast",
};

// Vad varje grupp av kombinationer används till, för en junior konstruktör.
const GROUP_HELP: Record<string, string> = {
  uls: "Bärförmåga för böjning och tvärkraft. EKS: 6.10a och 6.10b, den ogynnsammaste gäller. γd multipliceras på ogynnsamma laster.",
  characteristic: "Karakteristisk: irreversibla effekter, t.ex. spänningsbegränsning (EN 1992-1-1 7.2).",
  frequent: "Frekvent: reversibla effekter, t.ex. tillfällig nedböjning och vibrationer.",
  quasi_permanent: "Kvasipermanent: långtidslast för krypning, sprickbredd (EN 1992-1-1 7.3) och slutlig nedböjning (7.4).",
};

const PRESETS: { label: string; make: () => LoadCaseInput }[] = [
  {
    label: "Permanent last",
    make: () => ({ id: newId("c"), name: "Permanent last", kind: "permanent", loads: [{ id: newId("l"), type: "udl", value: 1, unit: "kN/m2" }] }),
  },
  {
    label: "Nyttig last",
    make: () => ({ id: newId("c"), name: "Nyttig last", kind: "variable", category: "B", loads: [{ id: newId("l"), type: "udl", value: 2.5, unit: "kN/m2" }] }),
  },
  {
    label: "Snö",
    make: () => ({ id: newId("c"), name: "Snölast", kind: "variable", category: "snow", snow: { sk: 2.0, mu: 0.8 }, loads: [] }),
  },
  {
    label: "Vind",
    make: () => ({ id: newId("c"), name: "Vindlast", kind: "variable", category: "wind", loads: [{ id: newId("l"), type: "udl", value: 0.5, unit: "kN/m2" }] }),
  },
  {
    label: "Punktlast",
    make: () => ({ id: newId("c"), name: "Punktlast", kind: "permanent", loads: [{ id: newId("l"), type: "point", value: 20, unit: "kN", a_m: 2 }] }),
  },
];

export function LoadsStep({ beam, update, options, result, error }: Props) {
  const [hover, setHover] = useState<string | null>(null);
  const setCase = (id: string, patch: Partial<LoadCaseInput>) =>
    update({ loadCases: beam.loadCases.map((lc) => (lc.id === id ? { ...lc, ...patch } : lc)) });
  const setLoad = (lc: LoadCaseInput, lid: string, patch: Partial<LoadInput>) =>
    setCase(lc.id, { loads: lc.loads.map((l) => (l.id === lid ? { ...l, ...patch } : l)) });
  const removeCase = (id: string) => update({ loadCases: beam.loadCases.filter((lc) => lc.id !== id) });
  const gammaD = options?.safety_classes[String(beam.safety_class)]?.gamma_d;
  // Lastfallens beteckningar (G1, Q1 …) kommer från kärnan i samma ordning.
  const caseIds = result?.cases.map((c) => c.id) ?? [];

  const psiCategories = options
    ? Object.entries(options.psi).filter(([k]) => !k.startsWith("snow"))
    : [];

  return (
    <div className="step-grid loads-grid">
      <div className="stack">
        <section className="card">
          <h2>Förutsättningar</h2>
          {options && (
            <label className="field" title="EKS avd. A: säkerhetsklass efter risken för allvarliga personskador. Ger partialkoefficienten γd som multipliceras på ogynnsamma laster i brottgräns.">
              <span className="field-label">
                Säkerhetsklass<span className="help-dot" aria-hidden>?</span>
              </span>
              <select value={beam.safety_class} onChange={(e) => update({ safety_class: Number(e.target.value) as 1 | 2 | 3 })}>
                {Object.entries(options.safety_classes).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v.label} (γd = {fmt(v.gamma_d)})
                  </option>
                ))}
              </select>
            </label>
          )}
          <p className="muted small">
            Bjälklagsbalkar i vanliga kontor och bostäder hamnar ofta i säkerhetsklass 2. Klass 3 gäller där ett brott
            ger stor risk för allvarliga personskador. Se EKS avd. A för vilka byggnadsdelar som avses.
          </p>
          <NumberField
            label="Belastningsbredd"
            symbol="c"
            unit="m"
            value={beam.width_m}
            step={0.1}
            help="Bredden av bjälklaget som balken bär (c/c-avstånd mellan balkarna). Ytlaster i kN/m² multipliceras med c och blir linjelaster i kN/m."
            onChange={(v) => update({ width_m: v })}
          />
          {beam.spans_m.length > 1 && (
            <label className="check" title="EN 1992-1-1 5.1.3 och Bärande konstruktioner del 1 fig. K1.12: en fri variabel last placeras där den verkar ogynnsamt. Programmet prövar varje fack för sig, vilket täcker de förenklade uppställningarna (a) varannat fack och (b) två intilliggande fack.">
              <input type="checkbox" checked={beam.pattern} onChange={(e) => update({ pattern: e.target.checked })} />
              Mönsterbelastning: variabel last fack för fack där den verkar ogynnsamt
            </label>
          )}
        </section>

        <section className="card">
          <h2>Lastfall</h2>
          <p className="muted small">
            Ett lastfall per oberoende last. Laster som alltid verkar samtidigt (t.ex. bjälklag och golv) läggs i samma
            permanenta lastfall. Nyttig last, snö och vind är egna variabla lastfall, eftersom de kombineras med
            ψ-faktorer.
          </p>
          {beam.loadCases.map((lc, i) => {
            const cid = caseIds[i];
            const psiKey = lc.category === "snow" ? result?.cases[i]?.category : lc.category;
            const psi = psiKey ? options?.psi[psiKey] : undefined;
            const suggestions = options
              ? Object.entries(options.imposed).filter(([, v]) => v.psi === lc.category)
              : [];
            return (
              <div
                key={lc.id}
                className={`case-card ${caseColor(beam.loadCases, i)}`}
                onMouseEnter={() => setHover(cid ?? null)}
                onMouseLeave={() => setHover(null)}
              >
                <div className="case-head">
                  <span className="case-id">{cid ?? "…"}</span>
                  <input className="case-name" value={lc.name} onChange={(e) => setCase(lc.id, { name: e.target.value })} aria-label="Lastfallets namn" />
                  <button className="btn ghost small" onClick={() => removeCase(lc.id)} title="Ta bort lastfallet" aria-label="Ta bort lastfallet">
                    ✕
                  </button>
                </div>
                <div className="row">
                  <label className="field" title="Permanent last (G) verkar hela tiden: egentyngd, bjälklag, golv, installationer. Variabel last (Q) varierar: nyttig last, snö, vind. EN 1990 4.1.1.">
                    <span className="field-label">
                      Typ<span className="help-dot" aria-hidden>?</span>
                    </span>
                    <select
                      value={lc.kind}
                      onChange={(e) => {
                        const kind = e.target.value as LoadCaseInput["kind"];
                        setCase(lc.id, kind === "permanent" ? { kind, category: undefined, snow: undefined } : { kind, category: "B", self_weight: false });
                      }}
                    >
                      <option value="permanent">Permanent (G)</option>
                      <option value="variable">Variabel (Q)</option>
                    </select>
                  </label>
                  {lc.kind === "variable" && options && (
                    <label className="field" title="Kategorin bestämmer ψ-faktorerna (EN 1990 tabell A1.1, EKS avd. B). För snö väljs raden efter s_k.">
                      <span className="field-label">
                        Kategori<span className="help-dot" aria-hidden>?</span>
                      </span>
                      <select
                        value={lc.category}
                        onChange={(e) => {
                          const category = e.target.value;
                          setCase(lc.id, category === "snow" ? { category, snow: lc.snow ?? { sk: 2, mu: 0.8 } } : { category, snow: undefined });
                        }}
                      >
                        {psiCategories.map(([k, v]) => (
                          <option key={k} value={k}>
                            {v.name}
                          </option>
                        ))}
                        <option value="snow">Snö (ψ efter s_k)</option>
                      </select>
                    </label>
                  )}
                </div>
                {psi && lc.kind === "variable" && (
                  <div className="psi-row" title="ψ0: kombinationsvärde, ψ1: frekvent värde, ψ2: kvasipermanent värde. EN 1990 tabell A1.1.">
                    <span>
                      <Tex tex="\psi_0" /> = {fmt(psi.psi0)}
                    </span>
                    <span>
                      <Tex tex="\psi_1" /> = {fmt(psi.psi1)}
                    </span>
                    <span>
                      <Tex tex="\psi_2" /> = {fmt(psi.psi2)}
                    </span>
                    <span className="muted">{psi.name}</span>
                  </div>
                )}
                {lc.kind === "permanent" && (
                  <label className="check" title="Armerad betong 25 kN/m³ (EN 1991-1-1 tabell A.1) gånger tvärsnittets b·h.">
                    <input type="checkbox" checked={Boolean(lc.self_weight)} onChange={(e) => setCase(lc.id, { self_weight: e.target.checked })} />
                    Balkens egentyngd: 25 kN/m³ · {fmt(beam.b_mm / 1000, 3)} · {fmt(beam.h_mm / 1000, 3)} m ={" "}
                    <strong>{fmt((25 * beam.b_mm * beam.h_mm) / 1e6)} kN/m</strong>
                  </label>
                )}
                {lc.category === "snow" && lc.snow && (
                  <div className="row">
                    <NumberField
                      label="Snölast på mark"
                      symbol="s_k"
                      unit="kN/m²"
                      value={lc.snow.sk}
                      step={0.5}
                      help="Karakteristisk snölast på mark för orten, EKS avd. B (snözonkarta). Bestämmer också ψ-faktorerna."
                      onChange={(v) => setCase(lc.id, { snow: { ...lc.snow!, sk: v } })}
                    />
                    <NumberField
                      label="Formfaktor"
                      symbol="\mu_1"
                      value={lc.snow.mu}
                      step={0.1}
                      help="EN 1991-1-3 tabell 5.2: 0,8 för taklutning 0–30°. Ce = Ct = 1,0."
                      onChange={(v) => setCase(lc.id, { snow: { ...lc.snow!, mu: v } })}
                    />
                  </div>
                )}
                {suggestions.length > 0 && (
                  <div className="chips" title={options?.imposed_note}>
                    {suggestions.map(([k, v]) => (
                      <button
                        key={k}
                        className="chip"
                        onClick={() => {
                          const first = lc.loads.find((l) => l.type !== "point");
                          const loads = first
                            ? lc.loads.map((l) => (l.id === first.id ? { ...l, value: v.qk, unit: "kN/m2" as const } : l))
                            : [...lc.loads, { id: newId("l"), type: "udl" as const, value: v.qk, unit: "kN/m2" as const }];
                          setCase(lc.id, { loads, name: lc.name.startsWith("Nyttig last") ? `Nyttig last, ${v.name.split("– ")[1] ?? v.name}` : lc.name });
                        }}
                      >
                        {v.name}: {fmt(v.qk)} kN/m²{options?.imposed_note.startsWith("OSÄKER") ? " ⚠" : ""}
                      </button>
                    ))}
                  </div>
                )}

                <div className="load-list">
                  {lc.loads.map((l) => (
                    <div key={l.id} className="load-row">
                      <div className="load-main">
                        <select
                          aria-label="Lasttyp"
                          value={l.type}
                          onChange={(e) => {
                            const type = e.target.value as LoadType;
                            setLoad(lc, l.id, {
                              type,
                              unit: type === "point" ? "kN" : l.unit === "kN" ? "kN/m" : l.unit,
                              a_m: type === "udl" ? undefined : (l.a_m ?? 0),
                              b_m: type === "partial" ? (l.b_m ?? beamLength(beam) / 2) : undefined,
                            });
                          }}
                        >
                          {Object.entries(TYPE_LABEL).map(([k, v]) => (
                            <option key={k} value={k}>
                              {v}
                            </option>
                          ))}
                        </select>
                        <span className="field-input compact">
                          <input
                            type="number"
                            step={0.1}
                            aria-label="Lastens storlek"
                            value={Number.isFinite(l.value) ? l.value : ""}
                            onChange={(e) => setLoad(lc, l.id, { value: parseFloat(e.target.value) })}
                          />
                          {l.type === "point" ? (
                            <span className="unit">kN</span>
                          ) : (
                            <select
                              className="unit-select"
                              aria-label="Enhet"
                              title="kN/m² är en ytlast som multipliceras med belastningsbredden c. kN/m är en linjelast direkt på balken."
                              value={l.unit}
                              onChange={(e) => setLoad(lc, l.id, { unit: e.target.value as LoadInput["unit"] })}
                            >
                              <option value="kN/m2">kN/m²</option>
                              <option value="kN/m">kN/m</option>
                            </select>
                          )}
                        </span>
                        <button
                          className="btn ghost small"
                          onClick={() => setCase(lc.id, { loads: lc.loads.filter((x) => x.id !== l.id) })}
                          aria-label="Ta bort lasten"
                          title="Ta bort lasten"
                        >
                          ✕
                        </button>
                      </div>
                      {l.type !== "udl" && (
                        <div className="load-pos" title="Läge mätt från balkens vänstra ände A">
                          <span>{l.type === "point" ? "Läge" : "Från"}</span>
                          <span className="field-input compact">
                            <input type="number" step={0.1} aria-label="a" value={l.a_m ?? 0} onChange={(e) => setLoad(lc, l.id, { a_m: parseFloat(e.target.value) })} />
                            <span className="unit">m</span>
                          </span>
                          {l.type === "partial" && (
                            <>
                              <span>till</span>
                              <span className="field-input compact">
                                <input type="number" step={0.1} aria-label="b" value={l.b_m ?? beamLength(beam)} onChange={(e) => setLoad(lc, l.id, { b_m: parseFloat(e.target.value) })} />
                                <span className="unit">m</span>
                              </span>
                            </>
                          )}
                          <span className="muted">från vänster ände A</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                <button
                  className="btn ghost small"
                  onClick={() => setCase(lc.id, { loads: [...lc.loads, { id: newId("l"), type: "udl", value: 1, unit: "kN/m2" }] })}
                >
                  + Last
                </button>
              </div>
            );
          })}
          <div className="add-row">
            <span className="muted small">Lägg till:</span>
            {PRESETS.map((p) => (
              <button key={p.label} className="chip" onClick={() => update({ loadCases: [...beam.loadCases, p.make()] })}>
                + {p.label}
              </button>
            ))}
          </div>
        </section>
      </div>

      <div className="stack">
        <section className="card">
          <h2>Laster på balken (karakteristiska värden)</h2>
          {error && <p className="warning">{error}</p>}
          {result && <LoadedBeam spans_m={beam.spans_m} supports={beam.supports} cases={result.cases} highlight={hover} />}
          {result?.warnings.map((w) => (
            <p key={w} className="warning">
              {w}
            </p>
          ))}
        </section>

        {result && <DesignSummary result={result} gammaD={gammaD} safetyClass={beam.safety_class} beam={beam} />}
      </div>
      {result && (
        <div className="full-row">
          <CombinationTable result={result} onHover={setHover} />
        </div>
      )}
    </div>
  );
}

function DesignSummary({ result, gammaD, safetyClass, beam }: { result: LoadsResult; gammaD?: number; safetyClass: number; beam: BeamInput }) {
  const uls = result.design.uls;
  const qp = result.design.quasi_permanent;
  const span = beamLength(beam);
  const supX = supportX(beam.spans_m);
  const hasNeg = (uls?.M_neg ?? 0) < -1e-6;
  const hasPos = (uls?.M_pos ?? 0) > 1e-6;
  return (
    <section className="card">
      <h2>Dimensionerande snittkrafter</h2>
      <div className="results">
        {hasPos && (
          <div className="result accent">
            <div className="result-label">
              Fältmoment <Tex tex="M_{Ed}" />
            </div>
            <div className="result-value">
              {fmt(uls?.M_pos, 1)} <span className="unit">kNm</span>
            </div>
            <div className="result-sub">{uls?.combination_M_pos_name}</div>
          </div>
        )}
        {hasNeg && (
          <div className="result accent">
            <div className="result-label">
              Stödmoment <Tex tex="M_{Ed}^{-}" />
            </div>
            <div className="result-value">
              {fmt(uls?.M_neg, 1)} <span className="unit">kNm</span>
            </div>
            <div className="result-sub">{uls?.combination_M_neg_name}</div>
          </div>
        )}
        <div className="result accent">
          <div className="result-label">
            Tvärkraft <Tex tex="V_{Ed}" />
          </div>
          <div className="result-value">
            {fmt(uls?.V, 1)} <span className="unit">kN</span>
          </div>
          <div className="result-sub">{uls?.combination_V_name}</div>
        </div>
        {qp?.w != null && (
          <div className="result">
            <div className="result-label">Nedböjning, kvasipermanent</div>
            <div className="result-value">
              {fmt(qp.w, 1)} <span className="unit">mm</span>
            </div>
            <div className="result-sub">Elastisk, osprucket, korttid</div>
          </div>
        )}
      </div>
      <p className="muted small">
        Säkerhetsklass {safetyClass} ger γd = {fmt(gammaD)}. Diagrammen visar en kombination och en lastuppställning
        i taget; välj i listan.
        {result.system.pattern && " Variabel last är placerad fack för fack där den verkar ogynnsamt."}
      </p>
      {uls && (
        <CombinationDiagrams result={result} span_m={span} supports_x={supX} initial={uls.combination_M} />
      )}
    </section>
  );
}

function CombinationTable({ result, onHover }: { result: LoadsResult; onHover: (id: string | null) => void }) {
  const groups = ["uls", "characteristic", "frequent", "quasi_permanent"] as const;
  const [open, setOpen] = useState<string | null>(null);
  const caseSym = Object.fromEntries(result.cases.map((c) => [c.id, c]));
  // q_d finns bara när alla laster är jämnt utbredda över hela spannet.
  const showQd = result.combinations.some((c) => c.q_d !== null);
  return (
    <section className="card">
      <h2>Lastkombinationer</h2>
      <p className="muted small">
        Programmet bildar alla kombinationer enligt EN 1990 med EKS. Varje variabel last får vara huvudlast i tur och
        ordning. Den kombination som ger störst moment respektive tvärkraft i varje grupp markeras som
        dimensionerande. Klicka på en rad för att se faktorerna.
      </p>
      <table className="table combo-table">
        <thead>
          <tr>
            <th>Kombination</th>
            {showQd && (
              <th className="num" title="Summan av faktor gånger last, när alla laster är jämnt utbredda">
                q<sub>d</sub> (kN/m)
              </th>
            )}
            <th>Faktorer</th>
            <th className="num">M (kNm)</th>
            <th className="num">V (kN)</th>
            <th className="bar-col" />
          </tr>
        </thead>
        <tbody>
          {groups.map((g) => {
            const rows = result.combinations.filter((c) => c.group === g);
            if (!rows.length) return null;
            const mMax = Math.max(1e-9, ...rows.map((r) => Math.max(Math.abs(r.M_max), Math.abs(r.M_min))));
            return (
              <Fragment key={g}>
                <tr className="group-row">
                  <td colSpan={showQd ? 6 : 5}>
                    <strong>{result.design[g]?.label}</strong>
                    <span className="muted small block">{GROUP_HELP[g]}</span>
                  </td>
                </tr>
                {rows.map((c) => (
                  <ComboRow
                    key={c.id}
                    c={c}
                    mMax={mMax}
                    open={open === c.id}
                    onToggle={() => setOpen(open === c.id ? null : c.id)}
                    onHover={onHover}
                    names={caseSym}
                    showQd={showQd}
                  />
                ))}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}

function ComboRow({
  c,
  mMax,
  open,
  onToggle,
  onHover,
  names,
  showQd,
}: {
  c: CombinationResult;
  showQd: boolean;
  mMax: number;
  open: boolean;
  onToggle: () => void;
  onHover: (id: string | null) => void;
  names: Record<string, { name: string }>;
}) {
  const governs = c.governs_M || c.governs_V;
  const M = Math.abs(c.M_min) > Math.abs(c.M_max) ? c.M_min : c.M_max;
  return (
    <>
      <tr className={`combo-row${governs ? " governs" : ""}`} onClick={onToggle} onMouseEnter={() => onHover(c.leading)} onMouseLeave={() => onHover(null)}>
        <td>
          <span className="combo-name">{c.name}</span>
          {governs && (
            <span className="badge">
              {c.governs_M && c.governs_V ? "Dimensionerande" : c.governs_M ? "Dimensionerande för M" : "Dimensionerande för V"}
            </span>
          )}
        </td>
        {showQd && <td className="num">{fmt(c.q_d)}</td>}
        <td className="factors">
          {Object.entries(c.factors).map(([id, f]) => (
            <span key={id} className="factor" title={names[id]?.name}>
              {fmt(f, 3)}·{id}
            </span>
          ))}
        </td>
        <td className={`num${c.governs_M ? " strong" : ""}`}>{fmt(M, 1)}</td>
        <td className={`num${c.governs_V ? " strong" : ""}`}>{fmt(c.V_abs, 1)}</td>
        <td className="bar-col">
          <span className="bar" style={{ width: `${(100 * Math.abs(M)) / mMax}%` }} />
        </td>
      </tr>
      {open && (
        <tr className="combo-detail">
          <td colSpan={showQd ? 6 : 5}>
            <Tex tex={`${c.latex}`} block />
            <Tex tex={`= ${c.latex_numeric}`} block />
            <ul className="factor-list">
              {Object.entries(c.factors).map(([id, f]) => (
                <li key={id}>
                  <strong>{id}</strong> {names[id]?.name}: faktor {fmt(f, 4)}
                </li>
              ))}
            </ul>
            <p className="muted small">
              Största fältmoment vid x = {fmt(c.x_M_max)} m
              {Object.keys(c.loaded_spans).length > 0 &&
                ` (${Object.entries(c.loaded_spans)
                  .map(([id, sp]) => `${id} på fack ${sp.join(", ") || "inget"}`)
                  .join("; ")})`}
              {c.M_min < -1e-6 && `, största negativa moment ${fmt(c.M_min, 1)} kNm vid x = ${fmt(c.x_M_min)} m`}, största
              tvärkraft vid x = {fmt(c.x_V)} m. Största upplagsreaktioner:{" "}
              {c.reactions.map((r) => `R${r.support} = ${fmt(r.max, 1)} kN`).join(", ")}. Gynnsamma variabla laster tas
              inte med, gynnsam permanent last med faktor 1,0.
            </p>
          </td>
        </tr>
      )}
    </>
  );
}
