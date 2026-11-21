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
from ..core.materials.durability import EXPOSURE_CLASSES, SERVICE_LIVES, concrete_cover
from ..core.materials.reinforcement import GRADES, reinforcement
from ..core.materials.time_effects import (
    CEMENT_CLASSES,
    DRYING,
    creep_coefficient,
    creep_curve,
    nominal_thickness_rect,
    shrinkage_curve,
    shrinkage_strain,
    strength_at_age,
    strength_curve,
)
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

    def material_options(self) -> dict[str, Any]:
        """Val i materialsteget: cementklasser, uttorkning, exponeringsklasser m.m."""
        annex = national.load(self.annex_code)
        return {
            "cements": {k: v["name"] for k, v in CEMENT_CLASSES.items()},
            "drying": DRYING,
            "exposure": EXPOSURE_CLASSES,
            "lives": SERVICE_LIVES,
            "binders": annex.get("cover.binders"),
        }

    def concrete_long_term(
        self,
        name: str,
        cement: str = "N",
        rh_percent: float = 50,
        b_mm: float = 300,
        h_mm: float = 500,
        drying: str = "all",
        t0_days: float = 28,
        ts_days: float = 7,
    ) -> dict[str, Any]:
        """Hållfasthet över tid, kryptal och krympning för balkens tvärsnitt."""
        c = concrete(name, national.load(self.annex_code))
        nt = nominal_thickness_rect(Q_(b_mm, "mm"), Q_(h_mm, "mm"), drying)
        st = strength_at_age(c, Q_(t0_days, "day"), cement)
        cr = creep_coefficient(c, nt.h0, rh_percent, Q_(t0_days, "day"), cement)
        sh = shrinkage_strain(c, nt.h0, rh_percent, cement, ts=Q_(ts_days, "day"))
        return {
            "h0": _q(nt.h0, "mm"),
            "strength_at_t0": {
                "t": t0_days,
                "fcm": _q(st.fcm_t, "MPa"),
                "fck": _q(st.fck_t, "MPa"),
                "fctm": _q(st.fctm_t, "MPa"),
                "Ecm": _q(st.Ecm_t, "GPa"),
                "beta_cc": st.beta_cc,
            },
            "strength_curve": strength_curve(c, cement),
            "creep": {
                "phi_inf": cr.phi,
                "phi_RH": cr.phi_RH,
                "beta_fcm": cr.beta_fcm,
                "beta_t0": cr.beta_t0,
                "beta_H": cr.beta_H,
                "Ec_eff": _q(cr.Ec_eff, "GPa"),
                "curve": creep_curve(cr),
            },
            "shrinkage": {
                "eps_cs_inf": sh.eps_cs,
                "eps_cd_inf": sh.eps_cd,
                "eps_ca_inf": sh.eps_ca,
                "kh": sh.kh,
                "beta_RH": sh.beta_RH,
                "curve": shrinkage_curve(sh),
            },
            "logs": [nt.log.to_dict(), st.log.to_dict(), cr.log.to_dict(), sh.log.to_dict()],
        }

    def concrete_cover(
        self,
        exposure: list[str],
        life: str = "L50",
        binder: str = "pc80",
        vct: float | None = None,
        bar_mm: float = 10,
    ) -> dict[str, Any]:
        """Högsta vct och täckande betongskikt för valda exponeringsklasser."""
        cv = concrete_cover(
            exposure, Q_(bar_mm, "mm"), life, binder, vct, national.load(self.annex_code)
        )
        return {
            "vct_max": cv.vct_max if cv.vct_max < 1.5 else None,
            "vct_ok": cv.vct_ok,
            "cmin_dur": _q(cv.cmin_dur, "mm"),
            "cmin_b": _q(cv.cmin_b, "mm"),
            "cmin": _q(cv.cmin, "mm"),
            "delta_c_dev": _q(cv.delta_c_dev, "mm"),
            "cnom": _q(cv.cnom, "mm"),
            "warnings": cv.warnings,
            "log": cv.log.to_dict(),
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
