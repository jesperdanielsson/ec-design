import { Tex } from "./Tex";

interface Props {
  label: string;
  symbol?: string;
  unit?: string;
  value: number;
  step?: number;
  min?: number;
  help?: string;
  onChange: (v: number) => void;
}

// Ett inmatningsfält med enhet och en kort förklaring (normhänvisning) vid hovring.
export function NumberField({ label, symbol, unit, value, step = 1, min = 0, help, onChange }: Props) {
  return (
    <label className="field" title={help}>
      <span className="field-label">
        {label}
        {symbol && (
          <span className="field-symbol">
            {" "}
            <Tex tex={symbol} />
          </span>
        )}
        {help && <span className="help-dot" aria-hidden>?</span>}
      </span>
      <span className="field-input">
        <input
          type="number"
          value={Number.isFinite(value) ? value : ""}
          step={step}
          min={min}
          onChange={(e) => onChange(parseFloat(e.target.value))}
        />
        {unit && <span className="unit">{unit}</span>}
      </span>
    </label>
  );
}

interface SelectProps {
  label: string;
  value: string;
  options: string[];
  help?: string;
  onChange: (v: string) => void;
}

export function SelectField({ label, value, options, help, onChange }: SelectProps) {
  return (
    <label className="field" title={help}>
      <span className="field-label">
        {label}
        {help && <span className="help-dot" aria-hidden>?</span>}
      </span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => (
          <option key={o}>{o}</option>
        ))}
      </select>
    </label>
  );
}
