import pytest

from ecdesign.core.units import Q_, to


def test_conversion():
    assert to(Q_(1, "kN*m"), "N*mm").magnitude == pytest.approx(1e6)


def test_wrong_dimension_raises():
    import pint

    with pytest.raises(pint.DimensionalityError):
        to(Q_(1, "kN"), "MPa")
