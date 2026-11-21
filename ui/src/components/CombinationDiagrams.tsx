import { useEffect, useMemo, useState } from "react";
import type { CombinationResult, LoadsResult } from "../api";
import { ForceDiagram } from "./ForceDiagram";

interface Props {
  result: LoadsResult;
  span_m: number;
  supports_x: number[];
  /** Visa bara kombinationer i den här gruppen (t.ex. "uls"). Annars alla. */
  group?: CombinationResult["group"];
  /** Kombination som väljs från början. */
  initial?: string;
}

const fmt = (v: number, d = 1) => v.toLocaleString("sv-SE", { maximumFractionDigits: d });

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/** "fältmoment i fack 1", "fältmoment i fack 3" -> "fältmoment i fack 1 och 3". */
function purposeText(purposes: string[]): string {
  const groups = new Map<string, string[]>();
  for (const p of purposes) {
    const m = p.match(/^(.* i (?:fack )?)(\S+)$/);
    const [head, tail] = m ? [m[1], m[2]] : [p, ""];
    groups.set(head, [...(groups.get(head) ?? []), tail]);
  }
  const join = (xs: string[]) => (xs.length > 1 ? `${xs.slice(0, -1).join(", ")} och ${xs[xs.length - 1]}` : xs[0]);
  return cap([...groups].map(([h, t]) => (t[0] ? h + join(t) : h)).join(", "));
}

function argExtreme(vals: number[], sign: 1 | -1) {
  let best = 0;
  for (let i = 1; i < vals.length; i++) if (sign * vals[i] > sign * vals[best]) best = i;
  return best;
}

// Diagram för en kombination och en lastuppställning i taget: en kurva per storhet, som i en
// handräkning. Med mönsterbelastning har en kombination flera uppställningar (t.ex. nyttig last
// i fack 1 för fältmomentet, i fack 1 och 2 för stödmomentet), och man väljer vilken som visas.
export function CombinationDiagrams({ result, span_m, supports_x, group, initial }: Props) {
  const combos = useMemo(
    () => result.combinations.filter((c) => !group || c.group === group),
    [result.combinations, group],
  );
  const [cid, setCid] = useState(initial ?? combos[0]?.id);
  const [ai, setAi] = useState(0);
  useEffect(() => {
    if (!combos.some((c) => c.id === cid)) setCid(initial ?? combos[0]?.id);
  }, [combos, cid, initial]);
  useEffect(() => setAi(0), [cid]);
  const combo = combos.find((c) => c.id === cid) ?? combos[0];
  if (!combo) return null;
  const arr = combo.arrangements[Math.min(ai, combo.arrangements.length - 1)];
  if (!arr) return null;
  const x = result.diagrams.x;
  const loaded = Object.entries(arr.loaded_spans);
  const sls = combo.group !== "uls";

  const notes = (q: "M" | "V" | "w", vals: number[]) => {
    const peaks = arr.peaks.filter((p) => p.quantity === q).map((p) => ({ x: p.x, value: p.value, label: q === "w" ? "δ" : q }));
    if (peaks.length) return peaks;
    const out = [];
    const iMax = argExtreme(vals, 1);
    const iMin = argExtreme(vals, -1);
    if (vals[iMax] > 1e-6) out.push({ x: x[iMax], value: vals[iMax], label: q === "w" ? "δ" : `${q} max` });
    if (vals[iMin] < -1e-6) out.push({ x: x[iMin], value: vals[iMin], label: q === "w" ? "δ" : `${q} min` });
    return out;
  };

  return (
    <div className="combo-diagrams">
      <label className="field">
        <span className="field-label">Lastkombination</span>
        <select value={combo.id} onChange={(e) => setCid(e.target.value)}>
          {combos.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
              {c.governs_M || c.governs_V ? " (dimensionerande)" : ""}
            </option>
          ))}
        </select>
      </label>
      {combo.arrangements.length > 1 && (
        <div className="tabs" role="tablist" aria-label="Lastuppställning">
          {combo.arrangements.map((a, i) => (
            <button
              key={i}
              role="tab"
              aria-selected={i === ai}
              className={`chip${i === ai ? " active" : ""}`}
              onClick={() => setAi(i)}
              title={Object.entries(a.loaded_spans)
                .map(([id, sp]) => `${id} på fack ${sp.join(", ") || "inget"}`)
                .join("; ")}
            >
              {purposeText(a.purposes)}
            </button>
          ))}
        </div>
      )}
      <p className="muted small">
        {Object.entries(arr.factors)
          .filter(([, f]) => f !== 0)
          .map(([id, f]) => `${fmt(f, 3)}·${id}`)
          .join(" + ")}
        {loaded.length > 0 && ` · ${loaded.map(([id, sp]) => `${id} på fack ${sp.join(", ") || "inget"}`).join("; ")}`}
        {combo.arrangements.length > 1 && ". Varje knapp är en lastuppställning: den ger största värdet för det som står på knappen."}
      </p>
      <ForceDiagram
        title="M"
        quantity="M"
        x={x}
        span_m={span_m}
        supports_x={supports_x}
        unit="kNm"
        downPositive
        series={[{ label: combo.name, values: arr.M, fill: true }]}
        annotate={notes("M", arr.M)}
      />
      <ForceDiagram
        title="V"
        quantity="V"
        x={x}
        span_m={span_m}
        supports_x={supports_x}
        unit="kN"
        series={[{ label: combo.name, values: arr.V, fill: true }]}
        annotate={notes("V", arr.V)}
      />
      {sls && arr.w && (
        <ForceDiagram
          title="δ"
          quantity="w"
          x={x}
          span_m={span_m}
          supports_x={supports_x}
          unit="mm"
          downPositive
          series={[{ label: combo.name, values: arr.w, fill: true }]}
          annotate={notes("w", arr.w)}
        />
      )}
    </div>
  );
}
