"""Betong enligt EN 1992-1-1 avsnitt 3.1.

Alla egenskaper räknas fram ur f_ck med formlerna i tabell 3.1, och varje steg
loggas. Tabellens avrundade värden används bara i testerna, som kontroll.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..calclog import CalcLog
from ..national import NationalAnnex
from ..national import load as load_annex
from ..units import Q_

REF_T31 = "EN 1992-1-1 tabell 3.1"

# Hållfasthetsklasser i tabell 3.1: namn -> (f_ck, f_ck,cube) i MPa
STRENGTH_CLASSES: dict[str, tuple[int, int]] = {
    "C12/15": (12, 15),
    "C16/20": (16, 20),
    "C20/25": (20, 25),
    "C25/30": (25, 30),
    "C30/37": (30, 37),
    "C35/45": (35, 45),
    "C40/50": (40, 50),
    "C45/55": (45, 55),
    "C50/60": (50, 60),
    "C55/67": (55, 67),
    "C60/75": (60, 75),
    "C70/85": (70, 85),
    "C80/95": (80, 95),
    "C90/105": (90, 105),
}


@dataclass
class Concrete:
    """En betongklass med alla egenskaper från tabell 3.1 och dimensionerande värden.

    Skapa med :func:`concrete`, som räknar fram allt och fyller ``log``.
    """

    name: str
    fck: Q_
    fck_cube: Q_
    fcm: Q_
    fctm: Q_
    fctk_005: Q_
    fctk_095: Q_
    Ecm: Q_
    eps_c2: float
    """Töjning vid maxspänning, parabel-rektangel (‰)."""
    eps_cu2: float
    """Brottstukning, parabel-rektangel (‰)."""
    n: float
    """Exponent i parabel-rektangel-sambandet."""
    eps_c3: float
    """Töjning vid maxspänning, bilinjärt samband (‰)."""
    eps_cu3: float
    """Brottstukning, bilinjärt samband (‰)."""
    gamma_c: float
    alpha_cc: float
    fcd: Q_
    log: CalcLog = field(repr=False)


def concrete(name: str, annex: NationalAnnex | None = None) -> Concrete:
    """Räkna fram alla egenskaper för betongklassen ``name`` (t.ex. ``"C30/37"``).

    Ref: EN 1992-1-1 3.1.2, tabell 3.1 och 3.1.6 (f_cd). Nationella val (γ_c, α_cc)
    hämtas från ``annex`` (standard: EKS).
    """
    if name not in STRENGTH_CLASSES:
        raise ValueError(f"Okänd betongklass {name!r}. Välj bland {', '.join(STRENGTH_CLASSES)}")
    annex = annex or load_annex("eks")
    fck_v, fck_cube_v = STRENGTH_CLASSES[name]
    fck = Q_(fck_v, "MPa")
    fck_cube = Q_(fck_cube_v, "MPa")
    log = CalcLog(title=f"Betong {name}")

    fcm = log.step(
        symbol="f_{cm}",
        description="Medelvärde av cylinderhållfastheten",
        formula=r"f_{ck} + 8",
        values={"f_{ck}": fck},
        result=fck + Q_(8, "MPa"),
        ref=REF_T31,
    )

    if fck_v <= 50:
        fctm = log.step(
            symbol="f_{ctm}",
            description="Medelvärde av axiell draghållfasthet (≤ C50/60)",
            formula=r"0{,}30 \cdot f_{ck}^{2/3}",
            values={"f_{ck}": fck},
            result=Q_(0.30 * fck_v ** (2 / 3), "MPa"),
            ref=REF_T31,
        )
    else:
        fctm = log.step(
            symbol="f_{ctm}",
            description="Medelvärde av axiell draghållfasthet (> C50/60)",
            formula=r"2{,}12 \cdot \ln\left(1 + \frac{f_{cm}}{10}\right)",
            values={"f_{cm}": fcm},
            result=Q_(2.12 * math.log(1 + fcm.magnitude / 10), "MPa"),
            ref=REF_T31,
        )

    fctk_005 = log.step(
        symbol=r"f_{ctk,0{,}05}",
        description="Karakteristisk draghållfasthet, 5 %-fraktil",
        formula=r"0{,}7 \cdot f_{ctm}",
        values={"f_{ctm}": fctm},
        result=0.7 * fctm,
        ref=REF_T31,
    )
    fctk_095 = log.step(
        symbol=r"f_{ctk,0{,}95}",
        description="Karakteristisk draghållfasthet, 95 %-fraktil",
        formula=r"1{,}3 \cdot f_{ctm}",
        values={"f_{ctm}": fctm},
        result=1.3 * fctm,
        ref=REF_T31,
    )
    Ecm = log.step(
        symbol="E_{cm}",
        description="Elasticitetsmodul (sekantmodul), f_cm i MPa",
        formula=r"22 \cdot \left(\frac{f_{cm}}{10}\right)^{0{,}3}",
        values={"f_{cm}": fcm},
        result=Q_(22 * (fcm.magnitude / 10) ** 0.3, "GPa"),
        ref=REF_T31,
    )

    if fck_v < 50:
        # Under C50/60 är töjningsgränserna konstanta. De loggas ändå så att
        # lösningsgången blir komplett.
        eps_c2 = log.step(
            symbol=r"\varepsilon_{c2}",
            description="Töjning vid maxspänning (‰)",
            formula="2{,}0",
            result=2.0,
            ref=REF_T31,
        )
        eps_cu2 = log.step(
            symbol=r"\varepsilon_{cu2}",
            description="Brottstukning (‰)",
            formula="3{,}5",
            result=3.5,
            ref=REF_T31,
        )
        n = log.step(
            symbol="n",
            description="Exponent i parabel-rektangel",
            formula="2{,}0",
            result=2.0,
            ref=REF_T31,
        )
        eps_c3 = log.step(
            symbol=r"\varepsilon_{c3}",
            description="Töjning vid maxspänning, bilinjärt (‰)",
            formula="1{,}75",
            result=1.75,
            ref=REF_T31,
        )
        eps_cu3 = log.step(
            symbol=r"\varepsilon_{cu3}",
            description="Brottstukning, bilinjärt (‰)",
            formula="3{,}5",
            result=3.5,
            ref=REF_T31,
        )
    else:
        k = (90 - fck_v) / 100
        eps_c2 = log.step(
            symbol=r"\varepsilon_{c2}",
            description="Töjning vid maxspänning (‰), ≥ C50/60",
            formula=r"2{,}0 + 0{,}085 \cdot (f_{ck} - 50)^{0{,}53}",
            values={"f_{ck}": fck},
            result=2.0 + 0.085 * (fck_v - 50) ** 0.53,
            ref=REF_T31,
        )
        eps_cu2 = log.step(
            symbol=r"\varepsilon_{cu2}",
            description="Brottstukning (‰), ≥ C50/60",
            formula=r"2{,}6 + 35 \cdot \left(\frac{90 - f_{ck}}{100}\right)^4",
            values={"f_{ck}": fck},
            result=2.6 + 35 * k**4,
            ref=REF_T31,
        )
        n = log.step(
            symbol="n",
            description="Exponent i parabel-rektangel, ≥ C50/60",
            formula=r"1{,}4 + 23{,}4 \cdot \left(\frac{90 - f_{ck}}{100}\right)^4",
            values={"f_{ck}": fck},
            result=1.4 + 23.4 * k**4,
            ref=REF_T31,
        )
        eps_c3 = log.step(
            symbol=r"\varepsilon_{c3}",
            description="Töjning vid maxspänning, bilinjärt (‰), ≥ C50/60",
            formula=r"1{,}75 + 0{,}55 \cdot \frac{f_{ck} - 50}{40}",
            values={"f_{ck}": fck},
            result=1.75 + 0.55 * (fck_v - 50) / 40,
            ref=REF_T31,
        )
        eps_cu3 = eps_cu2

    gamma_c = float(annex.get("concrete.gamma_c"))
    alpha_cc = float(annex.get("concrete.alpha_cc"))
    fcd = log.step(
        symbol="f_{cd}",
        description=f"Dimensionerande tryckhållfasthet ({annex.name})",
        formula=r"\alpha_{cc} \cdot \frac{f_{ck}}{\gamma_c}",
        values={r"\alpha_{cc}": alpha_cc, "f_{ck}": fck, r"\gamma_c": gamma_c},
        result=alpha_cc * fck / gamma_c,
        ref="EN 1992-1-1 3.1.6(1)P, ekv. (3.15)",
    )

    return Concrete(
        name=name,
        fck=fck,
        fck_cube=fck_cube,
        fcm=fcm,
        fctm=fctm,
        fctk_005=fctk_005,
        fctk_095=fctk_095,
        Ecm=Ecm,
        eps_c2=eps_c2,
        eps_cu2=eps_cu2,
        n=n,
        eps_c3=eps_c3,
        eps_cu3=eps_cu3,
        gamma_c=gamma_c,
        alpha_cc=alpha_cc,
        fcd=fcd,
        log=log,
    )


def parabola_rectangle(c: Concrete, eps_c: float) -> Q_:
    """Dimensionerande betongspänning σ_c vid stukningen ``eps_c`` (‰).

    Ref: EN 1992-1-1 3.1.7, ekv. (3.17) och (3.18).
    """
    if eps_c < 0 or eps_c > c.eps_cu2:
        raise ValueError(f"Stukningen {eps_c} ‰ ligger utanför 0 … {c.eps_cu2:.2f} ‰")
    if eps_c < c.eps_c2:
        return c.fcd * (1 - (1 - eps_c / c.eps_c2) ** c.n)
    return c.fcd


def parabola_rectangle_curve(c: Concrete, points: int = 50) -> list[tuple[float, float]]:
    """Punkter (ε_c i ‰, σ_c i MPa) för att rita σ-ε-diagrammet."""
    out = []
    for i in range(points + 1):
        eps = c.eps_cu2 * i / points
        out.append((eps, float(parabola_rectangle(c, eps).to("MPa").magnitude)))
    return out
