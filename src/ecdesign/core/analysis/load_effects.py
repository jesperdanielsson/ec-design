r"""Snittkrafter och nedböjning för varje lastkombination, och vilken som blir dimensionerande.

Varje lastfall räknas för sig med karakteristiska värden (superposition, linjärt elastisk
analys, EN 1990 6.3.2 och EN 1992-1-1 5.4). I varje snitt kombineras lastfallen med
kombinationens faktorer: ett lastfall som ökar snittkraften får den ogynnsamma faktorn,
ett som minskar den får den gynnsamma (EN 1990 6.4.3.2(3) och tabell A1.2(B) anm. 3).

.. math::
    M_{Ed}(x) = \sum_i f_i(x) \, M_{k,i}(x)

**Mönsterbelastning (fri last).** En permanent last är bunden: hela lastfallet får samma
faktor (EN 1990 tabell A1.2(B) anm. 3, "samma ursprung"). En variabel last på en balk med
flera fack är fri: den delas upp fack för fack, och i varje snitt tas bara de fack med där
lasten verkar ogynnsamt (Bärande konstruktioner del 1, fig. K1.12; EN 1992-1-1 5.1.3).
Det ger den ogynnsammaste av alla lastuppställningar, vilket täcker de förenklade
uppställningarna (a) och (b) i EN 1992-1-1 5.1.3 anm.

Den dimensionerande kombinationen i en grupp (brottgräns, karakteristisk, frekvent,
kvasipermanent) är den som ger störst värde någonstans längs balken.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..calclog import CalcLog, _fmt
from ..loads.actions import LoadCase, LoadKind
from ..loads.combinations import GROUPS, Combination, CombinationSet
from ..units import Q_
from .beam import BeamSystem, Solution, sample_points, solve, split_by_span

REF = "EN 1990 6.3.2 och 6.4.3.2(3); linjärelastisk analys EN 1992-1-1 5.4"
REF_PATTERN = "EN 1992-1-1 5.1.3; Bärande konstruktioner del 1 fig. K1.12 (fri last)"
REF_FE = "Förskjutningsmetoden, elementarfall (Diverse utdrag 2018 bilaga B)"
TINY = 1e-9


@dataclass
class _Part:
    """Ett lastfall, eller den del av ett variabelt lastfall som ligger på ett fack."""

    case_id: str
    span: int | None
    sol: Solution
    M: list[float]
    V: list[float]
    w: list[float]


@dataclass
class Extreme:
    """Ett största/minsta värde och var det uppträder."""

    value: Q_
    x: Q_
    loaded_spans: dict[str, list[int]] = field(default_factory=dict)
    """Variabla lastfall: vilka fack (index från 0) som är belastade för detta värde."""
    used: dict[str, tuple[float, float, list[int]]] = field(default_factory=dict, repr=False)
    """Faktor och belastade delar per lastfall, dvs. lastuppställningen som ger värdet."""


@dataclass
class LoadArrangement:
    """En bestämd lastuppställning i en kombination: fasta faktorer och belastade fack.

    Med mönsterbelastning ger en kombination olika uppställningar för olika snitt (t.ex.
    fältmoment i fack 1 eller stödmoment i B). Varje uppställning är ett vanligt lastfall
    med en enda M-, V- och nedböjningskurva, som i en handräkning.
    """

    purposes: list[str]
    """Vad uppställningen är dimensionerande för, t.ex. "största fältmoment i fack 1"."""
    factors: dict[str, float]
    loaded_spans: dict[str, list[int]]
    M: list[float]
    """Moment i kNm i varje snitt."""
    V: list[float]
    w: list[float] | None
    """Nedböjning i mm i varje snitt."""
    peaks: list[tuple[str, float, float]] = field(default_factory=list)
    """Exakta extremvärden (storhet "M"/"V"/"w", x i m, värde) som uppställningen ger."""


@dataclass
class SpanResult:
    """Resultat för ett fack: största fältmoment och största nedböjning."""

    index: int
    M_max: Extreme
    w_max: Extreme | None


@dataclass
class CombinationEffect:
    combination: Combination
    M_max: Q_
    """Största positiva moment (dragning i underkant). Noll om inget fältmoment finns."""
    x_M_max: Q_
    M_min: Q_
    """Minsta (mest negativa) moment, t.ex. stödmoment. Noll om inget negativt moment finns."""
    x_M_min: Q_
    V_abs: Q_
    """Största tvärkraft till beloppet."""
    x_V: Q_
    reactions: list[tuple[Q_, Q_]]
    """(största, minsta) upplagsreaktion i varje stöd, positiv uppåt (tryck mot stödet)."""
    support_M: list[Q_]
    """Minsta moment över varje stöd (stödmoment/inspänningsmoment), 0 vid fria ändar."""
    spans: list[SpanResult]
    w_max: Q_ | None
    """Största nedböjning (nedåt). ``None`` om EI saknas."""
    x_w: Q_ | None
    M_env: tuple[list[float], list[float]]
    """(max, min) moment i kNm i varje snitt, för diagram."""
    V_env: tuple[list[float], list[float]]
    """(max, min) tvärkraft i kN i varje snitt, för diagram."""
    w_env: tuple[list[float], list[float]] | None
    """(max, min) nedböjning i mm i varje snitt."""
    loaded_spans_M: dict[str, list[int]] = field(default_factory=dict)
    arrangements: list[LoadArrangement] = field(default_factory=list)
    """Lastuppställningarna som ger kombinationens största värden, med egna kurvor."""

    @property
    def M_abs(self) -> Q_:
        return self.M_max if abs(self.M_max) >= abs(self.M_min) else self.M_min

    @property
    def x_M_abs(self) -> Q_:
        return self.x_M_max if abs(self.M_max) >= abs(self.M_min) else self.x_M_min

    @property
    def R_A(self) -> Q_:
        """Största reaktion i första stödet (bakåtkompatibelt med fritt upplagd balk)."""
        return self.reactions[0][0]

    @property
    def R_B(self) -> Q_:
        return self.reactions[-1][0]


@dataclass
class DesignEffects:
    system: BeamSystem
    x: list[float]
    """Snittens läge i m (ett snitt kan förekomma två gånger vid stöd och punktlaster)."""
    case_M: dict[str, list[float]]
    """Karakteristiskt moment (kNm) per lastfall i varje snitt, hela lastfallet."""
    case_V: dict[str, list[float]]
    case_w: dict[str, list[float]] | None
    """Karakteristisk nedböjning (mm) per lastfall, om EI är känt."""
    effects: list[CombinationEffect]
    governing: dict[str, dict[str, str]]
    """``governing[grupp][storhet]`` = id för den dimensionerande kombinationen.
    Storheter: ``M`` (störst till beloppet), ``M_pos``, ``M_neg``, ``V`` och ``w``."""
    log: CalcLog
    pattern: bool
    EI: Q_ | None
    warnings: list[str] = field(default_factory=list)

    def get(self, cid: str) -> CombinationEffect:
        for e in self.effects:
            if e.combination.id == cid:
                return e
        raise KeyError(cid)

    def design(self, group: str, quantity: str = "M") -> CombinationEffect:
        return self.get(self.governing[group][quantity])

    def envelope(self, group: str) -> dict[str, list[float]]:
        """Omhylling över gruppens kombinationer: max/min av M (kNm), V (kN) och w (mm)."""
        members = [e for e in self.effects if e.combination.group == group]
        n = len(self.x)
        out = {
            "M_max": [max(e.M_env[0][i] for e in members) for i in range(n)],
            "M_min": [min(e.M_env[1][i] for e in members) for i in range(n)],
            "V_max": [max(e.V_env[0][i] for e in members) for i in range(n)],
            "V_min": [min(e.V_env[1][i] for e in members) for i in range(n)],
        }
        if all(e.w_env for e in members):
            out["w_max"] = [max(e.w_env[0][i] for e in members) for i in range(n)]
            out["w_min"] = [min(e.w_env[1][i] for e in members) for i in range(n)]
        return out


# --- Kombinering i ett snitt ----------------------------------------------------


def _combine(
    combo: Combination, values: dict[str, list[float]], sign: int
) -> tuple[float, dict[str, tuple[float, float, list[int]]]]:
    """Summa f·E i ett snitt, ogynnsamt åt ``sign`` (+1 största, −1 minsta).

    ``values[lastfall]`` är lastfallets delar: en del för en bunden last, en per fack för en
    fri (mönsterbelastad) last. Bunden last: hela lastfallet får samma faktor. Fri last:
    varje del tas med ogynnsam faktor om den drar åt ``sign``, annars gynnsam (0).
    Returnerar summan och, per lastfall, (faktor, lastfallets värde, belastade delar).
    """
    total = 0.0
    used: dict[str, tuple[float, float, list[int]]] = {}
    for t in combo.terms:
        parts = values.get(t.case_id, [0.0])
        if t.permanent or len(parts) == 1:
            e = sum(parts)
            f = t.unfav if e * sign > 0 else t.fav
            total += f * e
            used[t.case_id] = (f, e, list(range(len(parts))))
            continue
        loaded = [j for j, p in enumerate(parts) if p * sign > TINY]
        e_unf = sum(parts[j] for j in loaded)
        e_fav = sum(p for j, p in enumerate(parts) if j not in loaded)
        total += t.unfav * e_unf + t.fav * e_fav
        used[t.case_id] = (t.unfav, e_unf, loaded)
    return total, used


@dataclass
class _Model:
    system: BeamSystem
    cases: list[LoadCase]
    parts: dict[str, list[_Part]]
    pts: list[tuple[float, bool]]
    has_EI: bool

    def values(self, q: str, i: int) -> dict[str, list[float]]:
        return {cid: [getattr(p, q)[i] for p in ps] for cid, ps in self.parts.items()}

    def values_at(self, q: str, x: float, right: bool = True) -> dict[str, list[float]]:
        k = "MVw".index(q)
        scale = 1000.0 if q == "w" else 1.0  # nedböjning i mm
        return {cid: [p.sol.at(x, right)[k] * scale for p in ps] for cid, ps in self.parts.items()}

    def span_names(self, case_id: str, loaded: list[int]) -> list[int]:
        """Belastade delar -> fackindex."""
        ps = self.parts[case_id]
        return [ps[j].span for j in loaded if ps[j].span is not None]


def _build(system: BeamSystem, cases: list[LoadCase], EI: float, pattern: bool) -> _Model:
    pts = sample_points(system, [c.loads for c in cases])
    parts: dict[str, list[_Part]] = {}
    for c in cases:
        if c.kind is LoadKind.VARIABLE and pattern and system.n_spans > 1:
            groups = [
                (j, loads) for j, loads in enumerate(split_by_span(system, c.loads)) if loads
            ] or [(None, [])]
        else:
            groups = [(None, c.loads)]
        ps = []
        for span, loads in groups:
            sol = solve(system, loads, EI)
            vals = [sol.at(x, right) for x, right in pts]
            ps.append(
                _Part(
                    c.id,
                    span,
                    sol,
                    [v[0] for v in vals],
                    [v[1] for v in vals],
                    [v[2] * 1000 for v in vals],  # mm
                )
            )
        parts[c.id] = ps
    return _Model(system, cases, parts, pts, EI > 0)


# --- Huvudfunktion ----------------------------------------------------------------


def design_effects(
    system: BeamSystem | Q_,
    cases: list[LoadCase],
    combos: CombinationSet,
    EI: Q_ | None = None,
    pattern: bool = True,
) -> DesignEffects:
    """Snittkrafter och nedböjning för alla kombinationer, och de dimensionerande.

    ``system``: balkens statiska system, eller en spännvidd (fritt upplagd balk).
    ``EI``: böjstyvhet för nedböjningen (t.ex. E_cm·I_c). Utan EI räknas bara snittkrafter.
    ``pattern``: mönsterbelastning av variabla laster fack för fack (EN 1992-1-1 5.1.3).
    """
    if not isinstance(system, BeamSystem):
        system = BeamSystem.simply_supported(system)
    EI_val = float(EI.to("kN*m^2").magnitude) if EI is not None else 1.0
    pattern = pattern and system.n_spans > 1
    model = _build(system, cases, EI_val, pattern)
    pts = model.pts
    xs = [x for x, _ in pts]
    xs_sup = system.x_nodes()
    log = CalcLog(title="Snittkrafter och nedböjning")
    warnings: list[str] = []

    _log_system(log, system, pattern, cases)
    _log_cases(log, model)

    effects: list[CombinationEffect] = []
    n = len(pts)
    quantities = ("M", "V", "w") if EI is not None else ("M", "V")
    cache = {q: [model.values(q, i) for i in range(n)] for q in quantities}
    for combo in combos.combinations:
        env = {}
        for q in quantities:
            vals = cache[q]
            env[q] = (
                [_combine(combo, v, +1)[0] for v in vals],
                [_combine(combo, v, -1)[0] for v in vals],
            )
        Mmax, Mmin = env["M"]
        Vmax, Vmin = env["V"]

        top = _extreme_M(model, combo, range(n), +1, Mmax)
        bot = _extreme_M(model, combo, range(n), -1, Mmin)
        iV = max(range(n), key=lambda i: max(Vmax[i], -Vmin[i]))
        Vabs = max(Vmax[iV], -Vmin[iV])

        reactions = []
        support_M = []
        support_used: dict[int, dict] = {}
        for k, s in enumerate(system.supports):
            vals = {cid: [p.sol.reactions[k] for p in ps] for cid, ps in model.parts.items()}
            reactions.append(
                (Q_(_combine(combo, vals, +1)[0], "kN"), Q_(_combine(combo, vals, -1)[0], "kN"))
            )
            if s.value == "free":
                support_M.append(Q_(0.0, "kN*m"))
            else:
                mv = model.values_at("M", xs_sup[k], right=(k == 0))
                m_sup, support_used[k] = _combine(combo, mv, -1)
                support_M.append(Q_(min(0.0, m_sup), "kN*m"))

        spans: list[SpanResult] = []
        for j in range(system.n_spans):
            idx = [i for i in range(n) if xs_sup[j] - TINY <= xs[i] <= xs_sup[j + 1] + TINY]
            mspan = _extreme_M(model, combo, idx, +1, Mmax)
            wspan = _extreme_w(model, combo, idx, env["w"][0]) if EI is not None else None
            spans.append(SpanResult(j, mspan, wspan))

        w_max = x_w = None
        if EI is not None:
            ws = [s.w_max for s in spans if s.w_max is not None]
            best = max(ws, key=lambda e: e.value.magnitude)
            w_max, x_w = best.value, best.x

        eff = CombinationEffect(
            combination=combo,
            M_max=top.value if top.value.magnitude > TINY else Q_(0.0, "kN*m"),
            x_M_max=top.x,
            M_min=bot.value if bot.value.magnitude < -TINY else Q_(0.0, "kN*m"),
            x_M_min=bot.x,
            V_abs=Q_(Vabs, "kN"),
            x_V=Q_(xs[iV], "m"),
            reactions=reactions,
            support_M=support_M,
            spans=spans,
            w_max=w_max,
            x_w=x_w,
            M_env=(Mmax, Mmin),
            V_env=(Vmax, Vmin),
            w_env=env.get("w"),
            loaded_spans_M=top.loaded_spans,
        )
        eff.arrangements = _arrangements(
            model,
            combo,
            eff,
            support_used,
            _combine(combo, cache["V"][iV], 1 if Vmax[iV] >= -Vmin[iV] else -1)[1],
            cache,
        )
        effects.append(eff)
        _log_combination(log, model, combo, eff, pts, iV, Vmax[iV] >= -Vmin[iV])

    governing = _governing(effects, EI is not None)
    for group, gov in governing.items():
        _log_governing(log, system, group, effects, gov)

    for k, s in enumerate(system.supports):
        if s.value == "free":
            continue
        Rmin = min(e.reactions[k][1].magnitude for e in effects if e.combination.group == "uls")
        if Rmin < -1e-6:
            warnings.append(
                f"Stöd {system.label(k)} kan få en lyftande kraft (R = {_num(Rmin)} kN i "
                "brottgräns). Kontrollera statisk jämvikt (EQU, EN 1990 tabell A1.2(A)) och "
                "förankring. EQU ingår inte än."
            )

    case_w = None
    if EI is not None:
        case_w = {cid: _sum_parts(ps, "w") for cid, ps in model.parts.items()}
    return DesignEffects(
        system=system,
        x=xs,
        case_M={cid: _sum_parts(ps, "M") for cid, ps in model.parts.items()},
        case_V={cid: _sum_parts(ps, "V") for cid, ps in model.parts.items()},
        case_w=case_w,
        effects=effects,
        governing=governing,
        log=log,
        pattern=pattern,
        EI=EI,
        warnings=warnings,
    )


def _sum_parts(ps: list[_Part], q: str) -> list[float]:
    arrs = [getattr(p, q) for p in ps]
    return [sum(a[i] for a in arrs) for i in range(len(arrs[0]))]


def _num(v: float, d: int = 1) -> str:
    return f"{v:.{d}f}".replace(".", ",")


# --- Sökning av extremvärden ---------------------------------------------------------


def _loaded(model: _Model, used: dict[str, tuple[float, float, list[int]]]) -> dict:
    out = {}
    for cid, (_, _, loaded) in used.items():
        if len(model.parts[cid]) > 1:
            out[cid] = model.span_names(cid, loaded)
    return out


def _extreme_M(model: _Model, combo: Combination, idx, sign: int, arr: list[float]) -> Extreme:
    """Största (sign = +1) eller minsta (−1) moment bland snitten ``idx``, med exakt läge.

    Mellan två intilliggande snitt finns inga lastkanter, så tvärkraften är linjär och
    momentets extremvärde ligger där V = 0 (dM/dx = V). Ger samma x som en handräkning.
    """
    idx = list(idx)
    pts = model.pts
    mid = (pts[idx[0]][0] + pts[idx[-1]][0]) / 2
    i = max(idx, key=lambda k: (round(sign * arr[k], 9), round(-abs(pts[k][0] - mid), 6), -k))
    best_x = pts[i][0]
    best_val, used = _combine(combo, model.values("M", i), sign)
    lo, hi = idx[0], idx[-1]
    for j in (i - 1, i):
        if j < lo or j + 1 > hi:
            continue
        x0, x1 = pts[j][0], pts[j + 1][0]
        if x1 <= x0:
            continue
        v0 = _fixed(combo, used, model.values("V", j))
        v1 = _fixed(combo, used, model.values("V", j + 1))
        if v0 * v1 < 0 and (v0 > 0) == (sign > 0):
            xr = x0 + v0 / (v0 - v1) * (x1 - x0)
            m, u2 = _combine(combo, model.values_at("M", xr), sign)
            if sign * m > sign * best_val + 1e-12:
                best_val, best_x, used = m, xr, u2
    return Extreme(Q_(best_val, "kN*m"), Q_(best_x, "m"), _loaded(model, used), used)


def _arrangements(
    model: _Model,
    combo: Combination,
    eff: CombinationEffect,
    support_used: dict[int, dict],
    V_used: dict,
    cache: dict[str, list[dict[str, list[float]]]],
) -> list[LoadArrangement]:
    """Kombinationens dimensionerande lastuppställningar, var och en med egna kurvor.

    Uppställningar med samma faktorer och belastade fack slås ihop; deras syften listas.
    """
    system = model.system
    xs_sup = system.x_nodes()
    sources: list[tuple[str, dict, tuple | None]] = []
    for s in eff.spans:
        e = s.M_max
        if e.value.magnitude > TINY and e.used:
            what = "konsolen" if system.is_cantilever_span(s.index) else f"fack {s.index + 1}"
            peak = ("M", float(e.x.magnitude), float(e.value.magnitude))
            sources.append((f"fältmoment i {what}", e.used, peak))
    for k, used in support_used.items():
        if eff.support_M[k].magnitude < -TINY:
            what = "inspänningsmoment" if system.supports[k].value == "fixed" else "stödmoment"
            peak = ("M", xs_sup[k], float(eff.support_M[k].magnitude))
            sources.append((f"{what} i {system.label(k)}", used, peak))
    sources.append(("tvärkraft", V_used, None))
    if combo.group != "uls":
        for s in eff.spans:
            e = s.w_max
            if e is not None and e.value.magnitude > 1e-6 and e.used:
                peak = ("w", float(e.x.magnitude), float(e.value.magnitude))
                sources.append((f"nedböjning i fack {s.index + 1}", e.used, peak))
    out: dict[tuple, LoadArrangement] = {}
    n = len(model.pts)
    for purpose, used, peak in sources:
        key = tuple(sorted((cid, round(f, 9), tuple(ld)) for cid, (f, _, ld) in used.items()))
        if key in out:
            out[key].purposes.append(purpose)
            if peak:
                out[key].peaks.append(peak)
            continue
        curves = {q: [_fixed(combo, used, cache[q][i]) for i in range(n)] for q in cache}
        out[key] = LoadArrangement(
            purposes=[purpose],
            factors={cid: f for cid, (f, _, _) in used.items()},
            loaded_spans=_loaded(model, used),
            M=curves["M"],
            V=curves["V"],
            w=curves.get("w"),
            peaks=[peak] if peak else [],
        )
    return list(out.values())


def _fixed(combo: Combination, used, values: dict[str, list[float]]) -> float:
    """Kombinerat värde med samma belastade delar och faktorer som i ``used``."""
    total = 0.0
    for t in combo.terms:
        f, _, loaded = used[t.case_id]
        parts = values[t.case_id]
        total += f * sum(parts[j] for j in loaded)
        total += t.fav * sum(p for j, p in enumerate(parts) if j not in loaded)
    return total


def _extreme_w(model: _Model, combo: Combination, idx, arr: list[float]) -> Extreme:
    """Största nedböjning (mm) bland snitten ``idx``, förfinad med gyllene snittet."""
    idx = list(idx)
    pts = model.pts
    i = max(idx, key=lambda k: arr[k])
    a = pts[max(idx[0], i - 1)][0]
    b = pts[min(idx[-1], i + 1)][0]

    def f(x: float) -> float:
        return _combine(combo, model.values_at("w", x), +1)[0]

    best_x, best = pts[i][0], arr[i]
    if b - a > 1e-9:
        g = (math.sqrt(5) - 1) / 2
        c, d = b - g * (b - a), a + g * (b - a)
        fc, fd = f(c), f(d)
        for _ in range(60):
            if fc > fd:
                b, d, fd = d, c, fc
                c = b - g * (b - a)
                fc = f(c)
            else:
                a, c, fc = c, d, fd
                d = a + g * (b - a)
                fd = f(d)
        xm = (a + b) / 2
        fm = f(xm)
        if fm > best:
            best, best_x = fm, xm
    _, used = _combine(combo, model.values_at("w", best_x), +1)
    return Extreme(Q_(best, "mm"), Q_(best_x, "m"), _loaded(model, used), used)


# --- Dimensionerande kombination ------------------------------------------------------


def _governing(effects: list[CombinationEffect], has_w: bool) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for group in GROUPS:
        members = [e for e in effects if e.combination.group == group]
        if not members:
            continue
        g = {
            "M": max(members, key=lambda e: abs(e.M_abs.magnitude)).combination.id,
            "M_pos": max(members, key=lambda e: e.M_max.magnitude).combination.id,
            "M_neg": min(members, key=lambda e: e.M_min.magnitude).combination.id,
            "V": max(members, key=lambda e: e.V_abs.magnitude).combination.id,
        }
        if has_w:
            g["w"] = max(members, key=lambda e: e.w_max.magnitude).combination.id
        out[group] = g
    return out


# --- Loggning ------------------------------------------------------------------------


def _log_system(log: CalcLog, system: BeamSystem, pattern: bool, cases: list[LoadCase]) -> None:
    xs = system.x_nodes()
    supports = ", ".join(
        f"{system.label(k)}: {s.label.lower()} (x = {_fmt(round(x, 3))} m)"
        for k, (s, x) in enumerate(zip(system.supports, xs, strict=True))
    )
    log.step(
        symbol=r"\text{System}",
        description=f"{system.description}. Stöd {supports}",
        formula=r"L_{tot} = " + " + ".join(_fmt(round(float(L.to('m').magnitude), 4))
                                            for L in system.spans),
        substituted="",
        result=system.length,
        ref="EN 1992-1-1 5.3.1 och 5.4 (linjärelastisk analys)",
    )  # fmt: skip
    if system.n_spans > 1 and any(c.kind is LoadKind.VARIABLE for c in cases):
        log.step(
            symbol=r"\text{Mönsterbelastning}",
            description=(
                "Variabla laster placeras fack för fack där de verkar ogynnsamt (fri last). "
                "Permanenta laster ligger på alla fack med samma faktor (bunden last)."
                if pattern
                else "Avstängd: variabla laster ligger alltid på hela balken (bunden last)."
            ),
            formula=r"\text{fri variabel last}" if pattern else r"\text{bunden variabel last}",
            substituted="",
            result="på" if pattern else "av",
            ref=REF_PATTERN,
        )


def _log_cases(log: CalcLog, model: _Model) -> None:
    """Karakteristiska stödreaktioner och stödmoment per lastfall (hela lastfallet)."""
    system = model.system
    xs = system.x_nodes()
    simple = system.n_spans == 1 and all(s.value == "pinned" for s in system.supports)
    for c in model.cases:
        ps = model.parts[c.id]
        for k, s in enumerate(system.supports):
            if s.value == "free":
                continue
            R = sum(p.sol.reactions[k] for p in ps)
            log.step(
                symbol=rf"R_{{{system.label(k)},\mathrm{{{c.id}}}}}",
                description=f"{c.name}: upplagsreaktion i stöd {system.label(k)} (karakteristisk)",
                formula=(r"\frac{\sum F_i \, (L - x_i)}{L}" if k == 0 else r"\sum F_i - R_A")
                if simple
                else r"\text{förskjutningsmetoden}",
                substituted="",
                result=Q_(round(R, 9), "kN"),
                ref="Momentjämvikt" if simple else REF_FE,
            )
            if s.value == "fixed" or 0 < k < system.n_spans:
                M = sum(p.sol.at(xs[k], right=(k == 0))[0] for p in ps)
                what = "inspänningsmoment" if s.value == "fixed" else "stödmoment"
                log.step(
                    symbol=rf"M_{{{system.label(k)},\mathrm{{{c.id}}}}}",
                    description=f"{c.name}: {what} i stöd {system.label(k)} (karakteristiskt)",
                    formula=r"\text{förskjutningsmetoden}",
                    substituted="",
                    result=Q_(round(M, 9), "kN*m"),
                    ref=REF_FE,
                )


def _spans_text(system: BeamSystem, loaded: dict[str, list[int]]) -> str:
    bits = []
    for cid, spans in loaded.items():
        if len(spans) == system.n_spans:
            continue
        where = ", ".join(str(j + 1) for j in spans) if spans else "inget fack"
        bits.append(f"{cid} på fack {where}")
    return f" ({'; '.join(bits)})" if bits else ""


def _log_combination(
    log: CalcLog,
    model: _Model,
    combo: Combination,
    eff: CombinationEffect,
    pts: list[tuple[float, bool]],
    iV: int,
    V_pos: bool,
) -> None:
    if eff.M_max.magnitude > TINY or eff.M_min.magnitude > -TINY:
        x = float(eff.x_M_max.magnitude)
        _log_effect(log, model, combo, "M", x, +1, "Största fältmoment", eff.loaded_spans_M)
    if eff.M_min.magnitude < -TINY:
        x = float(eff.x_M_min.magnitude)
        mv = model.values_at("M", x, right=x <= TINY)
        _, used = _combine(combo, mv, -1)
        _log_effect(log, model, combo, "M", x, -1, "Största negativa moment", _loaded(model, used),
                    symbol_suffix="-")  # fmt: skip
    x, right = pts[iV]
    vv = model.values("V", iV)
    sign = +1 if V_pos else -1
    _, used = _combine(combo, vv, sign)
    _log_effect(log, model, combo, "V", x, sign, "Största tvärkraft", _loaded(model, used),
                right=right)  # fmt: skip
    if eff.w_max is not None and combo.group != "uls":
        x = float(eff.x_w.magnitude)
        _, used = _combine(combo, model.values_at("w", x), +1)
        _log_effect(log, model, combo, "w", x, +1, "Största nedböjning", _loaded(model, used))


def _log_effect(
    log: CalcLog,
    model: _Model,
    combo: Combination,
    q: str,
    x: float,
    sign: int,
    what: str,
    loaded: dict[str, list[int]],
    right: bool = True,
    symbol_suffix: str = "",
) -> None:
    vals = model.values_at(q, x, right)
    total, used = _combine(combo, vals, sign)
    unit = {"M": "kN*m", "V": "kN", "w": "mm"}[q]
    sym_q = r"\delta" if q == "w" else q
    terms = []
    for t in combo.terms:
        f, e, ld = used[t.case_id]
        if abs(e) > 1e-12 and ld and f:
            terms.append((t, f, e))
    sub = "Ed" if combo.group == "uls" else "Ek"
    sub_sym = "d" if combo.group == "uls" else "k"
    log.step(
        symbol=rf"{sym_q}_{{{sub},\mathrm{{{combo.id}}}}}{symbol_suffix and '^{-}'}"
        if q != "w"
        else rf"\delta_{{{sub_sym},\mathrm{{{combo.id}}}}}",
        description=f"{combo.name}: {what.lower()}, x = {_fmt(round(x, 3))} m"
        + _spans_text(model.system, loaded),
        formula=" + ".join(
            rf"f_{{\mathrm{{{t.case_id}}}}} \, {sym_q}_{{k,\mathrm{{{t.case_id}}}}}"
            for t, _, _ in terms
        )
        or "0",
        substituted=" + ".join(_term_str(t, f, e) for t, f, e in terms),
        result=Q_(round(total, 9), unit),
        ref=REF if not loaded else f"{REF}; {REF_PATTERN}",
    )


def _term_str(t, f: float, v: float) -> str:
    """En term i handräkningsform: faktorns delar gånger lastfallets snittkraft."""
    num = t.numeric() if f == t.unfav else (_fmt(f) if f != 1.0 else "")
    return rf"{num} \cdot {_paren(v)}" if num else _paren(v)


def _paren(v: float) -> str:
    s = _fmt(round(v, 4))
    return f"({s})" if v < 0 else s


def _log_governing(
    log: CalcLog,
    system: BeamSystem,
    group: str,
    effects: list[CombinationEffect],
    gov: dict[str, str],
) -> None:
    members = [e for e in effects if e.combination.group == group]
    label = GROUPS[group]
    tag = {
        "uls": "Ed",
        "characteristic": r"Ek,\mathrm{kar}",
        "frequent": r"Ek,\mathrm{frekv}",
        "quasi_permanent": r"Ek,\mathrm{kvasi}",
    }[group]
    sub = "Ed" if group == "uls" else "Ek"
    by_id = {e.combination.id: e for e in members}

    def step(symbol: str, what: str, formula: str, vals: list[float], best: CombinationEffect,
             result: Q_, ref: str = "EN 1990 6.4.3.2 och 6.5.3") -> None:  # fmt: skip
        log.step(
            symbol=symbol,
            description=f"{label}: {what} ger {best.combination.name}",
            formula=formula,
            substituted=r"\max(" + "; ".join(_fmt(round(v, 4)) for v in vals) + ")",
            result=result,
            ref=ref,
        )

    gp = by_id[gov["M_pos"]]
    if gp.M_max.magnitude > TINY:
        step(f"M_{{{tag}}}", "störst fältmoment", rf"\max_j M_{{{sub},j}}",
             [e.M_max.magnitude for e in members], gp, gp.M_max)  # fmt: skip
    gn = by_id[gov["M_neg"]]
    if gn.M_min.magnitude < -TINY:
        step(f"M_{{{tag}}}^{{-}}", "störst stödmoment (negativt)", rf"\max_j |M^-_{{{sub},j}}|",
             [abs(e.M_min.magnitude) for e in members], gn, gn.M_min)  # fmt: skip
    gv = by_id[gov["V"]]
    step(f"V_{{{tag}}}", "störst tvärkraft", rf"\max_j |V_{{{sub},j}}|",
         [e.V_abs.magnitude for e in members], gv, gv.V_abs)  # fmt: skip
    if group != "uls" and "w" in gov:
        gw = by_id[gov["w"]]
        wtag = tag.replace("E", "")
        step(rf"\delta_{{{wtag}}}", "störst nedböjning", r"\max_j \delta_j",
             [e.w_max.magnitude for e in members], gw, gw.w_max,
             "Linjärelastisk, osprucket tvärsnitt (jfr EN 1992-1-1 7.4.3)")  # fmt: skip
        for j in range(system.n_spans):
            best = max(members, key=lambda e, j=j: e.spans[j].w_max.value.magnitude)
            s = best.spans[j]
            if s.w_max is None or s.w_max.value.magnitude <= 1e-6:
                continue
            L = system.spans[s.index].to("m")
            cant = system.is_cantilever_span(s.index)
            log.step(
                symbol=rf"L_{{{s.index + 1}}}/\delta_{{{wtag}}}",
                description=f"{label}: fack {s.index + 1}, {best.combination.name}"
                + (" (konsol: L är konsolens längd)" if cant else "")
                + ", jämför med L/250 i EN 1992-1-1 7.4.1(4)",
                formula=r"\frac{L}{\delta}",
                values={"L": L.to("mm"), r"\delta": s.w_max.value},
                result=round(float((L / s.w_max.value).to("").magnitude)),
                ref="EN 1992-1-1 7.4.1(4) (kontroll i steg 6)",
            )
