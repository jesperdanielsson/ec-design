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
    ):
        json.dumps(payload)


def test_api_concrete_values():
    d = Api().concrete("C30/37")
    assert d["properties"]["fcd"] == 20.0
    assert d["log"]["steps"]
