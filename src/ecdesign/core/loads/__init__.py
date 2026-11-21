"""Laster och lastkombinationer enligt EN 1990/1991 med EKS.

Skelett: datamodellen finns, kombinationerna byggs i steg 3 i planen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from ..units import Q_


class LoadKind(StrEnum):
    PERMANENT = "permanent"
    VARIABLE = "variable"
    ACCIDENTAL = "accidental"


@dataclass
class LoadCase:
    """Ett lastfall, t.ex. "Egentyngd" eller "Nyttig last, kontor".

    ``category`` är nyckeln för ψ-faktorerna i det nationella datasetet (t.ex. ``"B"``).
    """

    name: str
    kind: LoadKind
    category: str | None = None
    loads: list[Load] = field(default_factory=list)


@dataclass
class Load:
    """En jämnt utbredd linjelast längs balken. Fler lasttyper tillkommer."""

    q: Q_
    description: str = ""
