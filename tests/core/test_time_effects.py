"""Hållfasthet över tid, krypning och krympning (EN 1992-1-1 3.1.2, 3.1.4, bilaga B).

Källor:
* EN 1992-1-1:2004 tabell 3.2 (ε_cd,0 för CEM klass N) och tabell 3.3 (k_h).
* Bärande konstruktioner del 1 (KTH, 2020), avsnitt B2.1.5–B2.1.6, s. B49–B55:
  tabell B2.5 (grundvärde ε_cdi = ε_cd,0/β_RH), B2.6 (β_RH), B2.7 (k_h),
  B2.8 (ε_ca(∞)), B2.9 (β(f_cm)) och figur B2.20 (β(t_0)).
* Egna handberäkningar, uträknade steg för steg i kommentarerna nedan.
"""

import math

import pytest

from ecdesign.core.materials.concrete import STRENGTH_CLASSES, concrete
from ecdesign.core.materials.time_effects import (
    beta_rh,
    creep_coefficient,
    creep_curve,
    eps_cd0_basic,
    kh,
    nominal_thickness_rect,
    shrinkage_curve,
    shrinkage_strain,
    strength_at_age,
    strength_curve,
)
from ecdesign.core.units import Q_

FCK = [12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 70, 80, 90]
NAME = {v[0]: k for k, v in STRENGTH_CLASSES.items()}

# Bärande konstruktioner del 1, tabell B2.5: ε_cdi [10⁻³] för klass S, N, R
TABLE_B2_5 = {
    "S": [0.360, 0.342, 0.325, 0.304, 0.285, 0.267, 0.250, 0.235, 0.220, 0.206, 0.193,
          0.170, 0.149, 0.131],
    "N": [0.441, 0.421, 0.401, 0.378, 0.356, 0.335, 0.315, 0.297, 0.280, 0.263, 0.248,
          0.220, 0.195, 0.173],
    "R": [0.600, 0.574, 0.550, 0.520, 0.492, 0.466, 0.441, 0.418, 0.395, 0.374, 0.354,
          0.317, 0.284, 0.255],
}  # fmt: skip

# Bärande konstruktioner del 1, tabell B2.8: ε_ca(∞) [10⁻³]
TABLE_B2_8 = [0.005, 0.015, 0.025, 0.0375, 0.050, 0.0625, 0.075, 0.0875, 0.10, 0.1125,
              0.125, 0.15, 0.175, 0.20]  # fmt: skip

# Bärande konstruktioner del 1, tabell B2.9: β(f_cm)
TABLE_B2_9 = [3.76, 3.43, 3.18, 2.93, 2.73, 2.56, 2.43, 2.31, 2.21, 2.12, 2.04, 1.90,
              1.79, 1.70]  # fmt: skip

# EN 1992-1-1 tabell 3.2: ε_cd,0 [‰] för CEM klass N, RH = 40, 60, 80, 90, 100 %
TABLE_3_2 = {
    "C20/25": [0.58, 0.49, 0.30, 0.17, 0.00],
    "C40/50": [0.46, 0.38, 0.24, 0.13, 0.00],
    "C60/75": [0.36, 0.30, 0.19, 0.10, 0.00],
    "C80/95": [0.28, 0.24, 0.15, 0.08, 0.00],
    "C90/105": [0.25, 0.21, 0.13, 0.07, 0.00],
}


@pytest.mark.parametrize("cement", ["S", "N", "R"])
def test_eps_cdi_table_b2_5(cement):
    for fck, expected in zip(FCK, TABLE_B2_5[cement], strict=True):
        assert eps_cd0_basic(fck + 8, cement) == pytest.approx(expected, abs=0.0006), fck


@pytest.mark.parametrize("name", TABLE_3_2)
def test_eps_cd0_table_3_2(name):
    fcm = concrete(name).fcm.to("MPa").magnitude
    for rh, expected in zip([40, 60, 80, 90, 100], TABLE_3_2[name], strict=True):
        assert round(eps_cd0_basic(fcm, "N") * beta_rh(rh), 2) == expected


def test_beta_rh_table_b2_6():
    assert round(beta_rh(50), 2) == 1.36
    assert round(beta_rh(80), 3) == 0.756
    assert round(beta_rh(95), 3) == 0.221


def test_kh_table_3_3():
    # Tabell 3.3 / B2.7, och linjär interpolation mellan raderna
    assert [kh(h) for h in (50, 100, 200, 300, 500, 800)] == pytest.approx(
        [1.0, 1.0, 0.85, 0.75, 0.70, 0.70]
    )
    assert kh(150) == pytest.approx(0.925)
    assert kh(400) == pytest.approx(0.725)


def test_eps_ca_inf_and_beta_fcm_tables():
    for fck, eca, bfcm in zip(FCK, TABLE_B2_8, TABLE_B2_9, strict=True):
        c = concrete(NAME[fck])
        sh = shrinkage_strain(c, Q_(200, "mm"), 50)
        assert sh.eps_ca_inf == pytest.approx(eca)
        cr = creep_coefficient(c, Q_(200, "mm"), 50, Q_(28, "day"))
        # Boken avrundar C20/25 till 3,18; 16,8/√28 = 3,175
        assert cr.beta_fcm == pytest.approx(bfcm, abs=0.006), fck


def test_beta_t0_figure_b2_20():
    c = concrete("C30/37")
    b1 = creep_coefficient(c, Q_(200, "mm"), 50, Q_(1, "day")).beta_t0
    b1000 = creep_coefficient(c, Q_(200, "mm"), 50, Q_(1000, "day")).beta_t0
    assert round(b1, 3) == 0.909 and round(b1000, 3) == 0.245


def test_nominal_thickness():
    # 300 x 500 mm: A_c = 150 000 mm², u = 1600 mm -> h_0 = 187,5 mm
    n = nominal_thickness_rect(Q_(300, "mm"), Q_(500, "mm"))
    assert n.h0.to("mm").magnitude == pytest.approx(187.5)
    # Ovansidan skyddad: u = 300 + 1000 = 1300 mm -> h_0 = 230,8 mm
    n = nominal_thickness_rect(Q_(300, "mm"), Q_(500, "mm"), "not_top")
    assert n.h0.to("mm").magnitude == pytest.approx(300000 / 1300)


def test_creep_handcalc_c30_37_cement_r():
    """Handberäkning: C30/37, 300 x 500 mm (h_0 = 187,5 mm), RH 50 %, t_0 = 28 d, cement R.

    f_cm = 38 MPa > 35 -> α1 = (35/38)^0,7 = 0,9441, α2 = (35/38)^0,2 = 0,9837
    φ_RH = [1 + 0,5/(0,1·187,5^(1/3))·0,9441]·0,9837 = [1 + 0,5/0,5724·0,9441]·0,9837 = 1,795
    β(f_cm) = 16,8/√38 = 2,725
    t_0 = 28·(9/(2 + 28^1,2) + 1)^1 = 28·(9/56,9 + 1) = 32,46 d   (cement R, α = 1)
    β(t_0) = 1/(0,1 + 32,46^0,2) = 1/(0,1 + 2,006) = 0,4749
    φ(∞, t_0) = 1,795·2,725·0,4749 = 2,323
    E_c,eff = 32,84/(1 + 2,323) = 9,88 GPa
    """
    c = concrete("C30/37")
    cr = creep_coefficient(c, Q_(187.5, "mm"), 50, Q_(28, "day"), "R")
    assert cr.log.find(r"\alpha_1").result == pytest.approx(0.9441, abs=1e-4)
    assert cr.phi_RH == pytest.approx(1.795, abs=1e-3)
    assert cr.beta_fcm == pytest.approx(2.725, abs=1e-3)
    assert cr.t0_adj.to("day").magnitude == pytest.approx(32.46, abs=0.01)
    assert cr.beta_t0 == pytest.approx(0.4749, abs=1e-4)
    assert cr.phi == pytest.approx(2.323, abs=2e-3)
    assert cr.Ec_eff.to("GPa").magnitude == pytest.approx(9.88, abs=0.01)
    assert all(s.ref for s in cr.log)


def test_creep_handcalc_c25_30_low_strength_branch():
    """Handberäkning: C25/30 (f_cm = 33 ≤ 35), h_0 = 200 mm, RH 60 %, t_0 = 14 d, cement N.

    φ_RH = 1 + 0,4/(0,1·200^(1/3)) = 1 + 0,4/0,5848 = 1,684
    β(f_cm) = 16,8/√33 = 2,925
    β(t_0) = 1/(0,1 + 14^0,2) = 1/(0,1 + 1,695) = 0,557
    φ_0 = 1,684·2,925·0,557 = 2,743
    β_H = 1,5·[1 + (0,012·60)^18]·200 + 250 = 1,5·1,00271·200 + 250 = 550,8 (< 1500)
    β_c(365, 14) = (351/(550,8 + 351))^0,3 = 0,7535
    φ(365, 14) = 2,743·0,7535 = 2,067
    """
    c = concrete("C25/30")
    cr = creep_coefficient(c, Q_(200, "mm"), 60, Q_(14, "day"), "N")
    assert cr.phi_RH == pytest.approx(1.684, abs=1e-3)
    assert cr.beta_t0 == pytest.approx(0.557, abs=1e-3)
    assert cr.phi_0 == pytest.approx(2.743, abs=2e-3)
    assert cr.beta_H == pytest.approx(550.8, abs=0.1)
    cr1 = creep_coefficient(c, Q_(200, "mm"), 60, Q_(14, "day"), "N", t=Q_(365, "day"))
    assert cr1.beta_c == pytest.approx(0.7535, abs=1e-4)
    assert cr1.phi == pytest.approx(2.067, abs=2e-3)
    assert cr1.log.find(r"\varphi(t, t_0)").result == cr1.phi


def test_creep_curve_approaches_final_value():
    c = concrete("C30/37")
    cr = creep_coefficient(c, Q_(187.5, "mm"), 50, Q_(28, "day"))
    pts = creep_curve(cr)
    values = [p for _, p in pts]
    assert values == sorted(values)
    assert 0.85 * cr.phi_0 < values[-1] < cr.phi_0


def test_shrinkage_handcalc_c30_37_cement_r():
    """Handberäkning: C30/37, h_0 = 187,5 mm, RH 50 %, cement R, slutvärde.

    β_RH = 1,55·(1 − 0,5³) = 1,356
    ε_cd,0 = 0,85·(220 + 110·6)·exp(−0,11·38/10)·10⁻⁶·1,356 = 0,668 ‰
    k_h = 1,0 + (0,85 − 1,0)·(187,5 − 100)/100 = 0,869
    ε_cd(∞) = 0,869·0,668 = 0,580 ‰,  ε_ca(∞) = 2,5·(30 − 10)·10⁻⁶ = 0,050 ‰
    ε_cs(∞) = 0,630 ‰
    """
    c = concrete("C30/37")
    sh = shrinkage_strain(c, Q_(187.5, "mm"), 50, "R")
    assert sh.beta_RH == pytest.approx(1.356, abs=1e-3)
    assert sh.eps_cd0 == pytest.approx(0.668, abs=1e-3)
    assert sh.kh == pytest.approx(0.86875)
    assert sh.eps_cd == pytest.approx(0.580, abs=1e-3)
    assert sh.eps_cs == pytest.approx(0.630, abs=1e-3)
    assert sh.log.find(r"\varepsilon_{cs}(\infty)").result == sh.eps_cs


def test_shrinkage_at_one_year():
    """Handberäkning: C25/30, h_0 = 200 mm, RH 60 %, cement N, t_s = 7 d, t = 365 d.

    ε_cd,0 = 0,85·660·exp(−0,12·3,3)·10⁻⁶·1,2152 = 0,4588 ‰,  k_h = 0,85
    β_ds = 358/(358 + 0,04·√200³) = 358/(358 + 113,1) = 0,7599
    ε_cd = 0,7599·0,85·0,4588 = 0,2963 ‰
    β_as = 1 − exp(−0,2·√365) = 0,9781,  ε_ca = 0,9781·0,0375 = 0,0367 ‰
    ε_cs = 0,333 ‰
    """
    c = concrete("C25/30")
    sh = shrinkage_strain(c, Q_(200, "mm"), 60, "N", ts=Q_(7, "day"), t=Q_(365, "day"))
    assert sh.beta_ds == pytest.approx(0.7599, abs=1e-4)
    assert sh.eps_cd == pytest.approx(0.2963, abs=1e-4)
    assert sh.beta_as == pytest.approx(0.9781, abs=1e-4)
    assert sh.eps_cs == pytest.approx(0.333, abs=1e-3)
    curve = shrinkage_curve(sh, days=[365])
    assert curve[0]["eps_cs"] == pytest.approx(sh.eps_cs)


def test_strength_at_7_days():
    """Handberäkning: C30/37, cement N (s = 0,25), t = 7 d.

    β_cc = exp(0,25·(1 − √(28/7))) = exp(−0,25) = 0,7788
    f_cm(7) = 0,7788·38 = 29,59 MPa,  f_ck(7) = 29,59 − 8 = 21,59 MPa
    f_ctm(7) = 0,7788·2,896 = 2,256 MPa (α = 1 före 28 d)
    E_cm(7) = (0,7788)^0,3·32,84 = 30,46 GPa
    """
    c = concrete("C30/37")
    s = strength_at_age(c, Q_(7, "day"), "N")
    assert s.beta_cc == pytest.approx(math.exp(-0.25))
    assert s.fcm_t.to("MPa").magnitude == pytest.approx(29.59, abs=0.01)
    assert s.fck_t.to("MPa").magnitude == pytest.approx(21.59, abs=0.01)
    assert s.fctm_t.to("MPa").magnitude == pytest.approx(2.256, abs=1e-3)
    assert s.Ecm_t.to("GPa").magnitude == pytest.approx(30.46, abs=0.01)
    # Vid 28 dygn: β_cc = 1 och alla värden som i tabell 3.1
    s28 = strength_at_age(c, Q_(28, "day"))
    assert s28.beta_cc == 1 and s28.fck_t == c.fck
    curve = strength_curve(c, "N", days=[7, 28])
    assert curve[0]["fcm"] == pytest.approx(29.59, abs=0.01)
    assert curve[1]["fck"] == 30


def test_invalid_input():
    c = concrete("C30/37")
    with pytest.raises(ValueError, match="Relativ fuktighet"):
        creep_coefficient(c, Q_(200, "mm"), 30, Q_(28, "day"))
    with pytest.raises(ValueError, match="cementklass"):
        shrinkage_strain(c, Q_(200, "mm"), 50, "X")
