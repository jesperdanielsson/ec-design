"""Beräkningsloggen: grundkravet i steg 1 är att ett trivialt fall loggar
formel, insatta värden, resultat och normhänvisning."""

from ecdesign.core.calclog import CalcLog, _substitute
from ecdesign.core.units import Q_


def test_step_returns_result_and_logs_everything():
    log = CalcLog(title="Test")
    fck = Q_(30, "MPa")
    fcm = log.step(
        symbol="f_{cm}",
        description="Medelvärde",
        formula="f_{ck} + 8",
        values={"f_{ck}": fck},
        result=fck + Q_(8, "MPa"),
        ref="EN 1992-1-1 tabell 3.1",
    )
    assert fcm == Q_(38, "MPa")
    step = log.find("f_{cm}")
    assert step.formula == "f_{ck} + 8"
    assert step.substituted == "30 + 8"
    assert step.ref == "EN 1992-1-1 tabell 3.1"
    assert step.latex() == r"f_{cm} = f_{ck} + 8 = 30 + 8 = 38\,\mathrm{MPa}"


def test_decimal_comma_in_latex():
    log = CalcLog(title="Test")
    log.step(symbol="x", description="", formula="a / 3", values={"a": 1}, result=1 / 3)
    assert "0{,}3333" in log.steps[0].latex()


def test_substitution_only_replaces_whole_symbols():
    # "q" får inte ersättas inuti "\sqrt", och f_{ck} inte inuti f_{ck,cube}
    assert _substitute(r"\sqrt{q} + q", {"q": 4}) == r"\sqrt{4} + 4"
    out = _substitute("f_{ck} + f_{ck,cube}", {"f_{ck}": 30, "f_{ck,cube}": 37})
    assert out == "30 + 37"


def test_to_dict_is_json_friendly():
    import json

    log = CalcLog(title="Test")
    log.step(symbol="M", description="", formula="q L^2/8", values={}, result=Q_(45, "kN*m"))
    d = log.to_dict()
    json.dumps(d)
    assert d["steps"][0]["result"] == {"value": 45.0, "unit": "kN⋅m"}
