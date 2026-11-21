r"""Lastkombinationer enligt EN 1990 med svenska val (EKS).

Brottgräns, STR/GEO (EN 1990 6.4.3.2 och tabell A1.2(B), EKS avd. B):

* 6.10a: :math:`\gamma_d 1{,}35 G_{k,sup} + 1{,}0 G_{k,inf} + \gamma_d 1{,}5 \psi_{0,i} Q_{k,i}`
* 6.10b: :math:`\gamma_d \xi 1{,}35 G_{k,sup} + 1{,}0 G_{k,inf} + \gamma_d 1{,}5 Q_{k,1}
  + \gamma_d 1{,}5 \psi_{0,i} Q_{k,i}`, en kombination per huvudlast :math:`Q_{k,1}`
* 6.10 (bara rekommenderade värden): :math:`1{,}35 G_k + 1{,}5 Q_{k,1} + 1{,}5\psi_0 Q_{k,i}`

γ_d (säkerhetsklass, EKS avd. A) multipliceras bara på ogynnsamma laster. Gynnsam
variabel last tas inte med (faktor 0).

Bruksgräns (EN 1990 6.5.3, ekv. 6.14b–6.16b), utan partialkoefficienter:

* karakteristisk: :math:`G_k + Q_{k,1} + \psi_{0,i} Q_{k,i}`
* frekvent: :math:`G_k + \psi_{1,1} Q_{k,1} + \psi_{2,i} Q_{k,i}`
* kvasipermanent: :math:`G_k + \psi_{2,i} Q_{k,i}` (krypning, sprickbredd, nedböjning)

Varje kombination är en lista med termer: en faktor när lastfallet verkar ogynnsamt och en
när det verkar gynnsamt. Vilken som gäller avgörs i varje snitt när snittkrafterna räknas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from ..calclog import CalcLog, _fmt
from ..national import NationalAnnex
from ..national import load as load_annex
from ..units import Q_
from .actions import DistributedLoad, LoadCase, LoadKind, psi_factors

REF_ULS = "EN 1990 6.4.3.2, tabell A1.2(B); EKS avd. B"
REF_SLS = "EN 1990 6.5.3"


class CombinationType(StrEnum):
    ULS_610 = "6.10"
    ULS_610A = "6.10a"
    ULS_610B = "6.10b"
    CHARACTERISTIC = "characteristic"
    FREQUENT = "frequent"
    QUASI_PERMANENT = "quasi_permanent"

    @property
    def group(self) -> str:
        """Grupp där den dimensionerande kombinationen väljs: uls eller en brukskombination."""
        return "uls" if self.value.startswith("6.10") else self.value

    @property
    def label(self) -> str:
        return {
            "6.10": "Brottgräns 6.10",
            "6.10a": "Brottgräns 6.10a",
            "6.10b": "Brottgräns 6.10b",
            "characteristic": "Karakteristisk",
            "frequent": "Frekvent",
            "quasi_permanent": "Kvasipermanent",
        }[self.value]


GROUPS = {
    "uls": "Brottgräns (STR)",
    "characteristic": "Bruksgräns, karakteristisk",
    "frequent": "Bruksgräns, frekvent",
    "quasi_permanent": "Bruksgräns, kvasipermanent",
}


@dataclass(frozen=True)
class Term:
    """Ett lastfall i en kombination: faktor som ogynnsam och som gynnsam last."""

    case_id: str
    unfav: float
    fav: float
    symbolic: str
    """Faktorn i symboler, t.ex. ``\\gamma_d \\cdot \\xi \\cdot \\gamma_{G,sup}``."""
    permanent: bool = False
    parts: tuple[float, ...] = ()
    """Faktorns delar i samma ordning som ``symbolic``, t.ex. (0,91; 0,89; 1,35)."""

    def numeric(self) -> str:
        """Faktorn som produkt av sina delar, som i en handräkning: ``0{,}91 \\cdot 1{,}5``."""
        if not self.parts:
            return _fmt(round(self.unfav, 6)) if self.unfav != 1.0 else ""
        return r" \cdot ".join(_fmt(p) for p in self.parts)


@dataclass(frozen=True)
class Combination:
    id: str
    type: CombinationType
    leading: str | None
    terms: tuple[Term, ...]

    @property
    def group(self) -> str:
        return self.type.group

    @property
    def name(self) -> str:
        base = self.type.label
        if self.leading and self.type not in (
            CombinationType.ULS_610A,
            CombinationType.QUASI_PERMANENT,
        ):
            return f"{base}, {self.leading} huvudlast"
        return base

    def factor(self, case_id: str, unfavourable: bool = True) -> float:
        for t in self.terms:
            if t.case_id == case_id:
                return t.unfav if unfavourable else t.fav
        return 0.0

    def latex(self) -> str:
        """Kombinationen i symboler, t.ex. ``γ_d·1,35·G_k,G1 + γ_d·1,5·Q_k,Q1``."""
        return " + ".join(
            rf"{t.symbolic} \cdot {_load_sym(t)}" if t.symbolic else _load_sym(t)
            for t in self.terms
        )

    def latex_numeric(self) -> str:
        """Samma kombination med faktorerna insatta (ogynnsamma värden)."""
        return " + ".join(
            rf"{t.numeric()} \cdot {_load_sym(t)}" if t.numeric() else _load_sym(t)
            for t in self.terms
        )


def _load_sym(t: Term) -> str:
    kind = "G" if t.permanent else "Q"
    return rf"{kind}_{{k,\mathrm{{{t.case_id}}}}}"


@dataclass
class CombinationSet:
    combinations: list[Combination]
    gamma_d: float
    psi: dict[str, tuple[float, float, float]]
    log: CalcLog
    warnings: list[str] = field(default_factory=list)

    def get(self, cid: str) -> Combination:
        for c in self.combinations:
            if c.id == cid:
                return c
        raise KeyError(cid)


def generate_combinations(
    cases: list[LoadCase],
    safety_class: int = 2,
    annex: NationalAnnex | None = None,
    method: str | None = None,
) -> CombinationSet:
    """Alla lastkombinationer för lastfallen (som ska ha ``id``, se ``resolve_cases``).

    ``method``: ``"6.10ab"`` (EKS) eller ``"6.10"``. Standard: första tillåtna i datasetet.
    EN 1990 6.4.3.2 ekv. 6.10/6.10a/6.10b, 6.5.3 ekv. 6.14b–6.16b; EKS avd. A och B.
    """
    annex = annex or load_annex("eks")
    allowed = annex.get("combination.uls.methods")
    method = method or allowed[0]
    if method not in allowed:
        raise ValueError(
            f"Kombinationsmetod {method!r} är inte tillåten i {annex.name} "
            f"(tillåtet: {', '.join(allowed)})."
        )
    log = CalcLog(title="Lastkombinationer enligt EN 1990 och " + annex.name)
    warnings: list[str] = []

    uls = annex.get("combination.uls")
    gd = log.step(
        symbol=r"\gamma_d",
        description=f"Partialkoefficient för säkerhetsklass {safety_class}",
        formula=_fmt(annex.get(f"safety_class.{safety_class}")),
        result=annex.get(f"safety_class.{safety_class}"),
        ref="EKS avd. A 13–14 §§ (säkerhetsklass)"
        if annex.code == "eks"
        else "EN 1990 (ingen säkerhetsklass, γ_d = 1,0)",
    )
    gG = log.step(
        symbol=r"\gamma_{G,sup}",
        description="Partialkoefficient för ogynnsam permanent last",
        formula=_fmt(uls["gamma_G_610a"]),
        result=uls["gamma_G_610a"],
        ref=REF_ULS,
    )
    gGinf = log.step(
        symbol=r"\gamma_{G,inf}",
        description="Partialkoefficient för gynnsam permanent last (utan γ_d)",
        formula=_fmt(uls["gamma_G_fav"]),
        result=uls["gamma_G_fav"],
        ref=REF_ULS,
    )
    gQ = log.step(
        symbol=r"\gamma_Q",
        description="Partialkoefficient för ogynnsam variabel last",
        formula=_fmt(uls["gamma_Q"]),
        result=uls["gamma_Q"],
        ref=REF_ULS,
    )
    xi = 1.0
    if method == "6.10ab":
        xi = log.step(
            symbol=r"\xi",
            description="Reduktionsfaktor för permanent last i ekv. 6.10b",
            formula=_fmt(uls["xi"]),
            result=uls["xi"],
            ref=REF_ULS,
        )

    perm = [c for c in cases if c.kind is LoadKind.PERMANENT]
    var = [c for c in cases if c.kind is LoadKind.VARIABLE]
    if any(c.kind is LoadKind.ACCIDENTAL for c in cases):
        warnings.append("Olyckslast (ekv. 6.11) ingår inte än och har hoppats över.")

    psi: dict[str, tuple[float, float, float]] = {}
    for c in var:
        p = psi_factors(c, annex)
        psi[c.id] = p
        src = (
            "angivet för lastfallet"
            if c.psi is not None
            else annex.get(f"psi.{c.category}")["name"]
        )
        for i in range(3):
            log.step(
                symbol=rf"\psi_{{{i},\mathrm{{{c.id}}}}}",
                description=f"{c.name} ({src})",
                formula=_fmt(p[i]),
                result=p[i],
                ref="EN 1990 tabell A1.1; EKS avd. B" if c.psi is None else "Angivet värde",
            )

    def g_terms(parts: tuple[float, ...], sym: str) -> list[Term]:
        return [Term(c.id, _prod(parts), gGinf, sym, True, parts) for c in perm]

    combos: list[Combination] = []
    leaders: list[LoadCase | None] = list(var) or [None]

    # --- Brottgräns ------------------------------------------------------
    if method == "6.10ab":
        terms = g_terms((gd, gG), r"\gamma_d \cdot \gamma_{G,sup}")
        terms += [_q_term(c.id, (gd, gQ, psi[c.id][0]), 0) for c in var]
        combos.append(Combination("6.10a", CombinationType.ULS_610A, None, tuple(terms)))
        uls_types = [
            (CombinationType.ULS_610B, (gd, xi, gG), r"\gamma_d \cdot \xi \cdot \gamma_{G,sup}")
        ]
    else:
        uls_types = [(CombinationType.ULS_610, (gd, gG), r"\gamma_d \cdot \gamma_{G,sup}")]
    for ctype, gfac, gsym in uls_types:
        for lead in leaders:
            terms = g_terms(gfac, gsym)
            for c in var:
                if c is lead:
                    terms.append(_q_term(c.id, (gd, gQ), None))
                else:
                    terms.append(_q_term(c.id, (gd, gQ, psi[c.id][0]), 0))
            combos.append(_combo(ctype, lead, terms))

    # --- Bruksgräns ------------------------------------------------------
    for ctype, lead_i, other_i in (
        (CombinationType.CHARACTERISTIC, None, 0),
        (CombinationType.FREQUENT, 1, 2),
    ):
        for lead in leaders:
            terms = [Term(c.id, 1.0, 1.0, "", True) for c in perm]
            for c in var:
                if c is lead and lead_i is None:
                    terms.append(Term(c.id, 1.0, 0.0, ""))
                else:
                    i = lead_i if c is lead else other_i
                    terms.append(_q_term(c.id, (psi[c.id][i],), i))
            combos.append(_combo(ctype, lead, terms))
    terms = [Term(c.id, 1.0, 1.0, "", True) for c in perm]
    terms += [_q_term(c.id, (psi[c.id][2],), 2) for c in var]
    combos.append(Combination("QP", CombinationType.QUASI_PERMANENT, None, tuple(terms)))

    # Logga varje kombination; med bara jämnt utbredda laster även q_d.
    for combo in combos:
        _log_combination(log, combo, cases)

    return CombinationSet(combos, gd, psi, log, warnings)


def _prod(parts: tuple[float, ...]) -> float:
    out = 1.0
    for p in parts:
        out *= p
    return out


def _q_term(case_id: str, parts: tuple[float, ...], psi_index: int | None) -> Term:
    """Term för en variabel last. ``parts`` = (γ_d, γ_Q, ψ) i brottgräns, (ψ,) i bruksgräns."""
    syms = []
    if len(parts) >= 2:
        syms = [r"\gamma_d", r"\gamma_Q"]
    if psi_index is not None:
        syms.append(rf"\psi_{{{psi_index},\mathrm{{{case_id}}}}}")
    return Term(case_id, _prod(parts), 0.0, r" \cdot ".join(syms), False, parts)


_PREFIX = {
    CombinationType.ULS_610: "6.10",
    CombinationType.ULS_610B: "6.10b",
    CombinationType.CHARACTERISTIC: "K",
    CombinationType.FREQUENT: "F",
}


def _combo(ctype: CombinationType, lead: LoadCase | None, terms: list[Term]) -> Combination:
    cid = _PREFIX[ctype] + (f"-{lead.id}" if lead else "")
    return Combination(cid, ctype, lead.id if lead else None, tuple(terms))


def _log_combination(log: CalcLog, combo: Combination, cases: list[LoadCase]) -> None:
    by_id = {c.id: c for c in cases}
    udl_only = all(
        all(isinstance(ld, DistributedLoad) and ld.full_span for ld in by_id[t.case_id].loads)
        for t in combo.terms
    )
    ref = REF_ULS if combo.group == "uls" else REF_SLS
    eq = {
        "6.10": "ekv. (6.10)",
        "6.10a": "ekv. (6.10a)",
        "6.10b": "ekv. (6.10b)",
        "characteristic": "ekv. (6.14b)",
        "frequent": "ekv. (6.15b)",
        "quasi_permanent": "ekv. (6.16b)",
    }[combo.type.value]
    symbol = rf"q_{{d,\mathrm{{{combo.id}}}}}"
    if udl_only and combo.terms:
        parts = []
        total = Q_(0, "kN/m")
        for t in combo.terms:
            q = sum((ld.q for ld in by_id[t.case_id].loads), Q_(0, "kN/m"))
            unfav = q.magnitude >= 0
            f = t.unfav if unfav else t.fav
            total = total + f * q
            num = t.numeric() if unfav else (_fmt(f) if f != 1.0 else "")
            qs = _fmt(q.magnitude) if unfav else f"({_fmt(q.magnitude)})"
            parts.append(rf"{num} \cdot {qs}" if num else qs)
        log.step(
            symbol=symbol,
            description=f"{combo.name}: dimensionerande utbredd last",
            formula=combo.latex(),
            substituted=" + ".join(parts),
            result=total.to("kN/m"),
            ref=f"{ref} {eq}",
        )
    else:
        log.step(
            symbol=symbol,
            description=f"{combo.name}: lastfallens faktorer (ogynnsam verkan)",
            formula=combo.latex(),
            substituted="",
            result=combo.latex_numeric() or "0",
            ref=f"{ref} {eq}",
        )
