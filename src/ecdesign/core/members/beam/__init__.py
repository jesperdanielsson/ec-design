"""Armerad betongbalk. Skelett: geometrimodellen finns, kontrollerna byggs i steg 5–6."""

from __future__ import annotations

from dataclasses import dataclass

from ...units import Q_


@dataclass
class RectangularSection:
    b: Q_
    h: Q_

    @property
    def area(self) -> Q_:
        return (self.b * self.h).to("mm**2")


@dataclass
class BeamModel:
    span: Q_
    section: RectangularSection
    cover: Q_
    concrete: str = "C30/37"
    reinforcement: str = "B500B"
