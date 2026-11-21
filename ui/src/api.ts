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

export interface LoadOptions {
  safety_classes: Record<string, { label: string; gamma_d: number }>;
  psi: Record<string, { name: string; psi0: number; psi1: number; psi2: number; sk_min?: number | null }>;
  imposed: Record<string, { name: string; psi: string; qk: number; Qk: number }>;
  imposed_note: string;
  methods: string[];
  groups: Record<string, string>;
}

export interface ResolvedLoad {
  type: "udl" | "partial" | "point";
  q?: number;
  P?: number;
  a: number | null;
  b?: number | null;
  text: string;
}

export interface ResolvedCase {
  id: string;
  name: string;
  kind: "permanent" | "variable";
  category: string | null;
  category_name: string | null;
  psi: [number, number, number] | null;
  loads: ResolvedLoad[];
}

export interface CombinationResult {
  id: string;
  name: string;
  type: string;
  type_label: string;
  group: "uls" | "characteristic" | "frequent" | "quasi_permanent";
  leading: string | null;
  latex: string;
  latex_numeric: string;
  factors: Record<string, number>;
  q_d: number | null;
  M_max: number;
  x_M_max: number;
  M_min: number;
  V_abs: number;
  x_V: number;
  x_M_min: number;
  R_A: number;
  R_B: number;
  reactions: { support: string; max: number; min: number }[];
  w_max: number | null;
  x_w: number | null;
  /** Belastade fack (från 1) för variabla lastfall vid största fältmoment. */
  loaded_spans: Record<string, number[]>;
  governs_M: boolean;
  governs_V: boolean;
}

export interface ExtremeValue {
  value: number;
  x: number;
  loaded_spans: Record<string, number[]>;
}

export interface SpanDesign {
  index: number;
  length: number;
  cantilever: boolean;
  M: ExtremeValue;
  combination_M: string;
  w?: ExtremeValue;
  combination_w?: string;
  L_over_w?: number | null;
}

export interface SupportDesign {
  label: string;
  type: "pinned" | "fixed";
  M: number;
  combination_M: string;
  R_max: number;
  combination_R: string;
  R_min: number;
}

export interface DesignValues {
  label: string;
  M: number;
  x_M: number;
  V: number;
  x_V: number;
  M_pos: number;
  x_M_pos: number;
  M_neg: number;
  x_M_neg: number;
  w: number | null;
  x_w: number | null;
  combination_M: string;
  combination_M_name: string;
  combination_V: string;
  combination_V_name: string;
  combination_M_pos_name: string;
  combination_M_neg_name: string;
  combination_w_name: string | null;
  spans: SpanDesign[];
  supports: SupportDesign[];
}

export interface SystemResult {
  description: string;
  length: number;
  spans: number[];
  supports: { label: string; type: "free" | "pinned" | "fixed"; type_label: string; x: number }[];
  pattern: boolean;
  EI: number | null;
}

export interface Envelope {
  M_max: number[];
  M_min: number[];
  V_max: number[];
  V_min: number[];
  w_max?: number[];
  w_min?: number[];
}

export interface LoadsResult {
  gamma_d: number;
  system: SystemResult;
  cases: ResolvedCase[];
  combinations: CombinationResult[];
  design: Record<string, DesignValues>;
  diagrams: { x: number[]; cases: Record<string, { M: number[]; V: number[]; w?: number[] }> } & Record<string, Envelope>;
  warnings: string[];
  logs: CalcLog[];
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
  loadOptions: () => call<LoadOptions>("load_options"),
  loads: (
    system: { spans_m: number[]; supports: string[] },
    bMm: number,
    hMm: number,
    widthM: number,
    safetyClass: number,
    cases: unknown[],
    concrete: string,
    pattern: boolean,
  ) => call<LoadsResult>("loads", 0, bMm, hMm, widthM, safetyClass, cases, null, system, concrete, pattern),
  simplySupported: (spanM: number, qKNm: number) =>
    call<SimplySupportedResult>("simply_supported", spanM, qKNm),
};
