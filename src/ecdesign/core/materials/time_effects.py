"""Tidsberoende egenskaper hos betong: hållfasthet över tid, krypning och krympning.

Ref: EN 1992-1-1 3.1.2(6) (hållfasthetstillväxt), 3.1.3(3) (E-modul över tid),
3.1.4 (krypning och krympning) och bilaga B (B.1 kryptal, B.2 uttorkningskrympning).

Förutsättningar som gäller hela modulen (EN 1992-1-1 3.1.4(2) och bilaga B):

* medeltemperatur 20 °C (temperaturjustering enligt B.10 görs inte än),
* relativ fuktighet RH mellan 40 och 100 %,
* betongspänning vid pålastning högst 0,45·f_ck(t_0), annars icke-linjär krypning
  enligt 3.1.4(4).

Tider anges som pint-storheter i dygn (``Q_(28, "day")``). Töjningar returneras i ‰
och kryptal är dimensionslösa tal.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field

from ..calclog import CalcLog
from ..units import Q_
from .concrete import Concrete

REF_B1 = "EN 1992-1-1 bilaga B.1"
REF_B2 = "EN 1992-1-1 bilaga B.2"

# Cementklasser enligt EN 1992-1-1 3.1.2(6) och bilaga B. Värdena är en del av
# normens modell (inte nationella val) och står därför här i koden.
CEMENT_CLASSES: dict[str, dict[str, float | str]] = {
    "S": {
        "name": "Klass S, långsamt hårdnande (CEM III)",
        "s": 0.38,  # 3.1.2(6), ekv. (3.2)
        "alpha": -1,  # B.9
        "alpha_ds1": 3,  # B.11
        "alpha_ds2": 0.13,  # B.11
    },
    "N": {
        "name": "Klass N, normalt hårdnande (CEM 32,5 R, CEM 42,5 N)",
        "s": 0.25,
        "alpha": 0,
        "alpha_ds1": 4,
        "alpha_ds2": 0.12,
    },
    "R": {
        "name": "Klass R, snabbt hårdnande (CEM 42,5 R, CEM 52,5 N/R)",
        "s": 0.20,
        "alpha": 1,
        "alpha_ds1": 6,
        "alpha_ds2": 0.11,
    },
}

# EN 1992-1-1 tabell 3.3: k_h som funktion av h_0 (mm). Linjär interpolation.
KH_TABLE: list[tuple[float, float]] = [(100, 1.0), (200, 0.85), (300, 0.75), (500, 0.70)]

FCM0 = 10.0  # MPa, B.11
RH0 = 100.0  # %, B.12


def _cement(cement: str) -> dict[str, float | str]:
    if cement not in CEMENT_CLASSES:
        raise ValueError(f"Okänd cementklass {cement!r}. Välj S, N eller R.")
    return CEMENT_CLASSES[cement]


def _days(t: Q_) -> float:
    return float(t.to("day").magnitude)


def _check_rh(rh: float) -> None:
    if not 40 <= rh <= 100:
        raise ValueError(
            f"Relativ fuktighet {rh} % ligger utanför 40–100 %, där modellen i "
            "EN 1992-1-1 3.1.4 gäller."
        )


# --- Hållfasthet över tid ------------------------------------------------------


def beta_cc(t_days: float, s: float) -> float:
    """β_cc(t) = exp(s·(1 − √(28/t))). Ref: EN 1992-1-1 3.1.2(6), ekv. (3.2)."""
    return math.exp(s * (1 - math.sqrt(28 / t_days)))


@dataclass
class StrengthAtAge:
    """Hållfasthet och E-modul vid betongåldern ``t``."""

    t: Q_
    cement: str
    s: float
    beta_cc: float
    fcm_t: Q_
    fck_t: Q_
    fctm_t: Q_
    Ecm_t: Q_
    log: CalcLog = field(repr=False)


def strength_at_age(c: Concrete, t: Q_, cement: str = "N") -> StrengthAtAge:
    """Tryck- och draghållfasthet samt E-modul vid åldern ``t`` (dygn).

    Ref: EN 1992-1-1 3.1.2(5)–(9), ekv. (3.1)–(3.4), och 3.1.3(3), ekv. (3.5).
    Gäller vid medeltemperatur 20 °C och härdning enligt EN 12390.
    """
    td = _days(t)
    if td <= 0:
        raise ValueError("Betongens ålder måste vara större än 0 dygn.")
    cem = _cement(cement)
    log = CalcLog(title=f"Hållfasthet vid {td:g} dygn ({c.name})")
    s = log.step(
        symbol="s",
        description=f"Koefficient för cementtyp, {cem['name']}",
        formula=_tex_num(float(cem["s"])),
        result=float(cem["s"]),
        ref="EN 1992-1-1 3.1.2(6)",
    )
    bcc = log.step(
        symbol=r"\beta_{cc}(t)",
        description="Hållfasthetstillväxt jämfört med 28 dygn",
        formula=r"\exp\left(s \left(1 - \sqrt{\frac{28}{t}}\right)\right)",
        values={"s": s, "t": td},
        result=beta_cc(td, s),
        ref="EN 1992-1-1 3.1.2(6), ekv. (3.2)",
    )
    fcm_t = log.step(
        symbol="f_{cm}(t)",
        description="Medeltryckhållfasthet vid åldern t",
        formula=r"\beta_{cc}(t) \cdot f_{cm}",
        values={r"\beta_{cc}(t)": bcc, "f_{cm}": c.fcm},
        result=bcc * c.fcm,
        ref="EN 1992-1-1 3.1.2(6), ekv. (3.1)",
    )
    if td < 28:
        fck_t = log.step(
            symbol="f_{ck}(t)",
            description="Karakteristisk tryckhållfasthet före 28 dygn",
            formula=r"f_{cm}(t) - 8",
            values={"f_{cm}(t)": fcm_t},
            result=fcm_t - Q_(8, "MPa"),
            ref="EN 1992-1-1 3.1.2(5)",
        )
        alpha = 1.0
    else:
        fck_t = log.step(
            symbol="f_{ck}(t)",
            description="Karakteristisk tryckhållfasthet från 28 dygn (ingen tillväxt räknas)",
            formula="f_{ck}",
            values={"f_{ck}": c.fck},
            result=c.fck,
            ref="EN 1992-1-1 3.1.2(5)",
        )
        alpha = 2 / 3
    fctm_t = log.step(
        symbol="f_{ctm}(t)",
        description=("Medeldraghållfasthet vid åldern t, α = 1 före 28 dygn och 2/3 efter"),
        formula=r"\beta_{cc}(t)^{\alpha} \cdot f_{ctm}",
        values={r"\beta_{cc}(t)": bcc, r"\alpha": alpha, "f_{ctm}": c.fctm},
        result=bcc**alpha * c.fctm,
        ref="EN 1992-1-1 3.1.2(9), ekv. (3.4)",
    )
    Ecm_t = log.step(
        symbol="E_{cm}(t)",
        description="E-modul vid åldern t",
        formula=r"\left(\frac{f_{cm}(t)}{f_{cm}}\right)^{0{,}3} \cdot E_{cm}",
        values={"f_{cm}(t)": fcm_t, "f_{cm}": c.fcm, "E_{cm}": c.Ecm},
        result=float((fcm_t / c.fcm).to("").magnitude) ** 0.3 * c.Ecm,
        ref="EN 1992-1-1 3.1.3(3), ekv. (3.5)",
    )
    return StrengthAtAge(
        t=t,
        cement=cement,
        s=s,
        beta_cc=bcc,
        fcm_t=fcm_t,
        fck_t=fck_t,
        fctm_t=fctm_t,
        Ecm_t=Ecm_t,
        log=log,
    )


def strength_curve(
    c: Concrete, cement: str = "N", days: Iterable[float] | None = None
) -> list[dict[str, float]]:
    """Punkter för att rita hållfasthet över tid: t (dygn), f_cm(t), f_ck(t), f_ctm(t) i MPa
    och E_cm(t) i GPa. Samma formler som :func:`strength_at_age`, men utan logg."""
    s = float(_cement(cement)["s"])
    fcm = float(c.fcm.to("MPa").magnitude)
    fck = float(c.fck.to("MPa").magnitude)
    fctm = float(c.fctm.to("MPa").magnitude)
    Ecm = float(c.Ecm.to("GPa").magnitude)
    out = []
    for td in days or log_days(1, 365, 40):
        b = beta_cc(td, s)
        fcm_t = b * fcm
        out.append(
            {
                "t": td,
                "fcm": fcm_t,
                "fck": fcm_t - 8 if td < 28 else fck,
                "fctm": b ** (1 if td < 28 else 2 / 3) * fctm,
                "Ecm": b**0.3 * Ecm,
            }
        )
    return out


# --- Nominell tjocklek ----------------------------------------------------------


@dataclass
class NominalThickness:
    Ac: Q_
    u: Q_
    h0: Q_
    log: CalcLog = field(repr=False)


DRYING = {
    "all": "Uttorkning från alla sidor",
    "not_top": "Ovansidan skyddad (t.ex. bjälklag ovanpå), uttorkning från tre sidor",
}


def nominal_thickness_rect(b: Q_, h: Q_, drying: str = "all") -> NominalThickness:
    """Nominell tjocklek h_0 = 2·A_c/u för ett rektangulärt tvärsnitt.

    ``drying`` anger vilka sidor som torkar ut: ``"all"`` (u = 2b + 2h) eller
    ``"not_top"`` (u = b + 2h, ovansidan skyddad).

    Ref: EN 1992-1-1 3.1.4(5) (definition av h_0) och bilaga B.1(1).
    """
    if drying not in DRYING:
        raise ValueError(f"Okänd uttorkning {drying!r}. Välj {', '.join(DRYING)}.")
    log = CalcLog(title="Nominell tjocklek")
    Ac = log.step(
        symbol="A_c",
        description="Betongens tvärsnittsarea",
        formula=r"b \cdot h",
        values={"b": b.to("mm"), "h": h.to("mm")},
        result=(b * h).to("mm**2"),
        ref="EN 1992-1-1 3.1.4(5)",
    )
    if drying == "all":
        u = log.step(
            symbol="u",
            description="Omkrets som torkar ut (alla sidor)",
            formula=r"2 b + 2 h",
            values={"b": b.to("mm"), "h": h.to("mm")},
            result=(2 * b + 2 * h).to("mm"),
            ref="EN 1992-1-1 3.1.4(5)",
        )
    else:
        u = log.step(
            symbol="u",
            description="Omkrets som torkar ut (ovansidan skyddad)",
            formula=r"b + 2 h",
            values={"b": b.to("mm"), "h": h.to("mm")},
            result=(b + 2 * h).to("mm"),
            ref="EN 1992-1-1 3.1.4(5)",
        )
    h0 = log.step(
        symbol="h_0",
        description="Nominell tjocklek: tjockleken hos en vägg som torkar från båda sidor",
        formula=r"\frac{2 A_c}{u}",
        values={"A_c": Ac, "u": u},
        result=(2 * Ac / u).to("mm"),
        ref="EN 1992-1-1 3.1.4(5)",
    )
    return NominalThickness(Ac=Ac, u=u, h0=h0, log=log)


# --- Krypning --------------------------------------------------------------------


def _phi_rh(rh: float, h0: float, fcm: float) -> float:
    """Ekv. (B.3a)/(B.3b)."""
    base = (1 - rh / 100) / (0.1 * h0 ** (1 / 3))
    if fcm <= 35:
        return 1 + base
    a1 = (35 / fcm) ** 0.7
    a2 = (35 / fcm) ** 0.2
    return (1 + base * a1) * a2


def _t0_adjusted(t0: float, alpha: float) -> float:
    """Ekv. (B.9), utan temperaturjustering (t_0,T = t_0)."""
    return max(t0 * (9 / (2 + t0**1.2) + 1) ** alpha, 0.5)


def _beta_h(rh: float, h0: float, fcm: float) -> float:
    """Ekv. (B.8a)/(B.8b)."""
    base = 1.5 * (1 + (0.012 * rh) ** 18) * h0
    if fcm <= 35:
        return min(base + 250, 1500)
    a3 = (35 / fcm) ** 0.5
    return min(base + 250 * a3, 1500 * a3)


def _beta_c(t: float, t0: float, beta_h: float) -> float:
    """Ekv. (B.7)."""
    if t <= t0:
        return 0.0
    return ((t - t0) / (beta_h + t - t0)) ** 0.3


@dataclass
class Creep:
    """Kryptal enligt bilaga B.1. ``phi`` är φ(t, t_0), eller φ(∞, t_0) om ``t`` saknas."""

    h0: Q_
    rh: float
    """Relativ fuktighet (%)."""
    t0: Q_
    t: Q_ | None
    cement: str
    phi_RH: float
    beta_fcm: float
    t0_adj: Q_
    beta_t0: float
    phi_0: float
    beta_H: float
    beta_c: float
    phi: float
    Ec_eff: Q_
    log: CalcLog = field(repr=False)


def creep_coefficient(
    c: Concrete,
    h0: Q_,
    rh: float,
    t0: Q_,
    cement: str = "N",
    t: Q_ | None = None,
) -> Creep:
    """Kryptal φ(t, t_0) för betongen ``c``. Utan ``t`` räknas slutvärdet φ(∞, t_0).

    ``rh`` är omgivningens relativa fuktighet i %, ``h0`` nominell tjocklek,
    ``t0`` ålder vid pålastning och ``cement`` cementklass S, N eller R.

    Ref: EN 1992-1-1 3.1.4(2) och bilaga B.1, ekv. (B.1)–(B.9). Effektiv E-modul
    enligt 7.4.3(5), ekv. (7.20).
    """
    _check_rh(rh)
    cem = _cement(cement)
    h0_mm = float(h0.to("mm").magnitude)
    t0_d = _days(t0)
    if t0_d <= 0:
        raise ValueError("Åldern vid pålastning t₀ måste vara större än 0 dygn.")
    fcm = float(c.fcm.to("MPa").magnitude)
    title = "Kryptal φ(∞, t₀)" if t is None else f"Kryptal φ({_days(t):g}, t₀)"
    log = CalcLog(title=f"{title}, {c.name}")

    if fcm <= 35:
        phi_RH = log.step(
            symbol=r"\varphi_{RH}",
            description="Inverkan av relativ fuktighet (f_cm ≤ 35 MPa)",
            formula=r"1 + \frac{1 - RH/100}{0{,}1 \cdot \sqrt[3]{h_0}}",
            values={"RH": rh, "h_0": h0_mm},
            result=_phi_rh(rh, h0_mm, fcm),
            ref=f"{REF_B1}, ekv. (B.3a)",
        )
    else:
        a1 = log.step(
            symbol=r"\alpha_1",
            description="Inverkan av betongens hållfasthet",
            formula=r"\left(\frac{35}{f_{cm}}\right)^{0{,}7}",
            values={"f_{cm}": fcm},
            result=(35 / fcm) ** 0.7,
            ref=f"{REF_B1}, ekv. (B.8c)",
        )
        a2 = log.step(
            symbol=r"\alpha_2",
            description="Inverkan av betongens hållfasthet",
            formula=r"\left(\frac{35}{f_{cm}}\right)^{0{,}2}",
            values={"f_{cm}": fcm},
            result=(35 / fcm) ** 0.2,
            ref=f"{REF_B1}, ekv. (B.8c)",
        )
        phi_RH = log.step(
            symbol=r"\varphi_{RH}",
            description="Inverkan av relativ fuktighet (f_cm > 35 MPa)",
            formula=(
                r"\left[1 + \frac{1 - RH/100}{0{,}1 \cdot \sqrt[3]{h_0}} \cdot \alpha_1\right]"
                r" \cdot \alpha_2"
            ),
            values={"RH": rh, "h_0": h0_mm, r"\alpha_1": a1, r"\alpha_2": a2},
            result=_phi_rh(rh, h0_mm, fcm),
            ref=f"{REF_B1}, ekv. (B.3b)",
        )
    beta_fcm = log.step(
        symbol=r"\beta(f_{cm})",
        description="Inverkan av betongens hållfasthet, f_cm i MPa",
        formula=r"\frac{16{,}8}{\sqrt{f_{cm}}}",
        values={"f_{cm}": fcm},
        result=16.8 / math.sqrt(fcm),
        ref=f"{REF_B1}, ekv. (B.4)",
    )
    alpha = float(cem["alpha"])
    t0_adj = log.step(
        symbol="t_{0,cem}",
        description=(
            f"Ålder vid pålastning justerad för cementtyp ({cement}: α = {alpha:g}), "
            "minst 0,5 dygn. Temperatur 20 °C antas."
        ),
        formula=r"t_{0,T} \cdot \left(\frac{9}{2 + t_{0,T}^{1{,}2}} + 1\right)^{\alpha}",
        values={"t_{0,T}": t0_d, r"\alpha": alpha},
        result=Q_(_t0_adjusted(t0_d, alpha), "day"),
        ref=f"{REF_B1}, ekv. (B.9)",
    )
    t0a = _days(t0_adj)
    beta_t0 = log.step(
        symbol=r"\beta(t_0)",
        description="Inverkan av betongens ålder vid pålastning",
        formula=r"\frac{1}{0{,}1 + t_{0,cem}^{0{,}20}}",
        values={"t_{0,cem}": t0a},
        result=1 / (0.1 + t0a**0.20),
        ref=f"{REF_B1}, ekv. (B.5)",
    )
    phi_0 = log.step(
        symbol=r"\varphi_0",
        description="Grundvärde för kryptalet (= slutvärdet φ(∞, t₀))",
        formula=r"\varphi_{RH} \cdot \beta(f_{cm}) \cdot \beta(t_0)",
        values={r"\varphi_{RH}": phi_RH, r"\beta(f_{cm})": beta_fcm, r"\beta(t_0)": beta_t0},
        result=phi_RH * beta_fcm * beta_t0,
        ref=f"{REF_B1}, ekv. (B.2)",
    )
    if fcm <= 35:
        beta_H = log.step(
            symbol=r"\beta_H",
            description="Inverkan av fuktighet och tjocklek på förloppet (f_cm ≤ 35 MPa)",
            formula=(
                r"\min\left(1{,}5 \left[1 + (0{,}012 \cdot RH)^{18}\right] h_0"
                r" + 250;\ 1500\right)"
            ),
            values={"RH": rh, "h_0": h0_mm},
            result=_beta_h(rh, h0_mm, fcm),
            ref=f"{REF_B1}, ekv. (B.8a)",
        )
    else:
        a3 = log.step(
            symbol=r"\alpha_3",
            description="Inverkan av betongens hållfasthet",
            formula=r"\left(\frac{35}{f_{cm}}\right)^{0{,}5}",
            values={"f_{cm}": fcm},
            result=(35 / fcm) ** 0.5,
            ref=f"{REF_B1}, ekv. (B.8c)",
        )
        beta_H = log.step(
            symbol=r"\beta_H",
            description="Inverkan av fuktighet och tjocklek på förloppet (f_cm > 35 MPa)",
            formula=(
                r"\min\left(1{,}5 \left[1 + (0{,}012 \cdot RH)^{18}\right] h_0"
                r" + 250 \cdot \alpha_3;\ 1500 \cdot \alpha_3\right)"
            ),
            values={"RH": rh, "h_0": h0_mm, r"\alpha_3": a3},
            result=_beta_h(rh, h0_mm, fcm),
            ref=f"{REF_B1}, ekv. (B.8b)",
        )
    if t is None:
        bc = 1.0
        phi = log.step(
            symbol=r"\varphi(\infty, t_0)",
            description="Slutligt kryptal (β_c → 1 när t → ∞)",
            formula=r"\varphi_0",
            values={r"\varphi_0": phi_0},
            result=phi_0,
            substituted="",
            ref=f"{REF_B1}, ekv. (B.1)",
        )
    else:
        td = _days(t)
        bc = log.step(
            symbol=r"\beta_c(t, t_0)",
            description="Krypningens utveckling med tiden efter pålastning",
            formula=r"\left(\frac{t - t_0}{\beta_H + t - t_0}\right)^{0{,}3}",
            values={"t": td, "t_0": t0_d, r"\beta_H": beta_H},
            result=_beta_c(td, t0_d, beta_H),
            ref=f"{REF_B1}, ekv. (B.7)",
        )
        phi = log.step(
            symbol=r"\varphi(t, t_0)",
            description="Kryptal vid tiden t",
            formula=r"\varphi_0 \cdot \beta_c(t, t_0)",
            values={r"\varphi_0": phi_0, r"\beta_c(t, t_0)": bc},
            result=phi_0 * bc,
            ref=f"{REF_B1}, ekv. (B.1)",
        )
    phi_sym = r"\varphi(\infty, t_0)" if t is None else r"\varphi(t, t_0)"
    Ec_eff = log.step(
        symbol=r"E_{c,eff}",
        description="Effektiv E-modul för långtidslast (används vid nedböjning och sprickor)",
        formula=rf"\frac{{E_{{cm}}}}{{1 + {phi_sym}}}",
        values={"E_{cm}": c.Ecm, phi_sym: phi},
        result=c.Ecm / (1 + phi),
        ref="EN 1992-1-1 7.4.3(5), ekv. (7.20)",
    )
    return Creep(
        h0=h0,
        rh=rh,
        t0=t0,
        t=t,
        cement=cement,
        phi_RH=phi_RH,
        beta_fcm=beta_fcm,
        t0_adj=t0_adj,
        beta_t0=beta_t0,
        phi_0=phi_0,
        beta_H=beta_H,
        beta_c=bc,
        phi=phi,
        Ec_eff=Ec_eff,
        log=log,
    )


def creep_curve(cr: Creep, days: Iterable[float] | None = None) -> list[tuple[float, float]]:
    """Punkter (t i dygn, φ(t, t_0)) för en redan beräknad krypning."""
    t0 = _days(cr.t0)
    pts = days or [t0 + d for d in log_days(1, 365 * 70, 50)]
    return [(t, cr.phi_0 * _beta_c(t, t0, cr.beta_H)) for t in pts]


# --- Krympning -------------------------------------------------------------------


def beta_rh(rh: float) -> float:
    """β_RH = 1,55·[1 − (RH/RH_0)³]. Ref: bilaga B.2, ekv. (B.12)."""
    return 1.55 * (1 - (rh / RH0) ** 3)


def eps_cd0_basic(fcm: float, cement: str) -> float:
    """Grundvärde för uttorkningskrympning utan β_RH (‰), f_cm i MPa. Ref: ekv. (B.11)."""
    cem = _cement(cement)
    a1 = float(cem["alpha_ds1"])
    a2 = float(cem["alpha_ds2"])
    return 0.85 * (220 + 110 * a1) * math.exp(-a2 * fcm / FCM0) * 1e-3


def kh(h0_mm: float) -> float:
    """Koefficient k_h ur tabell 3.3, linjärt interpolerad. Ref: EN 1992-1-1 3.1.4(6)."""
    if h0_mm <= KH_TABLE[0][0]:
        return KH_TABLE[0][1]
    for (x0, y0), (x1, y1) in zip(KH_TABLE, KH_TABLE[1:], strict=False):
        if h0_mm <= x1:
            return y0 + (y1 - y0) * (h0_mm - x0) / (x1 - x0)
    return KH_TABLE[-1][1]


def _beta_ds(t: float, ts: float, h0: float) -> float:
    """Ekv. (3.10)."""
    if t <= ts:
        return 0.0
    return (t - ts) / ((t - ts) + 0.04 * math.sqrt(h0**3))


def _beta_as(t: float) -> float:
    """Ekv. (3.13)."""
    return 1 - math.exp(-0.2 * math.sqrt(t))


@dataclass
class Shrinkage:
    """Krympning enligt 3.1.4(6). Alla töjningar i ‰. Utan ``t`` gäller slutvärden."""

    h0: Q_
    rh: float
    """Relativ fuktighet (%)."""
    ts: Q_
    t: Q_ | None
    cement: str
    beta_RH: float
    eps_cd0: float
    """Grundvärde för uttorkningskrympning (‰)."""
    kh: float
    beta_ds: float
    eps_cd: float
    """Uttorkningskrympning (‰)."""
    eps_ca_inf: float
    """Slutlig autogen krympning (‰)."""
    beta_as: float
    eps_ca: float
    """Autogen krympning (‰)."""
    eps_cs: float
    """Total krympning (‰)."""
    log: CalcLog = field(repr=False)


def shrinkage_strain(
    c: Concrete,
    h0: Q_,
    rh: float,
    cement: str = "N",
    ts: Q_ | None = None,
    t: Q_ | None = None,
) -> Shrinkage:
    """Krympning ε_cs = ε_cd + ε_ca. Utan ``t`` räknas slutvärdet ε_cs(∞).

    ``rh`` i %, ``ts`` betongens ålder när uttorkningen börjar (normalt när
    härdningen slutar, standard 7 dygn).

    Ref: EN 1992-1-1 3.1.4(6), ekv. (3.8)–(3.13), tabell 3.3, och bilaga B.2,
    ekv. (B.11)–(B.12).
    """
    _check_rh(rh)
    cem = _cement(cement)
    ts = ts if ts is not None else Q_(7, "day")
    ts_d = _days(ts)
    h0_mm = float(h0.to("mm").magnitude)
    fcm = float(c.fcm.to("MPa").magnitude)
    fck = float(c.fck.to("MPa").magnitude)
    title = "Krympning ε_cs(∞)" if t is None else f"Krympning ε_cs({_days(t):g})"
    log = CalcLog(title=f"{title}, {c.name}")

    bRH = log.step(
        symbol=r"\beta_{RH}",
        description="Inverkan av relativ fuktighet, RH₀ = 100 %",
        formula=r"1{,}55 \left[1 - \left(\frac{RH}{RH_0}\right)^3\right]",
        values={"RH": rh, "RH_0": RH0},
        result=beta_rh(rh),
        ref=f"{REF_B2}, ekv. (B.12)",
    )
    a1 = float(cem["alpha_ds1"])
    a2 = float(cem["alpha_ds2"])
    eps_cd0 = log.step(
        symbol=r"\varepsilon_{cd,0}",
        description=(
            f"Grundvärde för uttorkningskrympning (‰), cementklass {cement}: "
            f"α_ds1 = {a1:g}, α_ds2 = {a2:g}, f_cm0 = 10 MPa"
        ),
        formula=(
            r"0{,}85 \left[(220 + 110 \cdot \alpha_{ds1}) \exp\left(-\alpha_{ds2}"
            r" \frac{f_{cm}}{f_{cm0}}\right)\right] \cdot 10^{-3} \cdot \beta_{RH}"
        ),
        values={
            r"\alpha_{ds1}": a1,
            r"\alpha_{ds2}": a2,
            "f_{cm}": fcm,
            "f_{cm0}": FCM0,
            r"\beta_{RH}": bRH,
        },
        result=eps_cd0_basic(fcm, cement) * bRH,
        ref=f"{REF_B2}, ekv. (B.11). Normen skriver 10⁻⁶ för töjning; här ‰.",
    )
    k_h = log.step(
        symbol="k_h",
        description="Inverkan av nominell tjocklek, interpolerat i tabell 3.3",
        formula=r"k_h(h_0)",
        values={"h_0": h0_mm},
        result=kh(h0_mm),
        ref="EN 1992-1-1 3.1.4(6), tabell 3.3",
    )
    eps_ca_inf = log.step(
        symbol=r"\varepsilon_{ca}(\infty)",
        description="Slutlig autogen krympning (‰)",
        formula=r"2{,}5 \cdot (f_{ck} - 10) \cdot 10^{-3}",
        values={"f_{ck}": fck},
        result=2.5 * (fck - 10) * 1e-3,
        ref="EN 1992-1-1 3.1.4(6), ekv. (3.12)",
    )
    if t is None:
        b_ds = 1.0
        b_as = 1.0
        eps_cd = log.step(
            symbol=r"\varepsilon_{cd}(\infty)",
            description="Slutlig uttorkningskrympning (‰), β_ds → 1",
            formula=r"k_h \cdot \varepsilon_{cd,0}",
            values={"k_h": k_h, r"\varepsilon_{cd,0}": eps_cd0},
            result=k_h * eps_cd0,
            ref="EN 1992-1-1 3.1.4(6), ekv. (3.9)",
        )
        eps_ca = eps_ca_inf
        eps_cs = log.step(
            symbol=r"\varepsilon_{cs}(\infty)",
            description="Slutlig total krympning (‰)",
            formula=r"\varepsilon_{cd}(\infty) + \varepsilon_{ca}(\infty)",
            values={r"\varepsilon_{cd}(\infty)": eps_cd, r"\varepsilon_{ca}(\infty)": eps_ca},
            result=eps_cd + eps_ca,
            ref="EN 1992-1-1 3.1.4(6), ekv. (3.8)",
        )
    else:
        td = _days(t)
        b_ds = log.step(
            symbol=r"\beta_{ds}(t, t_s)",
            description="Uttorkningskrympningens utveckling, h₀ i mm",
            formula=r"\frac{t - t_s}{(t - t_s) + 0{,}04 \sqrt{h_0^3}}",
            values={"t": td, "t_s": ts_d, "h_0": h0_mm},
            result=_beta_ds(td, ts_d, h0_mm),
            ref="EN 1992-1-1 3.1.4(6), ekv. (3.10)",
        )
        eps_cd = log.step(
            symbol=r"\varepsilon_{cd}(t)",
            description="Uttorkningskrympning vid tiden t (‰)",
            formula=r"\beta_{ds}(t, t_s) \cdot k_h \cdot \varepsilon_{cd,0}",
            values={r"\beta_{ds}(t, t_s)": b_ds, "k_h": k_h, r"\varepsilon_{cd,0}": eps_cd0},
            result=b_ds * k_h * eps_cd0,
            ref="EN 1992-1-1 3.1.4(6), ekv. (3.9)",
        )
        b_as = log.step(
            symbol=r"\beta_{as}(t)",
            description="Autogena krympningens utveckling",
            formula=r"1 - \exp\left(-0{,}2 \cdot t^{0{,}5}\right)",
            values={"t": td},
            result=_beta_as(td),
            ref="EN 1992-1-1 3.1.4(6), ekv. (3.13)",
        )
        eps_ca = log.step(
            symbol=r"\varepsilon_{ca}(t)",
            description="Autogen krympning vid tiden t (‰)",
            formula=r"\beta_{as}(t) \cdot \varepsilon_{ca}(\infty)",
            values={r"\beta_{as}(t)": b_as, r"\varepsilon_{ca}(\infty)": eps_ca_inf},
            result=b_as * eps_ca_inf,
            ref="EN 1992-1-1 3.1.4(6), ekv. (3.11)",
        )
        eps_cs = log.step(
            symbol=r"\varepsilon_{cs}(t)",
            description="Total krympning vid tiden t (‰)",
            formula=r"\varepsilon_{cd}(t) + \varepsilon_{ca}(t)",
            values={r"\varepsilon_{cd}(t)": eps_cd, r"\varepsilon_{ca}(t)": eps_ca},
            result=eps_cd + eps_ca,
            ref="EN 1992-1-1 3.1.4(6), ekv. (3.8)",
        )
    return Shrinkage(
        h0=h0,
        rh=rh,
        ts=ts,
        t=t,
        cement=cement,
        beta_RH=bRH,
        eps_cd0=eps_cd0,
        kh=k_h,
        beta_ds=b_ds,
        eps_cd=eps_cd,
        eps_ca_inf=eps_ca_inf,
        beta_as=b_as,
        eps_ca=eps_ca,
        eps_cs=eps_cs,
        log=log,
    )


def shrinkage_curve(sh: Shrinkage, days: Iterable[float] | None = None) -> list[dict[str, float]]:
    """Punkter för att rita krympning över tid: t (dygn), ε_cd, ε_ca och ε_cs i ‰."""
    ts = _days(sh.ts)
    h0 = float(sh.h0.to("mm").magnitude)
    out = []
    for td in days or log_days(1, 365 * 70, 50):
        e_cd = _beta_ds(td, ts, h0) * sh.kh * sh.eps_cd0
        e_ca = _beta_as(td) * sh.eps_ca_inf
        out.append({"t": td, "eps_cd": e_cd, "eps_ca": e_ca, "eps_cs": e_cd + e_ca})
    return out


# --- Hjälp -----------------------------------------------------------------------


def log_days(start: float, stop: float, n: int) -> list[float]:
    """``n`` punkter jämnt fördelade på logaritmisk skala mellan ``start`` och ``stop``."""
    a, b = math.log10(start), math.log10(stop)
    return [10 ** (a + (b - a) * i / (n - 1)) for i in range(n)]


def _tex_num(x: float) -> str:
    return f"{x:g}".replace(".", "{,}")
