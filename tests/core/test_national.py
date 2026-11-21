import pytest

from ecdesign.core import national


def test_eks_values():
    eks = national.load("eks")
    assert eks.get("concrete.gamma_c") == 1.5
    assert eks.get("concrete.gamma_s") == 1.15
    assert eks.get("concrete.alpha_cc") == 1.0
    assert eks.get("safety_class.3") == 1.0
    assert eks.get("safety_class.2") == 0.91
    assert eks.get("combination.uls.xi") == 0.89
    assert eks.get("psi.B.psi2") == 0.3


def test_missing_key_gives_clear_error():
    with pytest.raises(KeyError, match="finns_inte"):
        national.load("eks").get("concrete.finns_inte")


def test_available_datasets():
    assert {"eks", "recommended"} <= set(national.available())
