"""Lastfall och laster på balken (EN 1990 kap. 4, EN 1991-1-1, EN 1991-1-3).

En balk bär ett antal *lastfall* (t.ex. "Egentyngd", "Nyttig last, kontor", "Snö").
Varje lastfall har en typ (permanent/variabel), en ψ-kategori för variabla laster och en
eller flera laster: utbredd över hela spannet, delutbredd eller punktlast.

Utbredda laster kan anges som linjelast (kN/m) eller som ytlast (kN/m²) som räknas om
med belastningsbredden. Omräkningen, egentyngden och snölasten loggas, så att varje
linjelast går att följa tillbaka till sitt ursprung.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum

from ..calclog import CalcLog
from ..national import NationalAnnex
from ..national import load as load_annex
from ..units import Q_

GAMMA_RC = Q_(25, "kN/m^3")
"""Tunghet för armerad betong, normal armeringsmängd. EN 1991-1-1 bilaga A, tabell A.1."""

SAFETY_CLASSES = {
    1: "Säkerhetsklass 1 – liten risk för allvarliga personskador",
    2: "Säkerhetsklass 2 – någon risk för allvarliga personskador",
    3: "Säkerhetsklass 3 – stor risk för allvarliga personskador",
}
"""EKS avd. A, 13–14 §§ (säkerhetsklasser). γ_d läses från det nationella datasetet."""


class LoadKind(StrEnum):
    PERMANENT = "permanent"
    VARIABLE = "variable"
    ACCIDENTAL = "accidental"


@dataclass
class DistributedLoad:
    """Jämnt utbredd last från ``a`` till ``b`` (mätt från vänster stöd).

    ``a`` och ``b`` = ``None`` betyder hela spannet. ``q`` är en linjelast (kN/m) eller en
    ytlast (kN/m²); en ytlast räknas om med belastningsbredden i :func:`resolve_cases`.
    """

    q: Q_
    a: Q_ | None = None
    b: Q_ | None = None
    description: str = ""

    @property
    def is_area_load(self) -> bool:
        return self.q.check("[pressure]")

    @property
    def full_span(self) -> bool:
        return self.a is None and self.b is None


@dataclass
class PointLoad:
    """Punktlast ``P`` på avståndet ``a`` från vänster stöd. Positiv nedåt."""

    P: Q_
    a: Q_
    description: str = ""


Load = DistributedLoad | PointLoad


@dataclass
class LoadCase:
    """Ett lastfall, t.ex. "Egentyngd" eller "Nyttig last, kontor".

    ``id`` är en kort beteckning som används i formler (t.ex. ``"G1"``, ``"Q1"``).
    ``category`` är nyckeln för ψ-faktorerna i det nationella datasetet (t.ex. ``"B"``).
    ``psi`` kan anges direkt som (ψ0, ψ1, ψ2) och går då före kategorin.
    ``self_weight``: lägg till balkens egentyngd ρ·b·h (bara för permanenta lastfall).
    ``snow_sk``: karakteristisk snölast på mark; ger ψ-kategori och, med ``snow_mu``,
    lasten på taket (EN 1991-1-3 ekv. 5.1). Ytlasten anges då inte separat.
    """

    name: str
    kind: LoadKind
    category: str | None = None
    loads: list[Load] = field(default_factory=list)
    id: str = ""
    psi: tuple[float, float, float] | None = None
    self_weight: bool = False
    snow_sk: Q_ | None = None
    snow_mu: float = 0.8
    snow_Ce: float = 1.0
    snow_Ct: float = 1.0


def _sym(case_id: str) -> str:
    return rf"\mathrm{{{case_id}}}"


def self_weight(b: Q_, h: Q_, log: CalcLog, case_id: str = "G") -> Q_:
    """Egentyngd för rektangulär betongbalk, g = ρ·b·h. EN 1991-1-1 tabell A.1 (25 kN/m³)."""
    return log.step(
        symbol=rf"g_{{k,{_sym(case_id)},\mathrm{{egen}}}}",
        description="Balkens egentyngd, armerad betong",
        formula=r"\rho \cdot b \cdot h",
        values={r"\rho": GAMMA_RC, "b": b.to("m"), "h": h.to("m")},
        result=(GAMMA_RC * b * h).to("kN/m"),
        ref="EN 1991-1-1 bilaga A, tabell A.1",
    )


def roof_snow(
    sk: Q_, mu1: float, log: CalcLog, Ce: float = 1.0, Ct: float = 1.0, case_id: str = "S"
) -> Q_:
    """Snölast på tak, varaktig dimensioneringssituation: s = μ_i·C_e·C_t·s_k.

    EN 1991-1-3 5.2(3)P ekv. (5.1). μ_1 = 0,8 för taklutning 0–30°, tabell 5.2.
    """
    return log.step(
        symbol=rf"s_{{{_sym(case_id)}}}",
        description="Snölast på taket",
        formula=r"\mu_1 \cdot C_e \cdot C_t \cdot s_k",
        values={r"\mu_1": mu1, "C_e": Ce, "C_t": Ct, "s_k": sk.to("kN/m^2")},
        result=(mu1 * Ce * Ct * sk).to("kN/m^2"),
        ref="EN 1991-1-3 5.2(3)P ekv. (5.1), tabell 5.2",
    )


def snow_category(sk: Q_, annex: NationalAnnex) -> str:
    """ψ-kategori för snö utifrån s_k (EKS tabell B-1; EN 1990 tabell A1.1)."""
    sk_val = sk.to("kN/m^2").magnitude
    rows = sorted(
        ((k, v) for k, v in annex.get("psi").items() if k.startswith("snow")),
        key=lambda kv: kv[1].get("sk_min", 0.0),
        reverse=True,
    )
    for key, row in rows:
        if sk_val >= row.get("sk_min", 0.0):
            return key
    return rows[-1][0]


def psi_factors(case: LoadCase, annex: NationalAnnex) -> tuple[float, float, float]:
    """(ψ0, ψ1, ψ2) för ett variabelt lastfall. EN 1990 tabell A1.1, EKS tabell B-1."""
    if case.psi is not None:
        return case.psi
    if case.category is None:
        raise ValueError(f"Lastfallet {case.name!r} saknar kategori för ψ-faktorerna.")
    row = annex.get(f"psi.{case.category}")
    return (row["psi0"], row["psi1"], row["psi2"])


@dataclass
class ResolvedCases:
    """Lastfallen med alla laster som linjelaster (kN/m) eller punktlaster (kN)."""

    cases: list[LoadCase]
    log: CalcLog
    warnings: list[str] = field(default_factory=list)


def resolve_cases(
    cases: list[LoadCase],
    span: Q_,
    width: Q_ | None = None,
    b: Q_ | None = None,
    h: Q_ | None = None,
    annex: NationalAnnex | None = None,
) -> ResolvedCases:
    """Räkna om ytlaster till linjelaster, lägg till egentyngd och snö, och kontrollera lägen.

    * ytlast: q = q_yta · belastningsbredd
    * egentyngd: g = ρ·b·h (EN 1991-1-1 tabell A.1)
    * snö: s = μ1·Ce·Ct·sk (EN 1991-1-3 ekv. 5.1), ψ-kategori efter s_k (EKS tabell B-1)
    """
    annex = annex or load_annex("eks")
    log = CalcLog(title="Laster på balken")
    warnings: list[str] = []
    L = span.to("m")
    out: list[LoadCase] = []
    ids = _unique_ids(cases)
    for case, cid in zip(cases, ids, strict=True):
        generated: list[Load] = []
        category = case.category
        if case.self_weight:
            if b is None or h is None:
                raise ValueError("Egentyngd kräver balkens bredd och höjd.")
            generated.append(DistributedLoad(self_weight(b, h, log, cid), description="Egentyngd"))
        if case.snow_sk is not None:
            category = snow_category(case.snow_sk, annex)
            if case.snow_sk.to("kN/m^2").magnitude < 1.0 and annex.code == "eks":
                warnings.append(
                    f"{case.name}: s_k under 1,0 kN/m² förekommer inte i EKS; ψ för "
                    "1 ≤ s_k < 2 används."
                )
            s = roof_snow(case.snow_sk, case.snow_mu, log, case.snow_Ce, case.snow_Ct, cid)
            generated.append(DistributedLoad(s, description="Snö på tak"))
        raw = [*generated, *case.loads]
        area_count = sum(isinstance(ld, DistributedLoad) and ld.is_area_load for ld in raw)
        n = 0
        loads: list[Load] = []
        for ld in raw:
            if isinstance(ld, DistributedLoad):
                a = (ld.a if ld.a is not None else Q_(0, "m")).to("m")
                e = (ld.b if ld.b is not None else L).to("m")
                if not (0 <= a.magnitude < e.magnitude <= L.magnitude + 1e-9):
                    raise ValueError(
                        f"{case.name}: delutbredd last måste ligga inom spannet, "
                        f"0 ≤ a < b ≤ L (a = {a.magnitude:g} m, b = {e.magnitude:g} m)."
                    )
                q = ld.q
                if ld.is_area_load:
                    if width is None or width.magnitude <= 0:
                        raise ValueError("Ytlast kräver en belastningsbredd större än noll.")
                    n += 1
                    idx = f",{n}" if area_count > 1 else ""
                    q = log.step(
                        symbol=rf"q_{{k,{_sym(cid)}{idx}}}",
                        description=f"{case.name}: ytlast gånger belastningsbredd"
                        + (f" ({ld.description})" if ld.description else ""),
                        formula=r"q_{yta} \cdot c",
                        values={r"q_{yta}": q.to("kN/m^2"), "c": width.to("m")},
                        result=(q * width).to("kN/m"),
                        ref="Belastningsbredd (c/c-avstånd mellan balkar)",
                    )
                q = q.to("kN/m")
                full = ld.full_span or (a.magnitude == 0 and abs(e.magnitude - L.magnitude) < 1e-9)
                loads.append(
                    DistributedLoad(q, None if full else a, None if full else e, ld.description)
                )
            else:
                a = ld.a.to("m")
                if not (0 <= a.magnitude <= L.magnitude + 1e-9):
                    raise ValueError(
                        f"{case.name}: punktlastens läge a = {a.magnitude:g} m ligger "
                        "utanför spannet."
                    )
                loads.append(PointLoad(ld.P.to("kN"), a, ld.description))
        if case.kind is LoadKind.VARIABLE and case.psi is None and category is None:
            raise ValueError(f"Lastfallet {case.name!r} saknar kategori för ψ-faktorerna.")
        out.append(replace(case, id=cid, category=category, loads=loads, self_weight=False))
    return ResolvedCases(out, log, warnings)


def _unique_ids(cases: list[LoadCase]) -> list[str]:
    """Korta beteckningar G1, G2, Q1, Q2 … där användaren inte angett någon."""
    used: set[str] = set()
    out: list[str] = []
    counters = {LoadKind.PERMANENT: 0, LoadKind.VARIABLE: 0, LoadKind.ACCIDENTAL: 0}
    prefix = {LoadKind.PERMANENT: "G", LoadKind.VARIABLE: "Q", LoadKind.ACCIDENTAL: "A"}
    for c in cases:
        cid = c.id
        if not cid or cid in used:
            while True:
                counters[c.kind] += 1
                cid = f"{prefix[c.kind]}{counters[c.kind]}"
                if cid not in used:
                    break
        used.add(cid)
        out.append(cid)
    return out
