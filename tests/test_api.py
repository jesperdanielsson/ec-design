"""API-lagret ska ge JSON-vänliga svar till gränssnittet."""

import json

from ecdesign.api import Api


def test_api_roundtrip_json():
    api = Api()
    for payload in (
        api.info(),
        api.concrete_classes(),
        api.concrete("C30/37"),
        api.reinforcement("B500B"),
        api.simply_supported(6, 10),
        api.material_options(),
        api.concrete_long_term("C30/37"),
        api.concrete_cover(["XC3"]),
    ):
        json.dumps(payload)


def test_api_concrete_values():
    d = Api().concrete("C30/37")
    assert d["properties"]["fcd"] == 20.0
    assert d["log"]["steps"]


def test_api_long_term_and_cover():
    api = Api()
    d = api.concrete_long_term("C30/37", "R", 50, 300, 500, "all", 28, 7)
    assert d["h0"] == 187.5
    assert round(d["creep"]["phi_inf"], 2) == 2.32
    assert round(d["shrinkage"]["eps_cs_inf"], 2) == 0.63
    assert len(d["logs"]) == 4
    cv = api.concrete_cover(["XC3"], "L50", "pc80", None, 10)
    assert cv["cnom"] == 30 and cv["vct_max"] == 0.55
    assert api.concrete_cover(["X0"])["vct_max"] is None
