import pytest

from ecdesign.core.materials.reinforcement import reinforcement


def test_b500b_with_eks():
    r = reinforcement("B500B")
    assert r.fyd.to("MPa").magnitude == pytest.approx(434.8, abs=0.1)
    assert r.eps_yd == pytest.approx(2.17, abs=0.01)
    assert r.ductility == "B"
