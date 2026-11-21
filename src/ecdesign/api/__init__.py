"""Tunt lager mellan kärnan och gränssnittet.

Metoderna i :class:`Api` anropas från JavaScript via pywebview
(``window.pywebview.api.<metod>(...)``). De tar enkla värden (tal i fasta
enheter, strängar) och returnerar JSON-vänliga dict:ar inklusive beräkningsloggen.
Här finns ingen beräkningslogik, bara översättning.
"""

from __future__ import annotations

from typing import Any

from ..core import national
from ..core.analysis.beam import BeamSystem, SupportType, gross_stiffness
from ..core.analysis.load_effects import DesignEffects, Extreme, design_effects
from ..core.analysis.simply_supported import simply_supported_udl
from ..core.calclog import CalcLog
from ..core.loads import (
    GROUPS,
    SAFETY_CLASSES,
    DistributedLoad,
    LoadCase,
    LoadKind,
    PointLoad,
    generate_combinations,
    resolve_cases,
)
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

    # --- Laster --------------------------------------------------------------
    def load_options(self) -> dict[str, Any]:
        """Val i laststeget: säkerhetsklasser, ψ-kategorier och förslag på nyttig last."""
        annex = national.load(self.annex_code)
        imposed = annex.get("imposed")
        return {
            "safety_classes": {
                str(k): {"label": v, "gamma_d": annex.get(f"safety_class.{k}")}
                for k, v in SAFETY_CLASSES.items()
            },
            "psi": {
                k: {
                    "name": v["name"],
                    "psi0": v["psi0"],
                    "psi1": v["psi1"],
                    "psi2": v["psi2"],
                    "sk_min": v.get("sk_min"),
                }
                for k, v in annex.get("psi").items()
            },
            "imposed": {k: v for k, v in imposed.items() if isinstance(v, dict)},
            "imposed_note": imposed.get("note", ""),
            "methods": annex.get("combination.uls.methods"),
            "groups": GROUPS,
        }

    def loads(
        self,
        span_m: float,
        b_mm: float,
        h_mm: float,
        width_m: float,
        safety_class: int,
        cases: list[dict[str, Any]],
        method: str | None = None,
        system: dict[str, Any] | None = None,
        concrete_class: str | None = "C30/37",
        pattern: bool | None = None,
    ) -> dict[str, Any]:
        """Lastfall, lastkombinationer, snittkrafter och nedböjning för balken.

        ``cases``: lista med ``{name, kind, category?, psi?, self_weight?, snow?: {sk, mu},
        loads: [{type: "udl" | "partial" | "point", value, unit: "kN/m" | "kN/m2" | "kN",
        a_m?, b_m?}]}``. Lägen mäts från balkens vänstra ände.
        ``system``: ``{spans_m: [...], supports: ["pinned" | "fixed" | "free", ...]}``.
        Saknas det är balken fritt upplagd med spännvidden ``span_m``.
        ``concrete_class``: ger E_cm för nedböjningen (osprucket tvärsnitt). ``None``: ingen
        nedböjning. ``pattern``: mönsterbelastning; standard enligt det nationella datasetet.
        """
        annex = national.load(self.annex_code)
        if system:
            beam = BeamSystem(
                [Q_(float(x), "m") for x in system["spans_m"]],
                [SupportType(x) for x in system["supports"]],
            )
        else:
            beam = BeamSystem.simply_supported(Q_(span_m, "m"))
        if pattern is None:
            pattern = annex.get("analysis.pattern_loading") != "none"
        b, h = Q_(b_mm, "mm"), Q_(h_mm, "mm")
        res = resolve_cases(
            [_case_from_dict(c) for c in cases],
            beam.length,
            width=Q_(width_m, "m"),
            b=b,
            h=h,
            annex=annex,
        )
        combos = generate_combinations(res.cases, int(safety_class), annex, method)
        EI = None
        stiff_log = CalcLog(title="Böjstyvhet för nedböjning")
        if concrete_class:
            Ecm = concrete(concrete_class, annex).Ecm
            EI = gross_stiffness(Ecm, b, h, stiff_log)
        de = design_effects(beam, res.cases, combos, EI=EI, pattern=bool(pattern))
        qd = {
            s.symbol: s.result
            for s in combos.log
            if s.symbol.startswith("q_{d,") and isinstance(s.result, Q_)
        }
        psi_names = {k: v["name"] for k, v in annex.get("psi").items()}
        out_cases = []
        for c in res.cases:
            out_cases.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "kind": c.kind.value,
                    "category": c.category,
                    "category_name": psi_names.get(c.category or "", None),
                    "psi": list(combos.psi[c.id]) if c.id in combos.psi else None,
                    "loads": [_load_to_dict(ld) for ld in c.loads],
                }
            )
        labels = [beam.label(k) for k in range(len(beam.supports))]
        out_combos = []
        for e in de.effects:
            co = e.combination
            q = qd.get(rf"q_{{d,\mathrm{{{co.id}}}}}")
            gov = de.governing.get(co.group, {})
            out_combos.append(
                {
                    "id": co.id,
                    "name": co.name,
                    "type": co.type.value,
                    "type_label": co.type.label,
                    "group": co.group,
                    "leading": co.leading,
                    "latex": co.latex(),
                    "latex_numeric": co.latex_numeric(),
                    "factors": {t.case_id: round(t.unfav, 6) for t in co.terms},
                    "q_d": _q(q, "kN/m") if q is not None and beam.n_spans == 1 else None,
                    "M_max": _q(e.M_max, "kN*m"),
                    "x_M_max": _q(e.x_M_max, "m"),
                    "M_min": _q(e.M_min, "kN*m"),
                    "x_M_min": _q(e.x_M_min, "m"),
                    "V_abs": _q(e.V_abs, "kN"),
                    "x_V": _q(e.x_V, "m"),
                    "R_A": _q(e.R_A, "kN"),
                    "R_B": _q(e.R_B, "kN"),
                    "reactions": [
                        {"support": labels[k], "max": _q(r[0], "kN"), "min": _q(r[1], "kN")}
                        for k, r in enumerate(e.reactions)
                        if beam.supports[k] is not SupportType.FREE
                    ],
                    "w_max": _q(e.w_max, "mm") if e.w_max is not None else None,
                    "x_w": _q(e.x_w, "m") if e.x_w is not None else None,
                    "loaded_spans": {k: [j + 1 for j in v] for k, v in e.loaded_spans_M.items()},
                    "governs_M": gov.get("M") == co.id,
                    "governs_V": gov.get("V") == co.id,
                }
            )
        design = {}
        for group, gov in de.governing.items():
            eM = de.get(gov["M"])
            eV = de.get(gov["V"])
            eP = de.get(gov["M_pos"])
            eN = de.get(gov["M_neg"])
            eW = de.get(gov["w"]) if "w" in gov else None
            design[group] = {
                "label": GROUPS[group],
                "M": _q(eM.M_abs, "kN*m"),
                "x_M": _q(eM.x_M_abs, "m"),
                "V": _q(eV.V_abs, "kN"),
                "x_V": _q(eV.x_V, "m"),
                "M_pos": _q(eP.M_max, "kN*m"),
                "x_M_pos": _q(eP.x_M_max, "m"),
                "M_neg": _q(eN.M_min, "kN*m"),
                "x_M_neg": _q(eN.x_M_min, "m"),
                "w": _q(eW.w_max, "mm") if eW else None,
                "x_w": _q(eW.x_w, "m") if eW else None,
                "combination_M": eM.combination.id,
                "combination_M_name": eM.combination.name,
                "combination_V": eV.combination.id,
                "combination_V_name": eV.combination.name,
                "combination_M_pos_name": eP.combination.name,
                "combination_M_neg_name": eN.combination.name,
                "combination_w_name": eW.combination.name if eW else None,
                **_per_span(de, beam, group, labels),
            }
        r6 = lambda vals: [round(v, 4) for v in vals]  # noqa: E731
        case_diagrams = {}
        for cid in de.case_M:
            case_diagrams[cid] = {"M": r6(de.case_M[cid]), "V": r6(de.case_V[cid])}
            if de.case_w:
                case_diagrams[cid]["w"] = r6(de.case_w[cid])
        xs_sup = beam.x_nodes()
        return {
            "gamma_d": combos.gamma_d,
            "system": {
                "description": beam.description,
                "length": _q(beam.length, "m"),
                "spans": [_q(L, "m") for L in beam.spans],
                "supports": [
                    {"label": labels[k], "type": s.value, "type_label": s.label, "x": xs_sup[k]}
                    for k, s in enumerate(beam.supports)
                ],
                "pattern": de.pattern,
                "EI": _q(EI, "kN*m^2") if EI is not None else None,
            },
            "cases": out_cases,
            "combinations": out_combos,
            "design": design,
            "diagrams": {
                "x": r6(de.x),
                "cases": case_diagrams,
                **{g: {k: r6(v) for k, v in de.envelope(g).items()} for g in de.governing},
            },
            "warnings": [*res.warnings, *combos.warnings, *de.warnings],
            "logs": [
                res.log.to_dict(),
                combos.log.to_dict(),
                *([stiff_log.to_dict()] if len(stiff_log) else []),
                de.log.to_dict(),
            ],
        }


def _extreme(e: Extreme | None, unit: str) -> dict[str, Any] | None:
    if e is None:
        return None
    return {
        "value": _q(e.value, unit),
        "x": _q(e.x, "m"),
        "loaded_spans": {k: [j + 1 for j in v] for k, v in e.loaded_spans.items()},
    }


def _per_span(de: DesignEffects, beam: BeamSystem, group: str, labels: list[str]) -> dict:
    """Dimensionerande värden fack för fack och stöd för stöd i en grupp."""
    members = [e for e in de.effects if e.combination.group == group]
    spans = []
    for j, L in enumerate(beam.spans):
        bestM = max(members, key=lambda e: e.spans[j].M_max.value.magnitude)
        row: dict[str, Any] = {
            "index": j + 1,
            "length": _q(L, "m"),
            "cantilever": beam.is_cantilever_span(j),
            "M": _extreme(bestM.spans[j].M_max, "kN*m"),
            "combination_M": bestM.combination.name,
        }
        if members[0].spans[j].w_max is not None:
            bestW = max(members, key=lambda e: e.spans[j].w_max.value.magnitude)
            row["w"] = _extreme(bestW.spans[j].w_max, "mm")
            row["combination_w"] = bestW.combination.name
            w = bestW.spans[j].w_max.value.magnitude
            row["L_over_w"] = round(L.to("mm").magnitude / w) if w > 1e-6 else None
        spans.append(row)
    supports = []
    for k, s in enumerate(beam.supports):
        if s is SupportType.FREE:
            continue
        bestM = min(members, key=lambda e: e.support_M[k].magnitude)
        bestR = max(members, key=lambda e: e.reactions[k][0].magnitude)
        minR = min(members, key=lambda e: e.reactions[k][1].magnitude)
        supports.append(
            {
                "label": labels[k],
                "type": s.value,
                "M": _q(bestM.support_M[k], "kN*m"),
                "combination_M": bestM.combination.name,
                "R_max": _q(bestR.reactions[k][0], "kN"),
                "combination_R": bestR.combination.name,
                "R_min": _q(minR.reactions[k][1], "kN"),
            }
        )
    return {"spans": spans, "supports": supports}


def _case_from_dict(d: dict[str, Any]) -> LoadCase:
    loads: list = []
    for ld in d.get("loads", []):
        kind = ld.get("type", "udl")
        if kind == "point":
            loads.append(PointLoad(Q_(float(ld["value"]), "kN"), Q_(float(ld.get("a_m", 0)), "m")))
            continue
        unit = "kN/m^2" if ld.get("unit") == "kN/m2" else "kN/m"
        q = Q_(float(ld["value"]), unit)
        if kind == "partial":
            loads.append(
                DistributedLoad(q, Q_(float(ld.get("a_m", 0)), "m"), Q_(float(ld["b_m"]), "m"))
            )
        else:
            loads.append(DistributedLoad(q))
    snow = d.get("snow")
    psi = d.get("psi")
    return LoadCase(
        name=d.get("name") or "Lastfall",
        kind=LoadKind(d.get("kind", "permanent")),
        category=d.get("category") or None,
        loads=loads,
        id=d.get("id", "") if d.get("id", "").isalnum() else "",
        psi=tuple(psi) if psi else None,
        self_weight=bool(d.get("self_weight")),
        snow_sk=Q_(float(snow["sk"]), "kN/m^2") if snow else None,
        snow_mu=float(snow.get("mu", 0.8)) if snow else 0.8,
    )


def _load_to_dict(ld: Any) -> dict[str, Any]:
    if isinstance(ld, PointLoad):
        return {"type": "point", "P": _q(ld.P, "kN"), "a": _q(ld.a, "m"), "text": ld.description}
    return {
        "type": "udl" if ld.full_span else "partial",
        "q": _q(ld.q, "kN/m"),
        "a": _q(ld.a, "m") if ld.a is not None else None,
        "b": _q(ld.b, "m") if ld.b is not None else None,
        "text": ld.description,
    }
