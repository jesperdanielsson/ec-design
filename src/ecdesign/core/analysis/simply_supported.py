"""Fritt upplagd balk med jämnt utbredd last.

Första, enkla fallet. Kontinuerliga balkar och punktlaster kommer i steg 4 i planen.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..calclog import CalcLog
from ..loads.actions import PointLoad
from ..units import Q_

REF = "Elementarfall, fritt upplagd balk"


@dataclass
class SimplySupportedResult:
    M_max: Q_
    V_max: Q_
    log: CalcLog = field(repr=False)


def simply_supported_udl(L: Q_, q: Q_) -> SimplySupportedResult:
    """Max moment och tvärkraft för fritt upplagd balk med spännvidd ``L`` och last ``q``."""
    L = L.to("m")
    q = q.to("kN/m")
    log = CalcLog(title="Fritt upplagd balk, utbredd last")
    M = log.step(
        symbol=r"M_{\mathrm{max}}",
        description="Största moment, i mitten av spannet",
        formula=r"\frac{q \cdot L^2}{8}",
        values={"q": q, "L": L},
        result=(q * L**2 / 8).to("kN*m"),
        ref=REF,
    )
    V = log.step(
        symbol=r"V_{\mathrm{max}}",
        description="Största tvärkraft, vid stöden",
        formula=r"\frac{q \cdot L}{2}",
        values={"q": q, "L": L},
        result=(q * L / 2).to("kN"),
        ref=REF,
    )
    return SimplySupportedResult(M_max=M, V_max=V, log=log)


# --- Godtyckliga laster: utbredd, delutbredd och punktlast -------------------------
#
# Fritt upplagd balk, stöd A i x = 0 och B i x = L. Laster positiva nedåt.
# Elementarfall (se t.ex. "Diverse utdrag 2018", Chalmers, bilaga B.1):
#   punktlast P i a:        R_A = P (L - a) / L,  M(x) = R_A x - P <x - a>
#   delutbredd q på [a, b]: R_A = q (b - a) (L - c) / L med c = (a + b) / 2
#                           M(x) = R_A x - q <x - a>²/2 + q <x - b>²/2
# Beräkningarna görs i fasta enheter (m, kN, kNm) eftersom de körs i många snitt;
# in- och utdata är pint-storheter.


def _udl_parts(L: float, ld) -> tuple[float, float, float]:
    """(q i kN/m, a i m, b i m) för en utbredd last."""
    q = float(ld.q.to("kN/m").magnitude)
    a = 0.0 if ld.a is None else float(ld.a.to("m").magnitude)
    b = L if ld.b is None else float(ld.b.to("m").magnitude)
    return q, a, b


def forces_at(L: float, loads: list, x: float, right: bool = True) -> tuple[float, float]:
    """Moment (kNm) och tvärkraft (kN) i snittet ``x`` (m) för en fritt upplagd balk.

    ``right`` väljer tvärkraften strax till höger om snittet (vid en punktlast).
    Positivt moment ger dragning i underkant, positiv tvärkraft enligt elementarfallen.
    """
    M = 0.0
    V = 0.0
    for ld in loads:
        if isinstance(ld, PointLoad):
            P = float(ld.P.to("kN").magnitude)
            a = float(ld.a.to("m").magnitude)
            RA = P * (L - a) / L
            passed = x > a or (right and x >= a)
            M += RA * x - (P * (x - a) if x > a else 0.0)
            V += RA - (P if passed else 0.0)
        else:
            q, a, b = _udl_parts(L, ld)
            c = (a + b) / 2
            RA = q * (b - a) * (L - c) / L
            sa = max(0.0, x - a)
            sb = max(0.0, x - b)
            M += RA * x - q * sa**2 / 2 + q * sb**2 / 2
            V += RA - q * (min(x, b) - a if x > a else 0.0)
    return M, V


def _ra_and_total(L: float, ld) -> tuple[float, float]:
    """(R_A, lastens resultant) i kN för en last."""
    if isinstance(ld, PointLoad):
        P = float(ld.P.to("kN").magnitude)
        return P * (L - float(ld.a.to("m").magnitude)) / L, P
    q, a, b = _udl_parts(L, ld)
    F = q * (b - a)
    return F * (L - (a + b) / 2) / L, F


def reactions(L: Q_, loads: list) -> tuple[Q_, Q_]:
    """Stödreaktioner R_A och R_B ur momentjämvikt. Elementarfall, fritt upplagd balk."""
    Lm = float(L.to("m").magnitude)
    parts = [_ra_and_total(Lm, ld) for ld in loads]
    RA = sum(p[0] for p in parts)
    total = sum(p[1] for p in parts)
    return Q_(RA, "kN"), Q_(total - RA, "kN")


def sample_points(L: float, loads_per_case: list[list], n: int = 120) -> list[tuple[float, bool]]:
    """Snitt (x i m, höger-sida) för diagram och max-sökning.

    Jämn indelning (n delar, jämnt n så att mitten är med) plus lastkanter. Vid en
    punktlast tas båda sidorna med, så att tvärkraftens språng syns.
    """
    xs = {round(L * i / n, 9) for i in range(n + 1)}
    jumps: set[float] = set()
    for loads in loads_per_case:
        for ld in loads:
            if isinstance(ld, PointLoad):
                a = round(float(ld.a.to("m").magnitude), 9)
                xs.add(a)
                if 0 < a < L:
                    jumps.add(a)
            else:
                _, a, b = _udl_parts(L, ld)
                xs.update((round(a, 9), round(b, 9)))
    pts: list[tuple[float, bool]] = []
    for x in sorted(xs):
        if x in jumps:
            pts.append((x, False))
        pts.append((x, x < L))
    return pts
