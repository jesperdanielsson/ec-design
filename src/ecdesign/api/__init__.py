"""Tunt lager mellan kärnan och gränssnittet.

Metoderna i :class:`Api` anropas från JavaScript via pywebview
(``window.pywebview.api.<metod>(...)``). De tar enkla värden (tal i fasta
enheter, strängar) och returnerar JSON-vänliga dict:ar inklusive beräkningsloggen.
Här finns ingen beräkningslogik, bara översättning.
"""

from __future__ import annotations

from typing import Any

from ..core import national
from ..core.analysis.simply_supported import simply_supported_udl
from ..core.materials.concrete import STRENGTH_CLASSES, concrete, parabola_rectangle_curve
from ..core.materials.reinforcement import GRADES, reinforcement
from ..core.units import Q_


def _q(q: Q_, unit: str) -> float:
    return round(float(q.to(unit).magnitude), 6)


class Api:
    def __init__(self, annex: str = "eks") -> None:
        self.annex_code = annex

    # --- Allmänt -------------------------------------------------------------
    def info(self) -> dict[str, Any]:
        from .. import __version__

        annex = national.load(self.annex_code)
        return {
            "version": __version__,
            "annex": annex.name,
            "annex_source": annex.source,
            "annexes": national.available(),
        }

    # --- Material ------------------------------------------------------------
    def concrete_classes(self) -> list[str]:
        return list(STRENGTH_CLASSES)

    def concrete(self, name: str) -> dict[str, Any]:
        c = concrete(name, national.load(self.annex_code))
        return {
            "name": c.name,
            "properties": {
                "fck": _q(c.fck, "MPa"),
                "fck_cube": _q(c.fck_cube, "MPa"),
                "fcm": _q(c.fcm, "MPa"),
                "fctm": _q(c.fctm, "MPa"),
                "fctk_005": _q(c.fctk_005, "MPa"),
                "fctk_095": _q(c.fctk_095, "MPa"),
                "Ecm": _q(c.Ecm, "GPa"),
                "fcd": _q(c.fcd, "MPa"),
                "eps_c2": c.eps_c2,
                "eps_cu2": c.eps_cu2,
                "n": c.n,
                "gamma_c": c.gamma_c,
                "alpha_cc": c.alpha_cc,
            },
            "curve": parabola_rectangle_curve(c),
            "log": c.log.to_dict(),
        }

    def reinforcement_grades(self) -> list[str]:
        return list(GRADES)

    def reinforcement(self, name: str = "B500B") -> dict[str, Any]:
        r = reinforcement(name, national.load(self.annex_code))
        return {
            "name": r.name,
            "properties": {
                "fyk": _q(r.fyk, "MPa"),
                "fyd": _q(r.fyd, "MPa"),
                "Es": _q(r.Es, "GPa"),
                "eps_yd": r.eps_yd,
                "eps_uk": r.eps_uk,
                "k": r.k,
                "ductility": r.ductility,
                "gamma_s": r.gamma_s,
            },
            "log": r.log.to_dict(),
        }

    # --- Analys --------------------------------------------------------------
    def simply_supported(self, span_m: float, q_kN_per_m: float) -> dict[str, Any]:
        res = simply_supported_udl(Q_(span_m, "m"), Q_(q_kN_per_m, "kN/m"))
        return {
            "M_max": _q(res.M_max, "kN*m"),
            "V_max": _q(res.V_max, "kN"),
            "log": res.log.to_dict(),
        }
