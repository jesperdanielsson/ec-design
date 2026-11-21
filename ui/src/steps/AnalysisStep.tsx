import type { SimplySupportedResult } from "../api";
import type { BeamInput } from "../model";

interface Props {
  beam: BeamInput;
  update: (patch: Partial<BeamInput>) => void;
  result?: SimplySupportedResult;
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
        <h2>Snittkrafter</h2>
        <p className="notice">
          Tillfälligt: summan av lastfallen utan lastfaktorer. Dimensionerande lastkombination enligt EKS kommer i
          nästa steg.
        </p>
        <div className="results">
          <div className="result">
            <div className="result-label">Största moment</div>
            <div className="result-value">
              {fmt(result?.M_max)} <span className="unit">kNm</span>
            </div>
          </div>
          <div className="result">
            <div className="result-label">Största tvärkraft</div>
            <div className="result-value">
              {fmt(result?.V_max)} <span className="unit">kN</span>
            </div>
          </div>
        </div>
        <h2>Utnyttjandegrader</h2>
        <p className="muted small">Böjning, tvärkraft och bruksgränskontroller visas här med färg när de är byggda.</p>
      </section>
    </div>
  );
}
