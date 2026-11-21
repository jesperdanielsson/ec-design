"""Trivialt handberäkningsfall: fritt upplagd balk, L = 6 m, q = 10 kN/m.

Handräkning: M = q L² / 8 = 10 · 36 / 8 = 45 kNm, V = q L / 2 = 30 kN.
"""

import pytest

from ecdesign.core.analysis.simply_supported import simply_supported_udl
from ecdesign.core.units import Q_


def test_moment_and_shear():
    res = simply_supported_udl(Q_(6, "m"), Q_(10, "kN/m"))
    assert res.M_max.to("kN*m").magnitude == pytest.approx(45)
    assert res.V_max.to("kN").magnitude == pytest.approx(30)


def test_log_shows_hand_calculation():
    res = simply_supported_udl(Q_(6000, "mm"), Q_(10, "N/mm"))
    step = res.log.find(r"M_{\mathrm{max}}")
    assert step.substituted == r"\frac{10 \cdot 6^2}{8}"
    assert step.latex().endswith(r"= 45\,\mathrm{kN} \cdot \mathrm{m}")
