"""Armering enligt EN 1992-1-1 avsnitt 3.2 och bilaga C."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..calclog import CalcLog
from ..national import NationalAnnex
from ..national import load as load_annex
from ..units import Q_

# Namn -> (f_yk MPa, duktilitetsklass, epsilon_uk ‰, k = (f_t/f_y)_k)
GRADES: dict[str, tuple[int, str, float, float]] = {
    "B500B": (500, "B", 50.0, 1.08),
    "B500C": (500, "C", 75.0, 1.15),
}


@dataclass
class Reinforcement:
    name: str
    fyk: Q_
    ductility: str
    eps_uk: float
    """Töjning vid maxlast (‰)."""
    k: float
    Es: Q_
    gamma_s: float
    fyd: Q_
    eps_yd: float
    """Töjning vid flytning, dimensionerande (‰)."""
    log: CalcLog = field(repr=False)


def reinforcement(name: str = "B500B", annex: NationalAnnex | None = None) -> Reinforcement:
    """Ref: EN 1992-1-1 3.2.2, 3.2.7 och bilaga C (tabell C.1)."""
    if name not in GRADES:
        raise ValueError(f"Okänd armering {name!r}. Välj bland {', '.join(GRADES)}")
    annex = annex or load_annex("eks")
    fyk_v, ductility, eps_uk, k = GRADES[name]
    fyk = Q_(fyk_v, "MPa")
    Es = Q_(200, "GPa")
    gamma_s = float(annex.get("concrete.gamma_s"))
    log = CalcLog(title=f"Armering {name}")

    fyd = log.step(
        symbol="f_{yd}",
        description=f"Dimensionerande flytgräns ({annex.name})",
        formula=r"\frac{f_{yk}}{\gamma_s}",
        values={"f_{yk}": fyk, r"\gamma_s": gamma_s},
        result=fyk / gamma_s,
        ref="EN 1992-1-1 3.2.7(2), figur 3.8",
    )
    eps_yd = log.step(
        symbol=r"\varepsilon_{yd}",
        description="Töjning vid flytning (‰)",
        formula=r"\frac{f_{yd}}{E_s} \cdot 1000",
        values={"f_{yd}": fyd, "E_s": Es.to("MPa")},
        result=float((fyd / Es).to("").magnitude * 1000),
        ref="EN 1992-1-1 3.2.7(4)",
    )
    return Reinforcement(
        name=name,
        fyk=fyk,
        ductility=ductility,
        eps_uk=eps_uk,
        k=k,
        Es=Es,
        gamma_s=gamma_s,
        fyd=fyd,
        eps_yd=eps_yd,
        log=log,
    )
