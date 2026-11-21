r"""Beräkningsloggen: varje steg i en beräkning sparas med formel, insatta värden,
resultat och normhänvisning.

Loggen är produkten. Rapporten, förklaringarna i gränssnittet och testerna läser
alla samma logg, så att varje siffra kan följas och jämföras mot en handberäkning.

Exempel::

    log = CalcLog(title="Betong C30/37")
    fcm = log.step(
        symbol="f_{cm}",
        description="Medelvärde av tryckhållfasthet",
        formula=r"f_{ck} + 8\,\mathrm{MPa}",
        values={"f_{ck}": fck},
        result=fck + Q_(8, "MPa"),
        ref="EN 1992-1-1 tabell 3.1",
    )
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

import pint

_CONSTANT = re.compile(r"[\d{},.\s]+")


def _fmt(value: Any, digits: int = 4) -> str:
    """Formatera ett värde för LaTeX, med svensk decimalkomma."""
    if isinstance(value, pint.Quantity):
        mag = value.magnitude
        unit = f"{value.units:~L}"
        num = _fmt_number(mag, digits)
        return f"{num}\\,{unit}" if unit else num
    if isinstance(value, (int, float)):
        return _fmt_number(value, digits)
    return str(value)


def _fmt_number(x: float, digits: int) -> str:
    s = f"{x:.{digits}g}"
    if "e" in s:
        mant, exp = s.split("e")
        s = f"{mant} \\cdot 10^{{{int(exp)}}}"
    return s.replace(".", "{,}")


@dataclass(frozen=True)
class CalcStep:
    """Ett steg i en beräkning, t.ex. f_cm = f_ck + 8 MPa = 38 MPa."""

    symbol: str
    """LaTeX-symbol för resultatet, t.ex. ``f_{cm}``."""
    description: str
    """Kort förklaring på svenska."""
    formula: str
    """Formeln i LaTeX med symboler, utan siffror."""
    values: Mapping[str, Any]
    """Insatta värden, nyckel = LaTeX-symbol."""
    result: Any
    """Resultatet, normalt en pint-storhet."""
    ref: str = ""
    """Normhänvisning, t.ex. ``EN 1992-1-1 3.1.2 tabell 3.1``."""
    substituted: str = ""
    """Formeln med insatta siffror i LaTeX. Byggs automatiskt om den saknas."""

    def latex(self) -> str:
        """Hela steget som en LaTeX-rad: symbol = formel = insatt = resultat."""
        parts = [self.symbol]
        # En ren konstant (t.ex. "3{,}5") skrivs bara en gång.
        if not _CONSTANT.fullmatch(self.formula):
            parts.append(self.formula)
        if self.substituted:
            parts.append(self.substituted)
        parts.append(_fmt(self.result))
        return " = ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Serialiserbar form för GUI och rapport."""
        result = self.result
        if isinstance(result, pint.Quantity):
            result_out: Any = {"value": float(result.magnitude), "unit": f"{result.units:~P}"}
        else:
            result_out = result
        return {
            "symbol": self.symbol,
            "description": self.description,
            "formula": self.formula,
            "substituted": self.substituted,
            "values": {k: _fmt(v) for k, v in self.values.items()},
            "result": result_out,
            "result_latex": _fmt(self.result),
            "latex": self.latex(),
            "ref": self.ref,
        }


@dataclass
class CalcLog:
    """En ordnad lista med beräkningssteg, med en rubrik."""

    title: str
    steps: list[CalcStep] = field(default_factory=list)

    def step(
        self,
        *,
        symbol: str,
        description: str,
        formula: str,
        result: Any,
        values: Mapping[str, Any] | None = None,
        ref: str = "",
        substituted: str | None = None,
    ) -> Any:
        """Lägg till ett steg och returnera resultatet, så att anropet kan stå i en tilldelning."""
        values = dict(values or {})
        if substituted is None:
            substituted = _substitute(formula, values)
        self.steps.append(
            CalcStep(
                symbol=symbol,
                description=description,
                formula=formula,
                values=values,
                result=result,
                ref=ref,
                substituted=substituted,
            )
        )
        return result

    def extend(self, other: CalcLog) -> None:
        self.steps.extend(other.steps)

    def __iter__(self) -> Iterator[CalcStep]:
        return iter(self.steps)

    def __len__(self) -> int:
        return len(self.steps)

    def find(self, symbol: str) -> CalcStep:
        """Hitta steget som räknar ut ``symbol``. Praktiskt i tester av mellanresultat."""
        for s in self.steps:
            if s.symbol == symbol:
                return s
        raise KeyError(f"Inget steg med symbolen {symbol!r} i loggen {self.title!r}")

    def to_dict(self) -> dict[str, Any]:
        return {"title": self.title, "steps": [s.to_dict() for s in self.steps]}


def _substitute(formula: str, values: Mapping[str, Any]) -> str:
    """Ersätt symboler i formeln med insatta siffror, som i en handberäkning.

    Bara talvärdet sätts in (enheten står i resultatet), precis som normens egna
    formler skrivs, t.ex. ``22 (f_cm/10)^0,3`` med f_cm i MPa. Längsta symbolen
    ersätts först, så att ``f_{ck}`` inte förstör ``f_{ck,cube}``.
    """
    if not values:
        return ""
    out = formula
    for sym in sorted(values, key=len, reverse=True):
        v = values[sym]
        mag = v.magnitude if isinstance(v, pint.Quantity) else v
        # Ersätt bara hela symboler: "q" får inte slå ut q:et i "\\sqrt".
        pattern = rf"(?<![A-Za-z\\\\]){re.escape(sym)}(?![A-Za-z_])"
        replacement = _fmt(mag)
        out = re.sub(pattern, lambda _m, r=replacement: r, out)
    return out
