import type { LoadsResult } from "../api";
import type { BeamInput } from "../model";

interface Props {
  beam: BeamInput;
  update: (patch: Partial<BeamInput>) => void;
  result?: LoadsResult;
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

export function AnalysisStep({ beam, update, result }: Props) {
  const a = beam.analysis;
  const set = (patch: Partial<BeamInput["analysis"]>) => update({ analysis: { ...a, ...patch } });
  const fmt = (v?: number) => (v === undefined ? "–" : v.toLocaleString("sv-SE", { maximumFractionDigits: 1 }));
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
      </section>

      <section className="card visual">
        <h2>Dimensionerande snittkrafter</h2>
        <p className="muted small">Från laststeget: den ogynnsammaste kombinationen i varje grupp enligt EKS.</p>
        <table className="table">
          <thead>
            <tr>
              <th>Gränstillstånd</th>
              <th className="num">M (kNm)</th>
              <th className="num">V (kN)</th>
              <th>Kombination</th>
            </tr>
          </thead>
          <tbody>
            {result &&
              Object.entries(result.design).map(([g, d]) => (
                <tr key={g}>
                  <td>{d.label}</td>
                  <td className="num">{fmt(d.M)}</td>
                  <td className="num">{fmt(d.V)}</td>
                  <td className="muted small">{d.combination_M_name}</td>
                </tr>
              ))}
          </tbody>
        </table>
        <h2>Utnyttjandegrader</h2>
        <p className="muted small">Böjning, tvärkraft och bruksgränskontroller visas här med färg när de är byggda.</p>
      </section>
    </div>
  );
}
