// Brygga till Python-kärnan.
// I skrivbordsappen: window.pywebview.api (direkt anrop till ecdesign.api.Api).
// I webbläsaren under utveckling: POST /api/<metod> till ecdesign.devserver.

export interface CalcStep {
  symbol: string;
  description: string;
  formula: string;
  substituted: string;
  latex: string;
  result_latex: string;
  ref: string;
}

export interface CalcLog {
  title: string;
  steps: CalcStep[];
}

export interface ConcreteResult {
  name: string;
  properties: Record<string, number>;
  curve: [number, number][];
  log: CalcLog;
}

export interface ReinforcementResult {
  name: string;
  properties: Record<string, number | string>;
  log: CalcLog;
}

export interface MaterialOptions {
  cements: Record<string, string>;
  drying: Record<string, string>;
  exposure: Record<string, { group: string; text: string }>;
  lives: Record<string, string>;
  binders: Record<string, string>;
}

export interface LongTermResult {
  h0: number;
  strength_at_t0: { t: number; fcm: number; fck: number; fctm: number; Ecm: number; beta_cc: number };
  strength_curve: { t: number; fcm: number; fck: number; fctm: number; Ecm: number }[];
  creep: {
    phi_inf: number;
    phi_RH: number;
    beta_fcm: number;
    beta_t0: number;
    beta_H: number;
    Ec_eff: number;
    curve: [number, number][];
  };
  shrinkage: {
    eps_cs_inf: number;
    eps_cd_inf: number;
    eps_ca_inf: number;
    kh: number;
    beta_RH: number;
    curve: { t: number; eps_cd: number; eps_ca: number; eps_cs: number }[];
  };
  logs: CalcLog[];
}

export interface CoverResult {
  vct_max: number | null;
  vct_ok: boolean;
  cmin_dur: number;
  cmin_b: number;
  cmin: number;
  delta_c_dev: number;
  cnom: number;
  warnings: string[];
  log: CalcLog;
}

export interface SimplySupportedResult {
  M_max: number;
  V_max: number;
  log: CalcLog;
}

export interface Info {
  version: string;
  annex: string;
  annex_source: string;
  annexes: string[];
}

declare global {
  interface Window {
    pywebview?: { api: Record<string, (...args: unknown[]) => Promise<unknown>> };
  }
}

function waitForPywebview(): Promise<boolean> {
  if (window.pywebview?.api) return Promise.resolve(true);
  return new Promise((resolve) => {
    const done = () => resolve(Boolean(window.pywebview?.api));
    window.addEventListener("pywebviewready", done, { once: true });
    // Ingen pywebview efter en kort stund: vi kör i en vanlig webbläsare.
    setTimeout(done, 300);
  });
}

async function call<T>(method: string, ...args: unknown[]): Promise<T> {
  if (await waitForPywebview()) {
    return (await window.pywebview!.api[method](...args)) as T;
  }
  const res = await fetch(`/api/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(args),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error ?? res.statusText);
  return data as T;
}

export const api = {
  info: () => call<Info>("info"),
  concreteClasses: () => call<string[]>("concrete_classes"),
  concrete: (name: string) => call<ConcreteResult>("concrete", name),
  materialOptions: () => call<MaterialOptions>("material_options"),
  concreteLongTerm: (
    name: string,
    cement: string,
    rh: number,
    bMm: number,
    hMm: number,
    drying: string,
    t0: number,
    ts: number,
  ) => call<LongTermResult>("concrete_long_term", name, cement, rh, bMm, hMm, drying, t0, ts),
  concreteCover: (exposure: string[], life: string, binder: string, vct: number | null, barMm: number) =>
    call<CoverResult>("concrete_cover", exposure, life, binder, vct, barMm),
  reinforcementGrades: () => call<string[]>("reinforcement_grades"),
  reinforcement: (name: string) => call<ReinforcementResult>("reinforcement", name),
  simplySupported: (spanM: number, qKNm: number) =>
    call<SimplySupportedResult>("simply_supported", spanM, qKNm),
};
