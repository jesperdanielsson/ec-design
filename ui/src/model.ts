// Modellen som användaren bygger upp genom menyns fyra steg.
// Enheter står i namnen så att inget behöver gissas: mm, m, kN/m.

export type LoadType = "udl" | "partial" | "point";
export type LoadUnit = "kN/m" | "kN/m2" | "kN";

/** En last på balken. Läget a/b mäts från vänster stöd i meter. */
export interface LoadInput {
  id: string;
  type: LoadType;
  value: number;
  unit: LoadUnit;
  a_m?: number;
  b_m?: number;
}

/** Ett lastfall (EN 1990 kap. 4). Variabla lastfall har en ψ-kategori. */
export interface LoadCaseInput {
  id: string;
  name: string;
  kind: "permanent" | "variable";
  /** ψ-kategori i det nationella datasetet, t.ex. "B", "wind". "snow" = välj efter s_k. */
  category?: string;
  /** Lägg till balkens egentyngd ρ·b·h (EN 1991-1-1 tabell A.1). */
  self_weight?: boolean;
  /** Snö på tak, EN 1991-1-3 ekv. (5.1). */
  snow?: { sk: number; mu: number };
  loads: LoadInput[];
}

/** Stödtyp: fri ände, fritt upplag eller fast inspänning. */
export type SupportType = "free" | "pinned" | "fixed";

export interface BeamInput {
  /** Fackens längder i m. Ett fack med en fri ände är en konsol eller ett överhäng. */
  spans_m: number[];
  /** Stödens typ från vänster, ett fler än antalet fack. Mellanstöd är fritt upplagda. */
  supports: SupportType[];
  /** Mönsterbelastning: variabel last fack för fack där den verkar ogynnsamt (EN 1992-1-1 5.1.3). */
  pattern: boolean;
  b_mm: number;
  h_mm: number;
  cover_mm: number;
  concrete: string;
  reinforcement: string;
  /** Miljö och tid för krypning och krympning (EN 1992-1-1 3.1.4, bilaga B). */
  cement: "S" | "N" | "R";
  rh_percent: number;
  drying: "all" | "not_top";
  t0_days: number;
  ts_days: number;
  /** Beständighet (EN 1992-1-1 4.4.1, EKS tabell D-1). */
  exposure: string[];
  life: "L100" | "L50" | "L20";
  binder: string;
  vct: number | null;
  stirrup_mm: number;
  /** Säkerhetsklass enligt EKS avd. A (ger γ_d). */
  safety_class: 1 | 2 | 3;
  /** Belastningsbredd (c/c) för ytlaster, m. */
  width_m: number;
  loadCases: LoadCaseInput[];
  analysis: {
    creep: boolean;
    cracking: boolean;
    deflection: boolean;
  };
}

export const defaultBeam: BeamInput = {
  spans_m: [6],
  supports: ["pinned", "pinned"],
  pattern: true,
  b_mm: 300,
  h_mm: 500,
  cover_mm: 30,
  concrete: "C30/37",
  reinforcement: "B500B",
  cement: "R",
  rh_percent: 50,
  drying: "all",
  t0_days: 28,
  ts_days: 7,
  exposure: ["XC1"],
  life: "L50",
  binder: "pc80",
  vct: null,
  stirrup_mm: 10,
  safety_class: 2,
  width_m: 4,
  loadCases: [
    {
      id: "c1",
      name: "Egentyngd, bjälklag och golv",
      kind: "permanent",
      self_weight: true,
      loads: [{ id: "l1", type: "udl", value: 2.0, unit: "kN/m2" }],
    },
    {
      id: "c2",
      name: "Nyttig last, kontor",
      kind: "variable",
      category: "B",
      loads: [{ id: "l2", type: "udl", value: 2.5, unit: "kN/m2" }],
    },
  ],
  analysis: { creep: false, cracking: false, deflection: true },
};

export type StepId = "geometry" | "material" | "loads" | "analysis";

export interface StepDef {
  id: StepId;
  title: string;
  subtitle: string;
  items: string[];
}

// Menyns fyra steg, i den ordning en konstruktör arbetar.
export const STEPS: StepDef[] = [
  {
    id: "geometry",
    title: "Geometri och tvärsnitt",
    subtitle: "Statiskt system, mått och täckskikt",
    items: ["Statiskt system och stöd", "Tvärsnitt", "Täckande betongskikt"],
  },
  {
    id: "material",
    title: "Material",
    subtitle: "Betong, armering, krypning, täckskikt",
    items: ["Betongklass", "Armering", "Spänning–töjning", "Krypning och krympning", "Beständighet och täckskikt"],
  },
  {
    id: "loads",
    title: "Laster",
    subtitle: "Lastfall och kombinationer",
    items: ["Säkerhetsklass", "Lastfall och laster", "Lastkombinationer", "Dimensionerande snittkrafter"],
  },
  {
    id: "analysis",
    title: "Analys och resultat",
    subtitle: "Brott- och bruksgräns",
    items: ["Snittkrafter", "Brottgräns", "Bruksgräns"],
  },
];

export function stepComplete(id: StepId, b: BeamInput): boolean {
  switch (id) {
    case "geometry":
      return validSystem(b) && b.b_mm > 0 && b.h_mm > 0 && b.cover_mm > 0 && b.cover_mm < b.h_mm / 2;
    case "material":
      return Boolean(b.concrete && b.reinforcement && b.exposure.length > 0 && b.rh_percent >= 40 && b.t0_days > 0);
    case "loads":
      return (
        b.width_m > 0 &&
        b.loadCases.length > 0 &&
        b.loadCases.every((lc) => (lc.loads.length > 0 || lc.self_weight || lc.snow) && lc.loads.every((l) => Number.isFinite(l.value)))
      );
    case "analysis":
      return false; // blir klar när kontrollerna finns (steg 5–6 i planen)
  }
}

let _seq = 100;
/** Unikt id för nya lastfall och laster (bara för gränssnittet). */
export const newId = (prefix: string) => `${prefix}${++_seq}`;

/** Balkens totala längd i m (summan av facken). */
export const beamLength = (b: Pick<BeamInput, "spans_m">) => b.spans_m.reduce((s, L) => s + L, 0);

/** Stödens lägen i m från vänster ände. */
export const supportX = (spans_m: number[]) => spans_m.reduce<number[]>((xs, L) => [...xs, xs[xs.length - 1] + L], [0]);

/** Stödens beteckning: A, B, C … */
export const supportLabel = (i: number) => String.fromCharCode(65 + i);

export function validSystem(b: Pick<BeamInput, "spans_m" | "supports">): boolean {
  const s = b.supports;
  if (!b.spans_m.length || s.length !== b.spans_m.length + 1) return false;
  if (!b.spans_m.every((L) => Number.isFinite(L) && L > 0)) return false;
  if (s.slice(1, -1).some((x) => x === "free")) return false;
  // Minst två upplag, eller en inspänning, annars är balken en mekanism.
  const restraints = s.reduce((n, x) => n + (x === "pinned" ? 1 : x === "fixed" ? 2 : 0), 0);
  return restraints >= 2;
}

export type SystemKind = "simple" | "cantilever" | "propped" | "fixed" | "continuous" | "overhang";

/** Vanliga statiska system, med en förklaring för den som är ny. */
export const SYSTEMS: Record<SystemKind, { label: string; help: string; make: (L: number, n: number) => Pick<BeamInput, "spans_m" | "supports"> }> = {
  simple: {
    label: "Fritt upplagd",
    help: "Två upplag som tar vertikal kraft men låter balken vrida sig. Statiskt bestämd: M = qL²/8 i mitten.",
    make: (L) => ({ spans_m: [L], supports: ["pinned", "pinned"] }),
  },
  cantilever: {
    label: "Konsol",
    help: "Fast inspänd i ena änden, fri i den andra. Störst moment (dragning i överkant) vid inspänningen: M = qL²/2.",
    make: (L) => ({ spans_m: [L], supports: ["fixed", "free"] }),
  },
  propped: {
    label: "Ensidigt inspänd",
    help: "Inspänd i ena änden, fritt upplagd i den andra. Statiskt obestämd: stödmoment qL²/8 vid inspänningen.",
    make: (L) => ({ spans_m: [L], supports: ["pinned", "fixed"] }),
  },
  fixed: {
    label: "Tvåsidigt inspänd",
    help: "Inspänd i båda ändar. Stödmoment qL²/12, fältmoment qL²/24. Full inspänning är sällsynt i verkligheten.",
    make: (L) => ({ spans_m: [L], supports: ["fixed", "fixed"] }),
  },
  continuous: {
    label: "Kontinuerlig",
    help: "Går över flera stöd. Negativa stödmoment över mellanstöden, och variabel last placeras fack för fack (mönsterbelastning).",
    make: (L, n) => ({ spans_m: Array(Math.max(2, n)).fill(L), supports: Array(Math.max(2, n) + 1).fill("pinned") }),
  },
  overhang: {
    label: "Med överhäng",
    help: "Fritt upplagd balk som fortsätter förbi stödet som en konsol. Last på överhänget minskar fältmomentet och kan lyfta det andra stödet.",
    make: (L) => ({ spans_m: [L, Math.round(L * 3) / 10], supports: ["pinned", "pinned", "free"] }),
  },
};

/** Vilket av de vanliga systemen balken är, om något. */
export function systemKind(b: Pick<BeamInput, "spans_m" | "supports">): SystemKind | null {
  const s = b.supports.join(",");
  if (b.spans_m.length === 1)
    return ({ "pinned,pinned": "simple", "fixed,free": "cantilever", "free,fixed": "cantilever", "pinned,fixed": "propped", "fixed,pinned": "propped", "fixed,fixed": "fixed" } as Record<string, SystemKind>)[s] ?? null;
  if (b.supports.every((x) => x === "pinned")) return "continuous";
  if (b.supports[0] === "free" || b.supports[b.supports.length - 1] === "free") return "overhang";
  return null;
}
