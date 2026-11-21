"""API-lagret ska ge JSON-vänliga svar till gränssnittet."""

import json

from ecdesign.api import Api

CASES = [
    {"name": "Egentyngd", "kind": "permanent", "self_weight": True,
     "loads": [{"type": "udl", "value": 3, "unit": "kN/m"}]},
    {"name": "Kontor", "kind": "variable", "category": "B",
     "loads": [{"type": "udl", "value": 2.5, "unit": "kN/m2"},
               {"type": "point", "value": 10, "a_m": 2}]},
    {"name": "Snö", "kind": "variable", "snow": {"sk": 2.0, "mu": 0.8},
     "loads": [{"type": "partial", "value": 1, "unit": "kN/m", "a_m": 0, "b_m": 3}]},
]  # fmt: skip


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
        api.load_options(),
        api.loads(6, 300, 500, 1, 2, CASES),
        api.loads(0, 300, 500, 1, 2, CASES, None, {"spans_m": [3], "supports": ["fixed", "free"]}),
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


def test_api_loads():
    d = Api().loads(6, 300, 500, 1, 3, CASES)
    assert [c["id"] for c in d["cases"]] == ["G1", "Q1", "Q2"]
    # g = 25·0,3·0,5 + 3 = 6,75 kN/m som två laster
    assert [ld["q"] for ld in d["cases"][0]["loads"]] == [3.75, 3.0]
    assert d["cases"][2]["category"] == "snow_mid"
    ids = [c["id"] for c in d["combinations"]]
    assert ids == ["6.10a", "6.10b-Q1", "6.10b-Q2", "K-Q1", "K-Q2", "F-Q1", "F-Q2", "QP"]
    assert sum(c["governs_M"] for c in d["combinations"]) == 4  # en per grupp
    assert d["design"]["uls"]["combination_M"] == "6.10b-Q1"
    assert len(d["diagrams"]["x"]) == len(d["diagrams"]["uls"]["M_max"])
    assert len(d["logs"]) == 4  # laster, kombinationer, böjstyvhet, snittkrafter
    assert d["system"]["description"] == "Fritt upplagd balk"
    assert d["design"]["quasi_permanent"]["w"] > 0


def test_api_continuous_beam_with_overhang():
    """Två fack och överhäng: varje fack och stöd får egna dimensionerande värden."""
    system = {"spans_m": [5, 5, 1.5], "supports": ["pinned", "pinned", "pinned", "free"]}
    d = Api().loads(0, 300, 500, 4, 2, CASES[:2], system=system)
    json.dumps(d)
    assert d["system"]["length"] == 11.5
    assert [s["label"] for s in d["system"]["supports"]] == ["A", "B", "C", "D"]
    assert d["system"]["pattern"] is True
    uls = d["design"]["uls"]
    assert len(uls["spans"]) == 3
    assert [s["label"] for s in uls["supports"]] == ["A", "B", "C"]
    assert uls["supports"][1]["M"] < 0  # stödmoment över mellanstödet
    assert uls["spans"][2]["cantilever"] is True
    assert len(d["diagrams"]["uls"]["w_max"]) == len(d["diagrams"]["x"])
    arr = d["combinations"][1]["arrangements"]
    assert len(arr) > 1 and all(len(a["M"]) == len(d["diagrams"]["x"]) for a in arr)
