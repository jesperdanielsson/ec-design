"""Betong mot EN 1992-1-1 tabell 3.1.

Tabellens värden är avrundade (f_ctm till 0,1 MPa, E_cm till 1 GPa). Kärnan
räknar med formlerna, och testet kontrollerar att avrundningen ger tabellens värde.
"""

import pytest

from ecdesign.core.materials.concrete import (
    STRENGTH_CLASSES,
    concrete,
    parabola_rectangle,
    parabola_rectangle_curve,
)

# Klass: (f_ctm MPa, E_cm GPa, eps_c2 ‰, eps_cu2 ‰, n) ur tabell 3.1
TABLE_3_1 = {
    "C12/15": (1.6, 27, 2.0, 3.5, 2.0),
    "C16/20": (1.9, 29, 2.0, 3.5, 2.0),
    "C20/25": (2.2, 30, 2.0, 3.5, 2.0),
    "C25/30": (2.6, 31, 2.0, 3.5, 2.0),
    "C30/37": (2.9, 33, 2.0, 3.5, 2.0),
    "C35/45": (3.2, 34, 2.0, 3.5, 2.0),
    "C40/50": (3.5, 35, 2.0, 3.5, 2.0),
    "C45/55": (3.8, 36, 2.0, 3.5, 2.0),
    "C50/60": (4.1, 37, 2.0, 3.5, 2.0),
    "C55/67": (4.2, 38, 2.2, 3.1, 1.75),
    "C60/75": (4.4, 39, 2.3, 2.9, 1.6),
    "C70/85": (4.6, 41, 2.4, 2.7, 1.45),
    "C80/95": (4.8, 42, 2.5, 2.6, 1.4),
    "C90/105": (5.0, 44, 2.6, 2.6, 1.4),
}


def test_all_classes_covered():
    assert set(TABLE_3_1) == set(STRENGTH_CLASSES)


@pytest.mark.parametrize("name", TABLE_3_1)
def test_table_3_1(name):
    fctm, Ecm, eps_c2, eps_cu2, n = TABLE_3_1[name]
    c = concrete(name)
    assert c.fcm.to("MPa").magnitude == c.fck.to("MPa").magnitude + 8
    assert round(c.fctm.to("MPa").magnitude, 1) == fctm
    assert round(c.Ecm.to("GPa").magnitude) == Ecm
    assert round(c.eps_c2, 1) == eps_c2
    assert round(c.eps_cu2, 1) == eps_cu2
    assert c.n == pytest.approx(n, abs=0.015)  # tabellen avrundar n


def test_fcd_with_eks():
    # EKS: alpha_cc = 1,0 och gamma_c = 1,5 -> f_cd = 30 / 1,5 = 20 MPa
    c = concrete("C30/37")
    assert c.fcd.to("MPa").magnitude == pytest.approx(20.0)


def test_log_has_reference_for_every_step():
    c = concrete("C30/37")
    assert len(c.log) >= 6
    assert all(step.ref for step in c.log)
    assert c.log.find("f_{ctm}").substituted == r"0{,}30 \cdot 30^{2/3}"


def test_parabola_rectangle():
    c = concrete("C30/37")
    assert parabola_rectangle(c, 0).magnitude == 0
    # Halva eps_c2 med n = 2: 1 - (1 - 0,5)^2 = 0,75
    assert parabola_rectangle(c, 1.0).to("MPa").magnitude == pytest.approx(0.75 * 20)
    assert parabola_rectangle(c, 3.0).to("MPa").magnitude == pytest.approx(20)
    curve = parabola_rectangle_curve(c, points=10)
    assert curve[0] == (0.0, 0.0) and curve[-1][0] == pytest.approx(3.5)


def test_unknown_class():
    with pytest.raises(ValueError, match="Okänd betongklass"):
        concrete("C33/40")
