"""Fritt upplagd balk med jämnt utbredd last.

Första, enkla fallet. Kontinuerliga balkar och punktlaster kommer i steg 4 i planen.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..calclog import CalcLog
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
