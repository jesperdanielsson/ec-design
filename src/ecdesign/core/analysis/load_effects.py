r"""Snittkrafter för varje lastkombination och vilken kombination som blir dimensionerande.

Varje lastfall räknas för sig med karakteristiska värden (superposition, linjärt elastisk
analys, EN 1990 6.3.2). I varje snitt kombineras lastfallen med kombinationens faktorer:
ett lastfall som ökar snittkraften får den ogynnsamma faktorn, ett som minskar den får
den gynnsamma (EN 1990 6.4.3.2(3) och tabell A1.2(B) anm. 3: "ogynnsam/gynnsam").

.. math::
    M_{Ed}(x) = \sum_i f_i(x) \, M_{k,i}(x)

Den dimensionerande kombinationen i en grupp (brottgräns, karakteristisk, frekvent,
kvasipermanent) är den som ger störst absolutvärde någonstans längs balken.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..calclog import CalcLog, _fmt
from ..loads.actions import LoadCase
from ..loads.combinations import GROUPS, Combination, CombinationSet
from ..units import Q_
from .simply_supported import forces_at, reactions, sample_points

REF = "EN 1990 6.3.2 och 6.4.3.2(3); elementarfall för fritt upplagd balk"


@dataclass
class CombinationEffect:
    combination: Combination
    M_max: Q_
    """Största positiva moment (dragning i underkant)."""
    x_M_max: Q_
    M_min: Q_
    """Minsta (mest negativa) moment. Noll för nedåtriktade laster på fritt upplagd balk."""
    x_M_min: Q_
    V_abs: Q_
    """Största tvärkraft till beloppet."""
    x_V: Q_
    R_A: Q_
    R_B: Q_
    M_env: tuple[list[float], list[float]]
    """(max, min) moment i kNm i varje snitt, för diagram."""
    V_env: tuple[list[float], list[float]]
    """(max, min) tvärkraft i kN i varje snitt, för diagram."""

    @property
    def M_abs(self) -> Q_:
        return self.M_max if abs(self.M_max) >= abs(self.M_min) else self.M_min


@dataclass
class DesignEffects:
    x: list[float]
    """Snittens läge i m (ett snitt kan förekomma två gånger vid en punktlast)."""
    case_M: dict[str, list[float]]
    """Karakteristiskt moment (kNm) per lastfall i varje snitt."""
    case_V: dict[str, list[float]]
    effects: list[CombinationEffect]
    governing: dict[str, dict[str, str]]
    """``governing[grupp]["M" | "V"]`` = id för den dimensionerande kombinationen."""
    log: CalcLog
    warnings: list[str] = field(default_factory=list)

    def get(self, cid: str) -> CombinationEffect:
        for e in self.effects:
            if e.combination.id == cid:
                return e
        raise KeyError(cid)

    def design(self, group: str, quantity: str = "M") -> CombinationEffect:
        return self.get(self.governing[group][quantity])

    def envelope(self, group: str) -> dict[str, list[float]]:
        """Omhylling över gruppens kombinationer: max/min av M (kNm) och V (kN) i varje snitt."""
        members = [e for e in self.effects if e.combination.group == group]
        n = len(self.x)
        return {
            "M_max": [max(e.M_env[0][i] for e in members) for i in range(n)],
            "M_min": [min(e.M_env[1][i] for e in members) for i in range(n)],
            "V_max": [max(e.V_env[0][i] for e in members) for i in range(n)],
            "V_min": [min(e.V_env[1][i] for e in members) for i in range(n)],
        }


def _combine(combo: Combination, values: dict[str, float], sign: int) -> tuple[float, dict]:
    """Summa f_i·E_i där f_i väljs ogynnsam om E_i drar åt ``sign`` (+1 max, -1 min)."""
    total = 0.0
    used: dict[str, float] = {}
    for t in combo.terms:
        e = values[t.case_id]
        unfav = e * sign > 0
        f = t.unfav if unfav else t.fav
        used[t.case_id] = f
        total += f * e
    return total, used


def design_effects(span: Q_, cases: list[LoadCase], combos: CombinationSet) -> DesignEffects:
    """Snittkrafter för alla kombinationer på en fritt upplagd balk, och de dimensionerande."""
    L = float(span.to("m").magnitude)
    log = CalcLog(title="Dimensionerande snittkrafter")
    pts = sample_points(L, [c.loads for c in cases])
    xs = [x for x, _ in pts]
    case_M: dict[str, list[float]] = {}
    case_V: dict[str, list[float]] = {}
    for c in cases:
        mv = [forces_at(L, c.loads, x, right) for x, right in pts]
        case_M[c.id] = [m for m, _ in mv]
        case_V[c.id] = [v for _, v in mv]

    # Karakteristiska stödreaktioner per lastfall, för att kunna följa summeringen.
    case_R = {c.id: reactions(span, c.loads) for c in cases}
    for c in cases:
        RA, _ = case_R[c.id]
        log.step(
            symbol=rf"R_{{A,\mathrm{{{c.id}}}}}",
            description=f"{c.name}: stödreaktion vid A (karakteristisk)",
            formula=r"\frac{\sum F_i \, (L - x_i)}{L}",
            substituted="",
            result=RA,
            ref="Momentjämvikt kring B",
        )

    effects: list[CombinationEffect] = []
    for combo in combos.combinations:
        Mmax, Mmin, Vmax, Vmin = [], [], [], []
        for i in range(len(pts)):
            mvals = {cid: case_M[cid][i] for cid in case_M}
            vvals = {cid: case_V[cid][i] for cid in case_V}
            Mmax.append(_combine(combo, mvals, +1)[0])
            Mmin.append(_combine(combo, mvals, -1)[0])
            Vmax.append(_combine(combo, vvals, +1)[0])
            Vmin.append(_combine(combo, vvals, -1)[0])
        iM = max(range(len(xs)), key=lambda i: (round(Mmax[i], 9), -abs(xs[i] - L / 2)))
        xM, mvals_M = _refine_max(L, cases, combo, pts, iM, case_M, case_V)
        M_top, _ = _combine(combo, mvals_M, +1)
        iMn = min(range(len(xs)), key=lambda i: Mmin[i])
        iV = max(range(len(xs)), key=lambda i: max(Vmax[i], -Vmin[i]))
        Vabs = max(Vmax[iV], -Vmin[iV])
        RA, RB = (
            sum(
                (combo.factor(cid, R[k].magnitude >= 0) * R[k] for cid, R in case_R.items()),
                Q_(0, "kN"),
            )
            for k in (0, 1)
        )
        eff = CombinationEffect(
            combination=combo,
            M_max=Q_(M_top, "kN*m"),
            x_M_max=Q_(xM, "m"),
            M_min=Q_(min(0.0, Mmin[iMn]), "kN*m"),
            x_M_min=Q_(xs[iMn], "m"),
            V_abs=Q_(Vabs, "kN"),
            x_V=Q_(xs[iV], "m"),
            R_A=RA.to("kN"),
            R_B=RB.to("kN"),
            M_env=(Mmax, Mmin),
            V_env=(Vmax, Vmin),
        )
        effects.append(eff)
        _log_effect(log, combo, "M", xM, mvals_M, +1)
        sign = +1 if Vmax[iV] >= -Vmin[iV] else -1
        _log_effect(log, combo, "V", xs[iV], {k: v[iV] for k, v in case_V.items()}, sign)

    governing: dict[str, dict[str, str]] = {}
    for group, label in GROUPS.items():
        members = [e for e in effects if e.combination.group == group]
        if not members:
            continue
        gM = max(members, key=lambda e: abs(e.M_abs.magnitude))
        gV = max(members, key=lambda e: e.V_abs.magnitude)
        governing[group] = {"M": gM.combination.id, "V": gV.combination.id}
        tag = {
            "uls": "Ed",
            "characteristic": r"Ek,\mathrm{kar}",
            "frequent": r"Ek,\mathrm{frekv}",
            "quasi_permanent": r"Ek,\mathrm{kvasi}",
        }[group]
        _log_max(log, tag, label, "moment", members, "M", gM)
        _log_max(log, tag, label, "tvärkraft", members, "V", gV)

    return DesignEffects(xs, case_M, case_V, effects, governing, log)


def _refine_max(
    L: float,
    cases: list[LoadCase],
    combo: Combination,
    pts: list[tuple[float, bool]],
    i: int,
    case_M: dict[str, list[float]],
    case_V: dict[str, list[float]],
) -> tuple[float, dict[str, float]]:
    """Exakt läge för största moment: där tvärkraften byter tecken (dM/dx = V).

    Mellan två intilliggande snitt finns inga lastkanter, så tvärkraften är linjär och
    nollstället fås med linjär interpolation. Ger samma x som en handräkning.
    """
    best_x = pts[i][0]
    best_vals = {k: v[i] for k, v in case_M.items()}
    best, used = _combine(combo, best_vals, +1)
    for j in (i - 1, i):
        if j < 0 or j + 1 >= len(pts):
            continue
        x0, x1 = pts[j][0], pts[j + 1][0]
        if x1 <= x0:
            continue
        v0 = sum(used[k] * case_V[k][j] for k in used)
        v1 = sum(used[k] * case_V[k][j + 1] for k in used)
        if v0 > 0 > v1:
            xr = x0 + v0 / (v0 - v1) * (x1 - x0)
            vals = {c.id: forces_at(L, c.loads, xr)[0] for c in cases}
            m, _ = _combine(combo, vals, +1)
            if m > best + 1e-12:
                best, best_x, best_vals = m, xr, vals
    return best_x, best_vals


def _log_effect(
    log: CalcLog,
    combo: Combination,
    q: str,
    x: float,
    vals: dict[str, float],
    sign: int,
) -> None:
    total, used = _combine(combo, vals, sign)
    unit = "kN*m" if q == "M" else "kN"
    terms = [t for t in combo.terms if abs(vals[t.case_id]) > 1e-12]
    what = "Största moment" if q == "M" else "Största tvärkraft"
    sub = "Ed" if combo.group == "uls" else "Ek"
    log.step(
        symbol=rf"{q}_{{{sub},\mathrm{{{combo.id}}}}}",
        description=f"{combo.name}: {what.lower()}, x = {_fmt(round(x, 3))} m",
        formula=" + ".join(
            rf"f_{{\mathrm{{{t.case_id}}}}} \, {q}_{{k,\mathrm{{{t.case_id}}}}}" for t in terms
        )
        or "0",
        substituted=" + ".join(_term_str(t, used[t.case_id], vals[t.case_id]) for t in terms),
        result=Q_(round(total, 9), unit),
        ref=REF,
    )


def _term_str(t, f: float, v: float) -> str:
    """En term i handräkningsform: faktorns delar gånger lastfallets snittkraft."""
    num = t.numeric() if f == t.unfav else (_fmt(f) if f != 1.0 else "")
    return rf"{num} \cdot {_paren(v)}" if num else _paren(v)


def _paren(v: float) -> str:
    s = _fmt(round(v, 4))
    return f"({s})" if v < 0 else s


def _log_max(
    log: CalcLog,
    tag: str,
    label: str,
    what: str,
    members: list[CombinationEffect],
    q: str,
    gov: CombinationEffect,
) -> None:
    def val(e: CombinationEffect) -> Q_:
        return e.M_abs if q == "M" else e.V_abs

    sub = "Ed" if gov.combination.group == "uls" else "Ek"
    log.step(
        symbol=f"{q}_{{{tag}}}",
        description=f"{label}: störst {what} ger {gov.combination.name}",
        formula=rf"\max_j |{q}_{{{sub},j}}|",
        substituted=r"\max(" + "; ".join(_fmt(abs(val(e).magnitude)) for e in members) + ")",
        result=abs(val(gov)),
        ref="EN 1990 6.4.3.2 och 6.5.3",
    )
