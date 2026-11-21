"""Enheter för hela kärnan.

Alla fysiska storheter i kärnan är pint-storheter (``Q_``), aldrig nakna floats.
Använd alltid samma registry, annars går storheter inte att kombinera.
"""

from __future__ import annotations

import pint

ureg = pint.UnitRegistry()
ureg.formatter.default_format = "~P"  # kort format: "30 MPa", inte "30 megapascal"
Q_ = ureg.Quantity

# Bekväma enheter som används i byggbranschen
mm = ureg.mm
m = ureg.m
kN = ureg.kN
kNm = ureg.kN * ureg.m
MPa = ureg.MPa
GPa = ureg.GPa


def to(q: pint.Quantity, unit: str | pint.Unit) -> pint.Quantity:
    """Konvertera ``q`` till ``unit``. Ger ett tydligt fel om dimensionerna inte stämmer."""
    return q.to(unit)
