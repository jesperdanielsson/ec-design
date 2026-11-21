import { useEffect, useMemo, useState } from "react";
import {
  api,
  type CalcLog,
  type ConcreteResult,
  type CoverResult,
  type Info,
  type LongTermResult,
  type MaterialOptions,
  type ReinforcementResult,
  type SimplySupportedResult,
} from "./api";
import { Sidebar } from "./components/Sidebar";
import { CalcLogView } from "./components/CalcLogView";
import { GeometryStep } from "./steps/GeometryStep";
import { MaterialStep } from "./steps/MaterialStep";
import { LoadsStep } from "./steps/LoadsStep";
import { AnalysisStep } from "./steps/AnalysisStep";
import { STEPS, defaultBeam, type BeamInput, type StepId } from "./model";

export default function App() {
  const [beam, setBeam] = useState<BeamInput>(defaultBeam);
  const [active, setActive] = useState<StepId>("geometry");
  const [info, setInfo] = useState<Info>();
  const [classes, setClasses] = useState<string[]>([]);
  const [grades, setGrades] = useState<string[]>([]);
  const [concrete, setConcrete] = useState<ConcreteResult>();
  const [reinforcement, setReinforcement] = useState<ReinforcementResult>();
  const [options, setOptions] = useState<MaterialOptions>();
  const [longTerm, setLongTerm] = useState<LongTermResult>();
  const [cover, setCover] = useState<CoverResult>();
  const [ss, setSs] = useState<SimplySupportedResult>();
  const [error, setError] = useState<string>();

  const update = (patch: Partial<BeamInput>) => setBeam((b) => ({ ...b, ...patch }));
  const fail = (e: unknown) => setError(e instanceof Error ? e.message : String(e));

  useEffect(() => {
    api.info().then(setInfo).catch(fail);
    api.concreteClasses().then(setClasses).catch(fail);
    api.reinforcementGrades().then(setGrades).catch(fail);
    api.materialOptions().then(setOptions).catch(fail);
  }, []);

  // Krypning och krympning beror på klass, miljö, ålder och tvärsnittets mått (h0).
  const ltValid = beam.rh_percent >= 40 && beam.rh_percent <= 100 && beam.t0_days > 0 && beam.ts_days > 0 && beam.b_mm > 0 && beam.h_mm > 0;
  useEffect(() => {
    if (!ltValid) return;
    api
      .concreteLongTerm(beam.concrete, beam.cement, beam.rh_percent, beam.b_mm, beam.h_mm, beam.drying, beam.t0_days, beam.ts_days)
      .then(setLongTerm)
      .catch(fail);
  }, [ltValid, beam.concrete, beam.cement, beam.rh_percent, beam.b_mm, beam.h_mm, beam.drying, beam.t0_days, beam.ts_days]);

  useEffect(() => {
    if (!beam.exposure.length || !(beam.stirrup_mm > 0)) return;
    api.concreteCover(beam.exposure, beam.life, beam.binder, beam.vct, beam.stirrup_mm).then(setCover).catch(fail);
  }, [beam.exposure, beam.life, beam.binder, beam.vct, beam.stirrup_mm]);

  useEffect(() => {
    api.concrete(beam.concrete).then(setConcrete).catch(fail);
  }, [beam.concrete]);

  useEffect(() => {
    api.reinforcement(beam.reinforcement).then(setReinforcement).catch(fail);
  }, [beam.reinforcement]);

  const qSum = beam.loadCases.reduce((s, lc) => s + (Number.isFinite(lc.q_kNm) ? lc.q_kNm : 0), 0);
  useEffect(() => {
    if (beam.span_m > 0) api.simplySupported(beam.span_m, qSum).then(setSs).catch(fail);
  }, [beam.span_m, qSum]);

  const logs: CalcLog[] = useMemo(() => {
    if (active === "material")
      return [concrete?.log, reinforcement?.log, ...(longTerm?.logs ?? []), cover?.log].filter(Boolean) as CalcLog[];
    if (active === "geometry") return cover ? [cover.log] : [];
    if (active === "analysis") return ss ? [ss.log] : [];
    return [];
  }, [active, concrete, reinforcement, longTerm, cover, ss]);

  const idx = STEPS.findIndex((s) => s.id === active);
  const step = STEPS[idx];

  return (
    <div className="app">
      <Sidebar active={active} beam={beam} annex={info?.annex} version={info?.version} onSelect={setActive} />

      <main className="main">
        <header className="main-head">
          <div>
            <div className="eyebrow">
              Steg {idx + 1} av {STEPS.length}
            </div>
            <h1>{step.title}</h1>
          </div>
          <div className="nav-buttons">
            <button className="btn ghost" disabled={idx === 0} onClick={() => setActive(STEPS[idx - 1].id)}>
              ← Föregående
            </button>
            <button
              className="btn primary"
              disabled={idx === STEPS.length - 1}
              onClick={() => setActive(STEPS[idx + 1].id)}
            >
              Nästa steg →
            </button>
          </div>
        </header>

        {error && (
          <div className="error" role="alert">
            Kunde inte nå beräkningskärnan: {error}
            <button className="btn ghost small" onClick={() => setError(undefined)}>
              Stäng
            </button>
          </div>
        )}

        {active === "geometry" && <GeometryStep beam={beam} update={update} cover={cover} />}
        {active === "material" && (
          <MaterialStep
            beam={beam}
            update={update}
            classes={classes}
            grades={grades}
            concrete={concrete}
            reinforcement={reinforcement}
            options={options}
            longTerm={longTerm}
            cover={cover}
          />
        )}
        {active === "loads" && <LoadsStep beam={beam} update={update} />}
        {active === "analysis" && <AnalysisStep beam={beam} update={update} result={ss} />}
      </main>

      <aside className="log-panel" aria-label="Lösningsgång">
        <div className="log-head">
          <h2>Lösningsgång</h2>
          <p className="muted small">Samma steg som i rapporten, med normhänvisning.</p>
        </div>
        {logs.length ? (
          logs.map((l) => <CalcLogView key={l.title} log={l} />)
        ) : (
          <p className="muted small">Inga beräkningar i det här steget ännu.</p>
        )}
      </aside>
    </div>
  );
}
