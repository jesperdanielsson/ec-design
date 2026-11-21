// Modellen som användaren bygger upp genom menyns fyra steg.
// Enheter står i namnen så att inget behöver gissas: mm, m, kN/m.

export interface LoadCaseInput {
  id: string;
  name: string;
  kind: "permanent" | "variable";
  category?: string;
  q_kNm: number;
}

export interface BeamInput {
  span_m: number;
  b_mm: number;
  h_mm: number;
  cover_mm: number;
  concrete: string;
  reinforcement: string;
  loadCases: LoadCaseInput[];
  analysis: {
    creep: boolean;
    cracking: boolean;
    deflection: boolean;
  };
}

export const defaultBeam: BeamInput = {
  span_m: 6,
  b_mm: 300,
  h_mm: 500,
  cover_mm: 30,
  concrete: "C30/37",
  reinforcement: "B500B",
  loadCases: [
    { id: "G", name: "Egentyngd och bjälklag", kind: "permanent", q_kNm: 12 },
    { id: "Q", name: "Nyttig last, kontor", kind: "variable", category: "B", q_kNm: 8 },
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
    subtitle: "Spann, stöd, mått och täckskikt",
    items: ["Balk och stöd", "Tvärsnitt", "Täckande betongskikt"],
  },
  {
    id: "material",
    title: "Material",
    subtitle: "Betong, armering, σ–ε, krypning",
    items: ["Betongklass", "Armering", "Spänning–töjning", "Krypning och krympning"],
  },
  {
    id: "loads",
    title: "Laster",
    subtitle: "Lastfall och kombinationer",
    items: ["Lastfall", "Laster", "Lastkombinationer"],
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
      return b.span_m > 0 && b.b_mm > 0 && b.h_mm > 0 && b.cover_mm > 0 && b.cover_mm < b.h_mm / 2;
    case "material":
      return Boolean(b.concrete && b.reinforcement);
    case "loads":
      return b.loadCases.length > 0;
    case "analysis":
      return false; // blir klar när kontrollerna finns (steg 5–6 i planen)
  }
}
