r"""Balkens statiska system och linjärelastisk analys med förskjutningsmetoden.

Statiskt system
---------------
En balk består av ett eller flera *fack* mellan *stöd*. Varje stöd är

* ``free``   fri ände (konsolspets), ingen upplagsreaktion,
* ``pinned`` fritt upplag: nedböjningen hindrad, vridning fri,
* ``fixed``  fast inspänning: både nedböjning och vridning hindrade.

Exempel: fritt upplagd balk = ``[pinned, pinned]``, konsol = ``[fixed, free]``,
kontinuerlig balk över tre fack = ``[pinned, pinned, pinned, pinned]``, fritt upplagd balk
med överhäng = ``[pinned, pinned, free]``.

Analys
------
Linjärelastisk analys med konstant böjstyvhet EI (EN 1992-1-1 5.4). Balken delas i element
vid stöd, lastkanter och punktlaster, så att varje element har högst en jämnt utbredd
last över hela sin längd. Då ger förskjutningsmetoden (balkelement enligt Euler–Bernoulli
med konsistenta fixmoment) *exakta* nodförskjutningar, och snittkrafter och nedböjning
mellan noderna fås exakt ur jämvikt och elementarfall:

.. math::
    M(s) = -F_1 + F_0 \, s - \frac{q s^2}{2}, \qquad V(s) = F_0 - q s

    w(s) = \text{Hermite}(v_1, \theta_1, v_2, \theta_2) + \frac{q s^2 (L_e - s)^2}{24 EI}

där :math:`F_0, F_1` är elementets ändkrafter i vänster nod. Samma resultat som
handberäkning med elementarfall och trestödsekvationen, men för godtyckligt antal fack.

Teckenregler (som i svensk handräkning): last positiv nedåt, moment positivt med dragning
i underkant (fältmoment), stödmoment över mellanstöd blir negativa. Nedböjning positiv
nedåt. Tvärkraften V = dM/dx.

Snittkrafterna beror inte på EI när EI är konstant längs balken; EI behövs bara för
nedböjningen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from ..calclog import CalcLog
from ..loads.actions import DistributedLoad, PointLoad
from ..units import Q_

TOL = 1e-9


class SupportType(StrEnum):
    FREE = "free"
    PINNED = "pinned"
    FIXED = "fixed"

    @property
    def label(self) -> str:
        return {"free": "Fri ände", "pinned": "Fritt upplag", "fixed": "Fast inspänning"}[
            self.value
        ]


@dataclass
class BeamSystem:
    """Fackens längder och stödens typ. ``len(supports) == len(spans) + 1``."""

    spans: list[Q_]
    supports: list[SupportType]

    def __post_init__(self) -> None:
        self.supports = [SupportType(s) for s in self.supports]
        if not self.spans:
            raise ValueError("Balken måste ha minst ett fack.")
        if len(self.supports) != len(self.spans) + 1:
            raise ValueError("Antalet stöd ska vara antalet fack plus ett.")
        for i, L in enumerate(self.spans):
            if L.to("m").magnitude <= 0:
                raise ValueError(f"Fack {i + 1} måste ha en längd större än noll.")
        for i, s in enumerate(self.supports[1:-1], start=1):
            if s is SupportType.FREE:
                raise ValueError(
                    f"Stöd {self.label(i)} ligger mellan två fack och kan inte vara en fri ände."
                )
        if self.supports[0] is SupportType.FREE and self.supports[-1] is SupportType.FREE:
            if len(self.spans) < 3:
                raise ValueError("En balk med två fria ändar behöver minst två stöd emellan.")

    # --- Fabriker för vanliga fall ------------------------------------------
    @classmethod
    def simply_supported(cls, L: Q_) -> BeamSystem:
        return cls([L], [SupportType.PINNED, SupportType.PINNED])

    @classmethod
    def cantilever(cls, L: Q_) -> BeamSystem:
        return cls([L], [SupportType.FIXED, SupportType.FREE])

    # --- Geometri -------------------------------------------------------------
    @property
    def n_spans(self) -> int:
        return len(self.spans)

    @property
    def length(self) -> Q_:
        return sum((L.to("m") for L in self.spans), Q_(0, "m"))

    def x_nodes(self) -> list[float]:
        """Stödens (och de fria ändarnas) lägen i m, mätt från balkens vänstra ände."""
        xs = [0.0]
        for L in self.spans:
            xs.append(xs[-1] + float(L.to("m").magnitude))
        return xs

    @staticmethod
    def label(i: int) -> str:
        """Stödens beteckning: A, B, C …"""
        return chr(ord("A") + i) if i < 26 else f"S{i + 1}"

    def span_of(self, x: float) -> int:
        """Index för facket som innehåller ``x`` (m). Ett stödläge räknas till facket till höger."""
        xs = self.x_nodes()
        for j in range(self.n_spans):
            if x < xs[j + 1] - TOL:
                return j
        return self.n_spans - 1

    def is_cantilever_span(self, j: int) -> bool:
        """Fack med en fri ände (konsol eller överhäng)."""
        return self.supports[j] is SupportType.FREE or self.supports[j + 1] is SupportType.FREE

    @property
    def description(self) -> str:
        """Kort svensk beskrivning av det statiska systemet."""
        s = self.supports
        n = self.n_spans
        free_ends = [s[0] is SupportType.FREE, s[-1] is SupportType.FREE]
        inner = n - sum(free_ends)
        if n == 1:
            kinds = tuple(x.value for x in s)
            return {
                ("pinned", "pinned"): "Fritt upplagd balk",
                ("fixed", "free"): "Konsol, inspänd i vänster ände",
                ("free", "fixed"): "Konsol, inspänd i höger ände",
                ("fixed", "pinned"): "Ensidigt inspänd balk",
                ("pinned", "fixed"): "Ensidigt inspänd balk",
                ("fixed", "fixed"): "Tvåsidigt inspänd balk",
            }.get(kinds, "Instabil balk")
        base = "Fritt upplagd balk" if inner == 1 else f"Kontinuerlig balk, {inner} fack"
        if any(free_ends):
            base += " med " + ("överhäng i båda ändar" if all(free_ends) else "överhäng")
        if SupportType.FIXED in (s[0], s[-1]):
            base += ", inspänd ände"
        return base


# --- Förskjutningsmetoden ------------------------------------------------------


@dataclass
class _Element:
    x0: float
    L: float
    q: float
    """Jämnt utbredd last över hela elementet, kN/m, positiv nedåt."""
    dofs: tuple[int, int, int, int]
    F: list[float] = field(default_factory=lambda: [0.0] * 4)
    u: list[float] = field(default_factory=lambda: [0.0] * 4)


@dataclass
class Solution:
    """Lösningen för en uppsättning laster: snittkrafter och nedböjning i godtyckligt snitt."""

    system: BeamSystem
    EI: float
    """Böjstyvhet i kNm²."""
    elements: list[_Element]
    reactions: list[float]
    """Upplagsreaktion (kN, positiv uppåt) i varje stöd. 0 i fria ändar."""
    support_moments: list[float]
    """Inspänningsmoment (kNm) i fast inspända stöd, som böjmoment i balken."""

    def _element(self, x: float, right: bool) -> _Element:
        els = self.elements
        if right:
            for e in els:
                if x < e.x0 + e.L - TOL:
                    return e
            return els[-1]
        for e in els:
            if x <= e.x0 + e.L + TOL:
                return els[0] if x <= TOL else e
        return els[-1]

    def at(self, x: float, right: bool = True) -> tuple[float, float, float]:
        """(M i kNm, V i kN, w i m) i snittet ``x`` (m). ``right``: sida vid ett språng."""
        e = self._element(x, right)
        s = min(max(x - e.x0, 0.0), e.L)
        F0, F1 = e.F[0], e.F[1]
        M = -F1 + F0 * s - e.q * s * s / 2
        V = F0 - e.q * s
        L = e.L
        xi = s / L
        n1 = 1 - 3 * xi**2 + 2 * xi**3
        n2 = L * (xi - 2 * xi**2 + xi**3)
        n3 = 3 * xi**2 - 2 * xi**3
        n4 = L * (-(xi**2) + xi**3)
        v1, t1, v2, t2 = e.u
        v = n1 * v1 + n2 * t1 + n3 * v2 + n4 * t2 - e.q * s**2 * (L - s) ** 2 / (24 * self.EI)
        return M, V, -v


def _load_edges(loads: list, length: float) -> tuple[set[float], dict[float, float]]:
    """Lastkanter (m) och punktlaster {x: P} för en lista med laster."""
    edges: set[float] = set()
    points: dict[float, float] = {}
    for ld in loads:
        if isinstance(ld, PointLoad):
            a = round(float(ld.a.to("m").magnitude), 9)
            edges.add(a)
            points[a] = points.get(a, 0.0) + float(ld.P.to("kN").magnitude)
        else:
            a, b = udl_extent(ld, length)
            edges.update((round(a, 9), round(b, 9)))
    return edges, points


def udl_extent(ld: DistributedLoad, length: float) -> tuple[float, float]:
    """(a, b) i m för en utbredd last; hela balken om a och b saknas."""
    a = 0.0 if ld.a is None else float(ld.a.to("m").magnitude)
    b = length if ld.b is None else float(ld.b.to("m").magnitude)
    return a, b


def solve(system: BeamSystem, loads: list, EI: float = 1.0) -> Solution:
    """Lös balken för ``loads`` (utbredda laster och punktlaster, x från vänster ände).

    ``EI`` i kNm². Förskjutningsmetoden med balkelement, se modulens beskrivning.
    Ger ett tydligt fel om balken är en mekanism (för få stöd).
    """
    xs_sup = system.x_nodes()
    length = xs_sup[-1]
    edges, points = _load_edges(loads, length)
    xs = sorted({round(x, 9) for x in xs_sup} | {x for x in edges if 0 <= x <= length})
    # Slå ihop noder som ligger närmare än toleransen.
    nodes: list[float] = []
    for x in xs:
        if not nodes or x - nodes[-1] > 1e-7:
            nodes.append(x)
    n = len(nodes)
    ndof = 2 * n
    K = [[0.0] * ndof for _ in range(ndof)]
    f = [0.0] * ndof
    elements: list[_Element] = []
    udls = [(float(ld.q.to("kN/m").magnitude), *udl_extent(ld, length))
            for ld in loads if isinstance(ld, DistributedLoad)]  # fmt: skip
    for i in range(n - 1):
        x0, x1 = nodes[i], nodes[i + 1]
        L = x1 - x0
        mid = (x0 + x1) / 2
        q = sum(qq for qq, a, b in udls if a - 1e-7 <= mid <= b + 1e-7)
        d = (2 * i, 2 * i + 1, 2 * i + 2, 2 * i + 3)
        k = _k_elem(EI, L)
        for r in range(4):
            for c in range(4):
                K[d[r]][d[c]] += k[r][c]
        for r, val in enumerate(_f_eq(q, L)):
            f[d[r]] += val
        elements.append(_Element(x0, L, q, d))
    for x, P in points.items():
        i = _nearest(nodes, x)
        f[2 * i] -= P

    restrained: set[int] = set()
    sup_node = [_nearest(nodes, x) for x in xs_sup]
    for i, s in zip(sup_node, system.supports, strict=True):
        if s in (SupportType.PINNED, SupportType.FIXED):
            restrained.add(2 * i)
        if s is SupportType.FIXED:
            restrained.add(2 * i + 1)
    free = [d for d in range(ndof) if d not in restrained]
    Kr = [[K[r][c] for c in free] for r in free]
    fr = [f[r] for r in free]
    ur = _gauss(Kr, fr)
    u = [0.0] * ndof
    for d, val in zip(free, ur, strict=True):
        u[d] = val

    for e in elements:
        e.u = [u[d] for d in e.dofs]
        k = _k_elem(EI, e.L)
        feq = _f_eq(e.q, e.L)
        e.F = [sum(k[r][c] * e.u[c] for c in range(4)) - feq[r] for r in range(4)]

    reactions: list[float] = []
    moments: list[float] = []
    for i, s in zip(sup_node, system.supports, strict=True):
        if s is SupportType.FREE:
            reactions.append(0.0)
            moments.append(0.0)
            continue
        R = points.get(round(nodes[i], 9), 0.0)
        for e in elements:
            if e.dofs[0] == 2 * i:
                R += e.F[0]
            if e.dofs[2] == 2 * i:
                R += e.F[2]
        reactions.append(R)
        moments.append(0.0)
    sol = Solution(system, EI, elements, reactions, moments)
    for k, (x, s) in enumerate(zip(xs_sup, system.supports, strict=True)):
        if s is SupportType.FIXED:
            sol.support_moments[k] = sol.at(x, right=(k == 0))[0]
    return sol


def _nearest(nodes: list[float], x: float) -> int:
    return min(range(len(nodes)), key=lambda i: abs(nodes[i] - x))


def _k_elem(EI: float, L: float) -> list[list[float]]:
    """Styvhetsmatris för ett balkelement (frihetsgrader v1, θ1, v2, θ2)."""
    a = EI / L**3
    return [
        [12 * a, 6 * L * a, -12 * a, 6 * L * a],
        [6 * L * a, 4 * L * L * a, -6 * L * a, 2 * L * L * a],
        [-12 * a, -6 * L * a, 12 * a, -6 * L * a],
        [6 * L * a, 2 * L * L * a, -6 * L * a, 4 * L * L * a],
    ]


def _f_eq(q: float, L: float) -> list[float]:
    """Ekvivalenta nodlaster för jämnt utbredd last q (nedåt): fixmomenten qL²/12."""
    return [-q * L / 2, -q * L * L / 12, -q * L / 2, q * L * L / 12]


def _gauss(A: list[list[float]], b: list[float]) -> list[float]:
    """Gausselimination med pivotering. Fel om systemet är singulärt (mekanism)."""
    n = len(b)
    if n == 0:
        return []
    A = [row[:] + [b[i]] for i, row in enumerate(A)]
    scale = max(abs(A[i][i]) for i in range(n)) or 1.0
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(A[r][c]))
        if abs(A[p][c]) < 1e-10 * scale:
            raise ValueError(
                "Balken är inte stabil (en mekanism): den behöver fler stöd eller en inspänning."
            )
        A[c], A[p] = A[p], A[c]
        piv = A[c][c]
        for r in range(c + 1, n):
            fac = A[r][c] / piv
            if fac:
                row_r, row_c = A[r], A[c]
                for k in range(c, n + 1):
                    row_r[k] -= fac * row_c[k]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        s = A[r][n] - sum(A[r][k] * x[k] for k in range(r + 1, n))
        x[r] = s / A[r][r]
    return x


def split_by_span(system: BeamSystem, loads: list) -> list[list]:
    """Dela lasterna per fack (för mönsterbelastning). Utbredda laster klipps vid stöden.

    En punktlast exakt över ett mellanstöd räknas till facket till höger.
    """
    xs = system.x_nodes()
    length = xs[-1]
    out: list[list] = [[] for _ in range(system.n_spans)]
    for ld in loads:
        if isinstance(ld, PointLoad):
            out[system.span_of(float(ld.a.to("m").magnitude))].append(ld)
            continue
        a, b = udl_extent(ld, length)
        for j in range(system.n_spans):
            lo, hi = max(a, xs[j]), min(b, xs[j + 1])
            if hi - lo > TOL:
                out[j].append(DistributedLoad(ld.q, Q_(lo, "m"), Q_(hi, "m"), ld.description))
    return out


def sample_points(
    system: BeamSystem, loads_per_case: list[list], n: int = 120
) -> list[tuple[float, bool]]:
    """Snitt (x i m, höger sida) för diagram och max-sökning.

    Jämn indelning (n delar per balk, och minst 24 per fack) plus stöd och lastkanter.
    Vid stöd och punktlaster tas båda sidorna med, så att tvärkraftens språng syns.
    """
    xs_sup = system.x_nodes()
    length = xs_sup[-1]
    xs = {round(length * i / n, 9) for i in range(n + 1)}
    for j in range(system.n_spans):
        a, b = xs_sup[j], xs_sup[j + 1]
        xs.update(round(a + (b - a) * i / 24, 9) for i in range(25))
    jumps = {round(x, 9) for x in xs_sup[1:-1]}
    for loads in loads_per_case:
        edges, points = _load_edges(loads, length)
        xs.update(x for x in edges if 0 <= x <= length)
        jumps.update(x for x in points if 0 < x < length)
    pts: list[tuple[float, bool]] = []
    for x in sorted(xs):
        if x in jumps:
            pts.append((x, False))
        pts.append((x, x < length))
    return pts


def gross_stiffness(Ecm: Q_, b: Q_, h: Q_, log: CalcLog) -> Q_:
    """Böjstyvhet för osprucket rektangulärt betongtvärsnitt, armeringen försummad.

    I_c = b·h³/12 och EI = E_cm·I_c (E_cm ur EN 1992-1-1 tabell 3.1). Ger korttidsnedböjning
    i stadium I. Sprucket tvärsnitt och krypning (EN 1992-1-1 7.4.3) kommer i steg 6.
    """
    Ic = log.step(
        symbol="I_c",
        description="Tröghetsmoment, osprucket betongtvärsnitt (armeringen försummas)",
        formula=r"\frac{b \cdot h^3}{12}",
        values={"b": b.to("mm"), "h": h.to("mm")},
        result=(b * h**3 / 12).to("mm^4"),
        ref="Rektangulärt tvärsnitt, stadium I",
    )
    return log.step(
        symbol="EI",
        description="Böjstyvhet för nedböjning (korttid, osprucket)",
        formula=r"E_{cm} \cdot I_c",
        values={"E_{cm}": Ecm.to("GPa"), "I_c": Ic.to("m^4")},
        result=(Ecm * Ic).to("kN*m^2"),
        ref="EN 1992-1-1 tabell 3.1 (E_cm); jfr 7.4.3",
    )
