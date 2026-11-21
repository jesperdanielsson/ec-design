import { STEPS, type BeamInput, type StepId, stepComplete } from "../model";

interface Props {
  active: StepId;
  beam: BeamInput;
  annex?: string;
  version?: string;
  onSelect: (id: StepId) => void;
}

export function Sidebar({ active, beam, annex, version, onSelect }: Props) {
  return (
    <nav className="sidebar" aria-label="Arbetsflöde">
      <div className="brand">
        <div className="brand-mark" aria-hidden>
          EC
        </div>
        <div>
          <div className="brand-name">EC Design</div>
          <div className="brand-sub">Armerad betongbalk</div>
        </div>
      </div>

      <ol className="steps">
        {STEPS.map((s, i) => {
          const done = stepComplete(s.id, beam);
          const isActive = s.id === active;
          return (
            <li key={s.id}>
              <button
                className={`step ${isActive ? "active" : ""} ${done ? "done" : ""}`}
                onClick={() => onSelect(s.id)}
                aria-current={isActive ? "step" : undefined}
              >
                <span className="step-num">{done ? "✓" : i + 1}</span>
                <span className="step-text">
                  <span className="step-title">{s.title}</span>
                  <span className="step-sub">{s.subtitle}</span>
                </span>
              </button>
              {isActive && (
                <ul className="step-items">
                  {s.items.map((it) => (
                    <li key={it}>{it}</li>
                  ))}
                </ul>
              )}
            </li>
          );
        })}
      </ol>

      <div className="sidebar-foot">
        <div className="annex-pill" title="Nationella val som används i alla beräkningar">
          {annex ?? "…"}
        </div>
        <div className="muted small">Version {version ?? "…"}</div>
      </div>
    </nav>
  );
}
