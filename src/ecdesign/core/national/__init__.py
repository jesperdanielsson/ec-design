"""Nationella val (NDP) som data, inte hårdkodade i beräkningarna.

Varje land eller version är en TOML-fil i ``data/``. Beräkningarna tar emot ett
``NationalAnnex``-objekt, så att samma kod kan köras med EKS eller med
rekommenderade värden och resultaten jämföras.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from importlib import resources
from typing import Any


@dataclass(frozen=True)
class NationalAnnex:
    code: str
    name: str
    source: str
    data: dict[str, Any]

    def get(self, path: str) -> Any:
        """Hämta ett värde med punktnotation, t.ex. ``"concrete.gamma_c"``."""
        node: Any = self.data
        for key in path.split("."):
            try:
                node = node[key]
            except (KeyError, TypeError) as exc:
                raise KeyError(f"{path!r} saknas i {self.code}") from exc
        return node


def load(code: str = "eks") -> NationalAnnex:
    """Läs in ett dataset, t.ex. ``load("eks")`` eller ``load("recommended")``."""
    text = resources.files(__package__).joinpath("data", f"{code}.toml").read_text("utf-8")
    raw = tomllib.loads(text)
    meta = raw.pop("meta")
    return NationalAnnex(code=code, name=meta["name"], source=meta["source"], data=raw)


def available() -> list[str]:
    return sorted(
        p.name.removesuffix(".toml")
        for p in resources.files(__package__).joinpath("data").iterdir()
        if p.name.endswith(".toml")
    )
