import { SelectField } from "../components/Field";
import { StressStrainChart } from "../components/StressStrainChart";
import { Tex } from "../components/Tex";
import type { ConcreteResult, ReinforcementResult } from "../api";
import type { BeamInput } from "../model";

interface Props {
  beam: BeamInput;
  update: (patch: Partial<BeamInput>) => void;
  classes: string[];
  grades: string[];
  concrete?: ConcreteResult;
  reinforcement?: ReinforcementResult;
}

const fmt = (v: number | string | undefined, d = 2) =>
  typeof v === "number" ? v.toLocaleString("sv-SE", { maximumFractionDigits: d }) : (v ?? "–");

function Prop({ label, symbol, value, unit }: { label: string; symbol: string; value: string; unit?: string }) {
  return (
    <div className="prop">
      <div className="prop-label">{label}</div>
      <div className="prop-value">
        {symbol && (
          <span className="prop-symbol">
            <Tex tex={symbol} />
          </span>
        )}{" "}
        {value}
        {unit && <span className="unit"> {unit}</span>}
      </div>
    </div>
  );
}

export function MaterialStep({ beam, update, classes, grades, concrete, reinforcement }: Props) {
  const p = concrete?.properties;
  const r = reinforcement?.properties;
  return (
    <div className="step-grid">
      <section className="card">
        <h2>Betong</h2>
        <SelectField
          label="Hållfasthetsklass"
          value={beam.concrete}
          options={classes}
          help="EN 1992-1-1 tabell 3.1. Cylinder-/kubhållfasthet i MPa."
          onChange={(v) => update({ concrete: v })}
        />
        {p && (
          <div className="props">
            <Prop label="Karakteristisk tryckhållfasthet" symbol="f_{ck}" value={fmt(p.fck)} unit="MPa" />
            <Prop label="Medeltryckhållfasthet" symbol="f_{cm}" value={fmt(p.fcm)} unit="MPa" />
            <Prop label="Medeldraghållfasthet" symbol="f_{ctm}" value={fmt(p.fctm)} unit="MPa" />
            <Prop label="E-modul" symbol="E_{cm}" value={fmt(p.Ecm, 1)} unit="GPa" />
            <Prop label="Dimensionerande tryckhållfasthet" symbol="f_{cd}" value={fmt(p.fcd)} unit="MPa" />
            <Prop label="Brottstukning" symbol="\varepsilon_{cu2}" value={fmt(p.eps_cu2)} unit="‰" />
          </div>
        )}

        <h2>Armering</h2>
        <SelectField
          label="Armeringstyp"
          value={beam.reinforcement}
          options={grades}
          help="EN 1992-1-1 3.2 och bilaga C."
          onChange={(v) => update({ reinforcement: v })}
        />
        {r && (
          <div className="props">
            <Prop label="Flytgräns" symbol="f_{yk}" value={fmt(r.fyk)} unit="MPa" />
            <Prop label="Dimensionerande flytgräns" symbol="f_{yd}" value={fmt(r.fyd, 1)} unit="MPa" />
            <Prop label="E-modul" symbol="E_s" value={fmt(r.Es)} unit="GPa" />
            <Prop label="Duktilitetsklass" symbol="" value={String(r.ductility)} />
          </div>
        )}

        <details className="later">
          <summary>Krypning, krympning och vct</summary>
          <p className="muted small">
            Kryptal φ(t,t₀), krympning och vct-krav per exponeringsklass kommer i nästa steg i planen (EN 1992-1-1
            3.1.4 och bilaga B).
          </p>
        </details>
      </section>

      <section className="card visual">
        <h2>Spänning–töjning, parabel-rektangel</h2>
        {concrete && p ? (
          <StressStrainChart curve={concrete.curve} fcd={p.fcd} epsC2={p.eps_c2} epsCu2={p.eps_cu2} />
        ) : (
          <p className="muted">Laddar…</p>
        )}
        <p className="muted small">EN 1992-1-1 3.1.7, ekv. (3.17)–(3.18). Bilinjärt samband läggs till senare.</p>
      </section>
    </div>
  );
}
