import { useState } from "react";
import { NumberField, SelectField } from "../components/Field";
import { StressStrainChart } from "../components/StressStrainChart";
import { LineChart, TIME_TICKS } from "../components/LineChart";
import { Tex } from "../components/Tex";
import type { ConcreteResult, CoverResult, LongTermResult, MaterialOptions, ReinforcementResult } from "../api";
import { beamLength, type BeamInput } from "../model";

interface Props {
  beam: BeamInput;
  update: (patch: Partial<BeamInput>) => void;
  classes: string[];
  grades: string[];
  concrete?: ConcreteResult;
  reinforcement?: ReinforcementResult;
  options?: MaterialOptions;
  longTerm?: LongTermResult;
  cover?: CoverResult;
}

const fmt = (v: number | string | undefined | null, d = 2) =>
  typeof v === "number" ? v.toLocaleString("sv-SE", { maximumFractionDigits: d }) : (v ?? "–");

function Prop({
  label,
  symbol,
  value,
  unit,
  highlight,
}: {
  label: string;
  symbol: string;
  value: string;
  unit?: string;
  highlight?: boolean;
}) {
  return (
    <div className={`prop${highlight ? " highlight" : ""}`}>
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

type Tab = "sigma" | "strength" | "creep" | "shrinkage";
const TABS: { id: Tab; label: string }[] = [
  { id: "sigma", label: "σ–ε" },
  { id: "strength", label: "Hållfasthet" },
  { id: "creep", label: "Krypning" },
  { id: "shrinkage", label: "Krympning" },
];

export function MaterialStep({ beam, update, classes, grades, concrete, reinforcement, options, longTerm, cover }: Props) {
  const [tab, setTab] = useState<Tab>("sigma");
  const p = concrete?.properties;
  const r = reinforcement?.properties;

  const toggleExposure = (cls: string) => {
    const has = beam.exposure.includes(cls);
    const next = has ? beam.exposure.filter((c) => c !== cls) : [...beam.exposure, cls];
    // X0 betyder "ingen risk" och kombineras inte med andra klasser.
    const cleaned = cls === "X0" && !has ? ["X0"] : next.filter((c) => c !== "X0" || next.length === 1);
    if (cleaned.length) update({ exposure: cleaned });
  };
  const groups = options
    ? Object.entries(options.exposure).reduce<Record<string, string[]>>((acc, [k, v]) => {
        (acc[v.group] ??= []).push(k);
        return acc;
      }, {})
    : {};

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
        {options && (
          <label className="field" title="Cementklass enligt EN 1992-1-1 3.1.2(6). Påverkar hållfasthetstillväxt, krypning och krympning. Byggcement (CEM II/A-LL 42,5 R) är klass R, anläggningscement (CEM I 42,5 N) är klass N.">
            <span className="field-label">
              Cementklass<span className="help-dot" aria-hidden>?</span>
            </span>
            <select value={beam.cement} onChange={(e) => update({ cement: e.target.value as BeamInput["cement"] })}>
              {Object.entries(options.cements).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </label>
        )}
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

        <h2>Miljö och tid</h2>
        <p className="muted small">
          Används för krypning och krympning (EN 1992-1-1 3.1.4 och bilaga B). Gäller vid 20 °C och betongspänning högst
          0,45·f<sub>ck</sub>(t<sub>0</sub>).
        </p>
        <NumberField
          label="Relativ fuktighet"
          symbol="RH"
          unit="%"
          value={beam.rh_percent}
          min={40}
          help="Omgivningens relativa fuktighet, 40–100 %. Torrare luft ger mer krypning och krympning."
          onChange={(v) => update({ rh_percent: v })}
        />
        <div className="chips">
          <button className={`chip${beam.rh_percent === 50 ? " on" : ""}`} onClick={() => update({ rh_percent: 50 })}>
            Inomhus, uppvärmt 50 %
          </button>
          <button className={`chip${beam.rh_percent === 80 ? " on" : ""}`} onClick={() => update({ rh_percent: 80 })}>
            Utomhus 80 %
          </button>
        </div>
        {beam.rh_percent < 40 && <p className="warning">Modellen gäller för RH mellan 40 och 100 %.</p>}
        {options && (
          <label className="field" title="Avgör omkretsen u som torkar ut och därmed nominell tjocklek h0 = 2Ac/u. EN 1992-1-1 3.1.4(5).">
            <span className="field-label">
              Uttorkning<span className="help-dot" aria-hidden>?</span>
            </span>
            <select value={beam.drying} onChange={(e) => update({ drying: e.target.value as BeamInput["drying"] })}>
              {Object.entries(options.drying).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </label>
        )}
        <div className="row">
          <NumberField
            label="Ålder vid pålastning"
            symbol="t_0"
            unit="dygn"
            value={beam.t0_days}
            help="Betongens ålder när lasten först verkar (t.ex. formrivning). Tidig pålastning ger större kryptal. Bilaga B.1."
            onChange={(v) => update({ t0_days: v })}
          />
          <NumberField
            label="Uttorkning börjar"
            symbol="t_s"
            unit="dygn"
            value={beam.ts_days}
            help="Betongens ålder när härdningen slutar och uttorkningen börjar. EN 1992-1-1 3.1.4(6)."
            onChange={(v) => update({ ts_days: v })}
          />
        </div>
        {longTerm && (
          <div className="props">
            <Prop label="Nominell tjocklek" symbol="h_0" value={fmt(longTerm.h0, 1)} unit="mm" />
            <Prop label="Slutligt kryptal" symbol="\varphi(\infty,t_0)" value={fmt(longTerm.creep.phi_inf)} highlight />
            <Prop label="Effektiv E-modul" symbol="E_{c,eff}" value={fmt(longTerm.creep.Ec_eff, 1)} unit="GPa" />
            <Prop label="Slutlig krympning" symbol="\varepsilon_{cs}(\infty)" value={fmt(longTerm.shrinkage.eps_cs_inf, 3)} unit="‰" highlight />
          </div>
        )}

        <h2>Beständighet och täckskikt</h2>
        {options && (
          <>
            <div className="field" title="Exponeringsklasser för armeringskorrosion, EN 1992-1-1 tabell 4.1. Välj alla som gäller; den strängaste styr.">
              <span className="field-label">
                Exponeringsklass<span className="help-dot" aria-hidden>?</span>
              </span>
              {Object.entries(groups).map(([group, list]) => (
                <div key={group} className="chip-group">
                  <div className="chip-group-label">{group}</div>
                  <div className="chips">
                    {list.map((cls) => (
                      <button
                        key={cls}
                        className={`chip${beam.exposure.includes(cls) ? " on" : ""}`}
                        title={options.exposure[cls].text}
                        onClick={() => toggleExposure(cls)}
                      >
                        {cls}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
              <ul className="exposure-text small muted">
                {beam.exposure.map((cls) => (
                  <li key={cls}>
                    <strong>{cls}</strong>: {options.exposure[cls]?.text}
                  </li>
                ))}
              </ul>
            </div>
            <label className="field" title="Avsedd livslängd. EKS: L100, L50 och L20 avser 100, 50 och 20 år.">
                <span className="field-label">
                  Livslängdsklass<span className="help-dot" aria-hidden>?</span>
                </span>
                <select value={beam.life} onChange={(e) => update({ life: e.target.value as BeamInput["life"] })}>
                  {Object.entries(options.lives).map(([k, v]) => (
                    <option key={k} value={k}>
                      {k}: {v}
                    </option>
                  ))}
                </select>
              </label>
            <label className="field" title="Bindemedlets andel portlandcementklinker. Påverkar kraven i klass XC2–XC4 (EKS tabell D-1).">
              <span className="field-label">
                Bindemedel<span className="help-dot" aria-hidden>?</span>
              </span>
              <select value={beam.binder} onChange={(e) => update({ binder: e.target.value })}>
                {Object.entries(options.binders).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </label>
            <div className="row">
              <NumberField
                label="Betongens vct"
                symbol="\mathrm{vct}_{ekv}"
                step={0.05}
                value={beam.vct ?? NaN}
                help="Ekvivalent vattencementtal. Lämna tomt för att använda högsta tillåtna. Lägre vct ger tätare betong och kan ge mindre täckskikt."
                onChange={(v) => update({ vct: Number.isFinite(v) ? v : null })}
              />
              <NumberField
                label="Bygeldiameter"
                symbol="\phi"
                unit="mm"
                value={beam.stirrup_mm}
                help="Diametern på yttersta stången (normalt bygeln). Ger c_min,b = φ, EN 1992-1-1 tabell 4.2."
                onChange={(v) => update({ stirrup_mm: v })}
              />
            </div>
          </>
        )}
        {cover && (
          <>
            <div className="props">
              <Prop
                label="Högsta tillåtna vct"
                symbol=""
                value={cover.vct_max === null ? "inget krav" : fmt(cover.vct_max)}
                highlight
              />
              <Prop label="För beständighet" symbol="c_{min,dur}" value={fmt(cover.cmin_dur)} unit="mm" />
              <Prop label="Minsta täckskikt" symbol="c_{min}" value={fmt(cover.cmin)} unit="mm" />
              <Prop label="Nominellt täckskikt" symbol="c_{nom}" value={fmt(cover.cnom)} unit="mm" highlight />
            </div>
            {cover.warnings.map((w) => (
              <p key={w} className="warning">
                {w}
              </p>
            ))}
            {beam.cover_mm < cover.cnom ? (
              <p className="warning">
                Täckskiktet i geometrin är {beam.cover_mm} mm, mindre än c<sub>nom</sub>.{" "}
                <button className="btn ghost small" onClick={() => update({ cover_mm: cover.cnom })}>
                  Använd {cover.cnom} mm
                </button>
              </p>
            ) : (
              <p className="ok-note">Täckskiktet i geometrin ({beam.cover_mm} mm) uppfyller kravet.</p>
            )}
            <p className="muted small">
              c<sub>nom</sub> = c<sub>min</sub> + Δc<sub>dev</sub> ({fmt(cover.delta_c_dev)} mm). Krav enligt EKS tabell D-1.
              Frost (XF), kemiskt angrepp (XA), brand och spännarmering ingår inte än.
            </p>
          </>
        )}
      </section>

      <section className="card visual">
        <div className="tabs" role="tablist">
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={tab === t.id}
              className={`tab${tab === t.id ? " active" : ""}`}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === "sigma" &&
          (concrete && p ? (
            <>
              <h2>Parabel-rektangel, dimensionerande</h2>
              <StressStrainChart curve={concrete.curve} fcd={p.fcd} epsC2={p.eps_c2} epsCu2={p.eps_cu2} />
              <Explain>
                Sambandet används när man räknar bärförmåga i brottgränstillståndet. Betongen tar tryck upp till f<sub>cd</sub>{" "}
                vid töjningen ε<sub>c2</sub> och går sönder vid ε<sub>cu2</sub>. Draghållfastheten räknas inte med.
                <Ref>EN 1992-1-1 3.1.7, ekv. (3.17)–(3.18), figur 3.3</Ref>
              </Explain>
            </>
          ) : (
            <p className="muted">Laddar…</p>
          ))}

        {tab === "strength" && longTerm && p && (
          <>
            <h2>Medeltryckhållfasthet och E-modul över tid</h2>
            <div className="props">
              <Prop
                label={`f_cm vid pålastning (${fmt(beam.t0_days, 0)} d)`}
                symbol="f_{cm}(t_0)"
                value={fmt(longTerm.strength_at_t0.fcm, 1)}
                unit="MPa"
              />
              <Prop label="E-modul vid pålastning" symbol="E_{cm}(t_0)" value={fmt(longTerm.strength_at_t0.Ecm, 1)} unit="GPa" />
            </div>
            <LineChart
              ariaLabel="Hållfasthet över tid"
              logX
              xTicks={TIME_TICKS}
              xLabel="Betongens ålder t (dygn, logaritmisk skala)"
              yLabel="MPa"
              series={[
                { label: "f_cm(t)", points: longTerm.strength_curve.map((d) => [d.t, d.fcm]) },
                { label: "f_ck(t)", points: longTerm.strength_curve.map((d) => [d.t, d.fck]), className: "curve-2" },
              ]}
              markers={
                beam.t0_days === 28
                  ? [{ x: 28, label: "28 d = t₀" }]
                  : [
                      { x: 28, label: "28 d" },
                      { x: beam.t0_days, label: "t₀" },
                    ]
              }
            />
            <Explain>
              Hållfasthetsklassen gäller vid 28 dygn. Före dess är betongen svagare, vilket spelar roll vid tidig formrivning
              eller pålastning. Snabbt hårdnande cement (klass R) når högre värden tidigt. Efter 28 dygn räknas ingen ökning
              av f<sub>ck</sub>.
              <Ref>EN 1992-1-1 3.1.2(5)–(6), ekv. (3.1)–(3.2), och 3.1.3(3)</Ref>
            </Explain>
          </>
        )}

        {tab === "creep" && longTerm && (
          <>
            <h2>Kryptal över tid</h2>
            <div className="props">
              <Prop label="Slutligt kryptal" symbol="\varphi(\infty,t_0)" value={fmt(longTerm.creep.phi_inf)} highlight />
              <Prop label="Effektiv E-modul" symbol="E_{c,eff}" value={fmt(longTerm.creep.Ec_eff, 1)} unit="GPa" />
              <Prop label="Fuktighet" symbol="\varphi_{RH}" value={fmt(longTerm.creep.phi_RH, 3)} />
              <Prop label="Ålder vid pålastning" symbol="\beta(t_0)" value={fmt(longTerm.creep.beta_t0, 3)} />
            </div>
            <LineChart
              ariaLabel="Kryptal över tid"
              logX
              xTicks={TIME_TICKS}
              xLabel="Tid t (dygn, logaritmisk skala)"
              yLabel="φ(t, t₀)"
              series={[{ label: "φ(t, t₀)", points: longTerm.creep.curve }]}
              markers={[{ y: longTerm.creep.phi_inf, label: `φ(∞, t₀) = ${fmt(longTerm.creep.phi_inf)}` }]}
            />
            <Explain>
              Under långvarig last fortsätter betongen att deformeras. Kryptalet anger hur mycket större den slutliga
              töjningen blir än den elastiska: med φ = {fmt(longTerm.creep.phi_inf)} blir töjningen{" "}
              {fmt(1 + longTerm.creep.phi_inf)} gånger större. Därför används E<sub>c,eff</sub> = E<sub>cm</sub>/(1 + φ) för
              nedböjning och sprickor av långtidslast. Torr luft, tunna tvärsnitt och tidig pålastning ger mer krypning.
              <Ref>EN 1992-1-1 3.1.4(2), bilaga B.1, ekv. (B.1)–(B.9) och 7.4.3(5)</Ref>
            </Explain>
          </>
        )}

        {tab === "shrinkage" && longTerm && (
          <>
            <h2>Krympning över tid</h2>
            <div className="props">
              <Prop label="Slutlig total krympning" symbol="\varepsilon_{cs}(\infty)" value={fmt(longTerm.shrinkage.eps_cs_inf, 3)} unit="‰" highlight />
              <Prop label="Uttorkningskrympning" symbol="\varepsilon_{cd}(\infty)" value={fmt(longTerm.shrinkage.eps_cd_inf, 3)} unit="‰" />
              <Prop label="Autogen krympning" symbol="\varepsilon_{ca}(\infty)" value={fmt(longTerm.shrinkage.eps_ca_inf, 3)} unit="‰" />
              <Prop label="Tvärsnittets storlek" symbol="k_h" value={fmt(longTerm.shrinkage.kh, 3)} />
            </div>
            <LineChart
              ariaLabel="Krympning över tid"
              logX
              xTicks={TIME_TICKS}
              xLabel="Betongens ålder t (dygn, logaritmisk skala)"
              yLabel="‰"
              series={[
                { label: "Total ε_cs", points: longTerm.shrinkage.curve.map((d) => [d.t, d.eps_cs]) },
                { label: "Uttorkning ε_cd", points: longTerm.shrinkage.curve.map((d) => [d.t, d.eps_cd]), className: "curve-2" },
                { label: "Autogen ε_ca", points: longTerm.shrinkage.curve.map((d) => [d.t, d.eps_ca]), className: "curve-3", dashed: true },
              ]}
            />
            <Explain>
              Betongen krymper utan last: autogen krympning när cementet reagerar (de första veckorna) och
              uttorkningskrympning när fukt lämnar betongen (under många år). Om krympningen hindras av armering eller stöd
              uppstår dragspänningar och sprickor, och en osymmetriskt armerad balk böjer ut. En krympning på{" "}
              {fmt(longTerm.shrinkage.eps_cs_inf, 2)} ‰ motsvarar {fmt(longTerm.shrinkage.eps_cs_inf * beamLength(beam), 1)} mm
              förkortning av en {fmt(beamLength(beam), 1)} m lång balk.
              <Ref>EN 1992-1-1 3.1.4(6), ekv. (3.8)–(3.13), tabell 3.3 och bilaga B.2</Ref>
            </Explain>
          </>
        )}
      </section>
    </div>
  );
}

function Explain({ children }: { children: React.ReactNode }) {
  return (
    <div className="explain">
      <div className="explain-title">Vad betyder det?</div>
      <p>{children}</p>
    </div>
  );
}

function Ref({ children }: { children: React.ReactNode }) {
  return <span className="explain-ref">{children}</span>;
}
