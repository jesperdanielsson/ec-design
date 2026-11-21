import type { CalcLog } from "../api";
import { Tex } from "./Tex";

// Lösningsgången: samma logg som rapporten och testerna använder.
export function CalcLogView({ log }: { log?: CalcLog }) {
  if (!log) return <p className="muted">Ingen beräkning ännu.</p>;
  return (
    <div className="calclog">
      <h3>{log.title}</h3>
      <ol>
        {log.steps.map((s, i) => (
          <li key={i} className="calc-step">
            <div className="calc-desc">{s.description}</div>
            <Tex tex={s.latex} block />
            {s.ref && <div className="calc-ref">{s.ref}</div>}
          </li>
        ))}
      </ol>
    </div>
  );
}
