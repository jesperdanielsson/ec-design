import { BeamDiagram } from "../components/BeamDiagram";
import type { BeamInput, LoadCaseInput } from "../model";

interface Props {
  beam: BeamInput;
  update: (patch: Partial<BeamInput>) => void;
}

const CATEGORIES: Record<string, string> = {
  A: "A – bostäder",
  B: "B – kontor",
  C: "C – samlingslokaler",
  D: "D – handel",
  E: "E – lager",
};

export function LoadsStep({ beam, update }: Props) {
  const setCase = (id: string, patch: Partial<LoadCaseInput>) =>
    update({ loadCases: beam.loadCases.map((lc) => (lc.id === id ? { ...lc, ...patch } : lc)) });

  return (
    <div className="step-grid single">
      <section className="card">
        <h2>Lastfall</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Lastfall</th>
              <th>Typ</th>
              <th>Kategori</th>
              <th className="num">q (kN/m)</th>
            </tr>
          </thead>
          <tbody>
            {beam.loadCases.map((lc) => (
              <tr key={lc.id}>
                <td>
                  <input value={lc.name} onChange={(e) => setCase(lc.id, { name: e.target.value })} />
                </td>
                <td>{lc.kind === "permanent" ? "Permanent" : "Variabel"}</td>
                <td>
                  {lc.kind === "variable" ? (
                    <select value={lc.category} onChange={(e) => setCase(lc.id, { category: e.target.value })}>
                      {Object.entries(CATEGORIES).map(([k, v]) => (
                        <option key={k} value={k}>
                          {v}
                        </option>
                      ))}
                    </select>
                  ) : (
                    "–"
                  )}
                </td>
                <td className="num">
                  <input
                    type="number"
                    value={lc.q_kNm}
                    step={0.5}
                    onChange={(e) => setCase(lc.id, { q_kNm: parseFloat(e.target.value) })}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <details className="later" open>
          <summary>Lastkombinationer</summary>
          <p className="muted small">
            Kombinationerna genereras automatiskt enligt EKS (6.10a/6.10b med γ_d för säkerhetsklass, samt
            karakteristisk, frekvent och kvasipermanent) i nästa steg i planen. Varje faktor kommer att gå att se
            och ändra.
          </p>
        </details>
      </section>

      <section className="card visual diagram-pair">
        {beam.loadCases.map((lc) => (
          <div key={lc.id}>
            <h2>{lc.name}</h2>
            <BeamDiagram span_m={beam.span_m} q_kNm={lc.q_kNm} label={lc.kind === "permanent" ? "g_k" : "q_k"} />
          </div>
        ))}
      </section>
    </div>
  );
}
