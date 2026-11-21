"""Täckande betongskikt och vct (EN 1992-1-1 4.4.1).

Källor:
* EKS tabell D-1, BFS 2011:10 avd. D kap. 2.1.1 § 10 i lydelse BFS 2022:4, s. 2.
* EN 1992-1-1:2004 tabell 4.4N (konstruktionsklass S4) för rekommenderade värden.
* c_nom = c_min + Δc_dev, ekv. (4.1); c_min enligt ekv. (4.2). Handräknat nedan.
"""

import pytest

from ecdesign.core import national
from ecdesign.core.materials.durability import EXPOSURE_CLASSES, concrete_cover
from ecdesign.core.units import Q_

PHI10 = Q_(10, "mm")


def test_xc3_l50_handcalc():
    # XC3, L50, minst 80 % PC-klinker, vct ej angivet -> högsta vct 0,55, c_min,dur = 20 mm
    # c_min = max(10; 20; 10) = 20 mm, c_nom = 20 + 10 = 30 mm
    cv = concrete_cover("XC3", PHI10)
    assert cv.vct_max == 0.55
    assert cv.log.find(r"c_{min,dur,XC3}").result == Q_(20, "mm")
    assert cv.cmin == Q_(20, "mm")
    assert cv.cnom == Q_(30, "mm")
    assert all(s.ref for s in cv.log)


def test_lower_vct_gives_less_cover():
    # XC3, vct 0,50 -> raden "0,50": c_min,dur = 15 mm, c_nom = 25 mm
    cv = concrete_cover("XC3", PHI10, vct=0.50)
    assert cv.cmin_dur == Q_(15, "mm") and cv.cnom == Q_(25, "mm")


def test_bond_governs_for_large_bars():
    # XC1, L50: c_min,dur = 10 mm, men φ25 -> c_min,b = 25 mm styr. c_nom = 35 mm
    cv = concrete_cover("XC1", Q_(25, "mm"))
    assert cv.cmin == Q_(25, "mm") and cv.cnom == Q_(35, "mm")


def test_l100_and_chlorides():
    # XD3, L100, vct 0,40 -> 45 mm; c_nom = 55 mm
    cv = concrete_cover("XD3", PHI10, life="L100")
    assert cv.vct_max == 0.40 and cv.cnom == Q_(55, "mm")


def test_several_exposure_classes():
    # XC4 + XD1: vct ≤ min(0,55; 0,45) = 0,45. XC4 med vct 0,45 -> raden 0,50: 15 mm.
    # XD1 med vct 0,45 -> 25 mm. Störst styr: c_min,dur = 25 mm, c_nom = 35 mm
    cv = concrete_cover(["XC4", "XD1"], PHI10)
    assert cv.vct_max == 0.45
    assert cv.log.find(r"c_{min,dur,XC4}").result == Q_(15, "mm")
    assert cv.cmin_dur == Q_(25, "mm") and cv.cnom == Q_(35, "mm")


def test_binder_less_than_80_percent_clinker():
    # XC2, < 80 % PC-klinker, L50: högsta vct 0,55 -> 20 mm
    cv = concrete_cover("XC2", PHI10, binder="pc_lt80")
    assert cv.vct_max == 0.55 and cv.cmin_dur == Q_(20, "mm")


def test_too_high_vct_gives_warning():
    cv = concrete_cover("XC3", PHI10, vct=0.60)
    assert not cv.vct_ok and "0,55" in cv.warnings[0]


def test_x0_minimum_10_mm():
    cv = concrete_cover("X0", Q_(8, "mm"))
    assert cv.cmin == Q_(10, "mm") and cv.cnom == Q_(20, "mm")


def test_recommended_table_4_4n():
    # EN 1992-1-1 tabell 4.4N, S4: XC1 15, XC2/XC3 25, XC4 30, XD1/XS1 35, XD3 45 mm
    rec = national.load("recommended")
    expected = {"XC1": 15, "XC2": 25, "XC3": 25, "XC4": 30, "XD1": 35, "XS1": 35, "XD3": 45}
    for cls, c in expected.items():
        assert concrete_cover(cls, PHI10, annex=rec).cmin_dur == Q_(c, "mm"), cls


def test_eks_table_covers_all_exposure_classes():
    eks = national.load("eks")
    in_table = {cls for r in eks.get("cover.cmin_dur") for cls in r["classes"]}
    assert in_table == set(EXPOSURE_CLASSES)


def test_unknown_class():
    with pytest.raises(ValueError, match="XF1"):
        concrete_cover("XF1", PHI10)
