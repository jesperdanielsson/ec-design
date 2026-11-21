"""Statiska system: konsol, inspänd, kontinuerlig balk och mönsterbelastning.

Källor:
* "Diverse utdrag 2018" (Chalmers), bilaga B, Elementarfall för balkar med konstant
  styvhet, s. 369–372: B.1 fritt upplagd, B.2 fast inspänd konsol, B.3 ensidig fast
  inspänning, B.4 tvåsidig fast inspänning. W1 = q·L (total utbredd last).
* Bärande konstruktioner del 1 (Chalmers 2020), fig. B1.16 s. B15: trestödsbalk med lika
  fack och utbredd last, M_s = qL²/8 och M_f = 9qL²/128. Fig. K1.12 s. K24: fri variabel
  last placeras fack för fack så att den verkar ogynnsamt.
* Trefacksbalk och mönsterbelastning: handräknat med trestödsekvationen nedan.
"""

import pytest

from ecdesign.core import national
from ecdesign.core.analysis.beam import BeamSystem, SupportType, solve
from ecdesign.core.analysis.load_effects import design_effects
from ecdesign.core.loads import (
    DistributedLoad,
    LoadCase,
    LoadKind,
    PointLoad,
    generate_combinations,
    resolve_cases,
)
from ecdesign.core.units import Q_

P, F, X = SupportType.PINNED, SupportType.FIXED, SupportType.FREE
L = 6.0
EI = 10_000.0  # kNm²
q = 10.0  # kN/m
Pk = 20.0  # kN


def udl(value=q, a=None, b=None):
    return DistributedLoad(
        Q_(value, "kN/m"), None if a is None else Q_(a, "m"), None if b is None else Q_(b, "m")
    )


def point(value, a):
    return PointLoad(Q_(value, "kN"), Q_(a, "m"))


def system(spans, supports):
    return BeamSystem([Q_(s, "m") for s in spans], supports)


# --- Elementarfall, Diverse utdrag 2018 bilaga B ------------------------------------


def test_b1_simply_supported():
    """B.1: p1 = 5·W1·L³/(384·EI) för utbredd last, P·L³/(48·EI) för punktlast i mitten."""
    s = solve(system([L], [P, P]), [udl()], EI)
    M, V, w = s.at(L / 2)
    assert M == pytest.approx(q * L**2 / 8)
    assert w == pytest.approx(5 * q * L**4 / (384 * EI))
    assert s.reactions == pytest.approx([q * L / 2, q * L / 2])
    s = solve(system([L], [P, P]), [point(Pk, L / 2)], EI)
    assert s.at(L / 2)[0] == pytest.approx(Pk * L / 4)
    assert s.at(L / 2)[2] == pytest.approx(Pk * L**3 / (48 * EI))


def test_b2_cantilever():
    """B.2 fast inspänd konsol: M1 = P·L, p1 = P·L³/(3EI); M1 = W1·L/2, p1 = W1·L³/(8EI)."""
    sys = BeamSystem.cantilever(Q_(L, "m"))
    s = solve(sys, [point(Pk, L)], EI)
    assert s.at(0)[0] == pytest.approx(-Pk * L)  # stödmoment: dragning i överkant
    assert s.at(L, right=False)[2] == pytest.approx(Pk * L**3 / (3 * EI))
    assert s.reactions[0] == pytest.approx(Pk)
    s = solve(sys, [udl()], EI)
    assert s.at(0)[0] == pytest.approx(-q * L**2 / 2)
    assert s.at(0)[1] == pytest.approx(q * L)
    assert s.at(L, right=False)[2] == pytest.approx(q * L**4 / (8 * EI))
    assert s.support_moments[0] == pytest.approx(-q * L**2 / 2)


def test_b3_propped_cantilever():
    """B.3 ensidig fast inspänning (fritt upplag vänster, inspänd höger).

    Utbredd last: R1 = 3/8·W1, R2 = 5/8·W1, M2 = W1·L/8, p1(L/2) = W1·L³/(192·EI).
    Punktlast i mitten: R1 = 5/16·P, M2 = 3PL/16, moment under lasten 5PL/32,
    p1 = 7PL³/(768·EI).
    """
    sys = system([L], [P, F])
    W1 = q * L
    s = solve(sys, [udl()], EI)
    assert s.reactions == pytest.approx([3 / 8 * W1, 5 / 8 * W1])
    assert s.at(L, right=False)[0] == pytest.approx(-W1 * L / 8)
    assert s.at(L / 2)[2] == pytest.approx(W1 * L**3 / (192 * EI))
    s = solve(sys, [point(Pk, L / 2)], EI)
    assert s.reactions[0] == pytest.approx(5 / 16 * Pk)
    assert s.at(L, right=False)[0] == pytest.approx(-3 * Pk * L / 16)
    assert s.at(L / 2)[0] == pytest.approx(5 * Pk * L / 32)
    assert s.at(L / 2)[2] == pytest.approx(7 * Pk * L**3 / (768 * EI))


def test_b4_fixed_fixed():
    """B.4 tvåsidig fast inspänning: M1 = M2 = W1·L/12, mitt W1·L/24, p1 = W1·L³/(384·EI).

    Punktlast i mitten: M = PL/8 vid stöd och i mitten, p1 = PL³/(192·EI).
    """
    sys = system([L], [F, F])
    s = solve(sys, [udl()], EI)
    assert s.at(0)[0] == pytest.approx(-q * L**2 / 12)
    assert s.at(L / 2)[0] == pytest.approx(q * L**2 / 24)
    assert s.at(L / 2)[2] == pytest.approx(q * L**4 / (384 * EI))
    s = solve(sys, [point(Pk, L / 2)], EI)
    assert s.at(0)[0] == pytest.approx(-Pk * L / 8)
    assert s.at(L / 2)[0] == pytest.approx(Pk * L / 8)
    assert s.at(L / 2)[2] == pytest.approx(Pk * L**3 / (192 * EI))


def test_partial_load_matches_simply_supported_elementary_case():
    """Samma delutbredda last och punktlast som i test_loads (R_A = 13,667 kN)."""
    s = solve(system([L], [P, P]), [point(10, 2), udl(4, 1, 4)], EI)
    assert s.reactions[0] == pytest.approx(13.6667, abs=1e-4)
    assert s.at(2)[0] == pytest.approx(25.3333, abs=1e-4)
    assert s.at(2, right=False)[1] - s.at(2)[1] == pytest.approx(10)


# --- Kontinuerliga balkar ------------------------------------------------------------


def test_two_span_textbook_b116():
    """Bärande konstruktioner del 1 fig. B1.16: M_s = qL²/8, M_f = 9qL²/128 vid x = 3L/8."""
    s = solve(system([L, L], [P, P, P]), [udl()], EI)
    assert s.at(L)[0] == pytest.approx(-q * L**2 / 8)
    assert s.at(3 * L / 8)[0] == pytest.approx(9 * q * L**2 / 128)
    # Reaktioner: 3/8·qL, 10/8·qL, 3/8·qL
    assert s.reactions == pytest.approx([3 / 8 * q * L, 5 / 4 * q * L, 3 / 8 * q * L])


def test_three_span_three_moment_equation():
    """Trestödsekvationen för tre lika fack, symmetri M_B = M_C:

    M_A·L + 2·M_B·(L + L) + M_C·L = −q·L³/4 − q·L³/4  ->  5·M_B·L = −q·L³/2
    M_B = −q·L²/10 = −36 kNm. Fack 1: R_A = qL/2 + M_B/L = 30 − 6 = 24 kN,
    M_f = R_A²/(2q) = 28,8 kNm = 0,08·q·L².
    """
    s = solve(system([L, L, L], [P, P, P, P]), [udl()], EI)
    assert s.at(L)[0] == pytest.approx(-0.1 * q * L**2)
    assert s.at(2 * L)[0] == pytest.approx(-0.1 * q * L**2)
    assert s.reactions[0] == pytest.approx(24)
    assert s.at(2.4)[0] == pytest.approx(0.08 * q * L**2)


def test_mechanism_is_rejected():
    with pytest.raises(ValueError, match="mekanism"):
        solve(system([L], [P, X]), [udl()], EI)
    with pytest.raises(ValueError, match="fri ände"):
        system([L, L], [P, X, P])


# --- Lastkombinationer och mönsterbelastning ---------------------------------------


def two_span_cases():
    return [
        LoadCase("Egentyngd", LoadKind.PERMANENT, loads=[udl(10)]),
        LoadCase("Nyttig last", LoadKind.VARIABLE, psi=(0.7, 0.5, 0.3), loads=[udl(10)]),
    ]


def test_pattern_loading_two_spans():
    """Två lika fack L = 6 m, g = q = 10 kN/m, ekv. 6.10 utan γ_d (rekommenderade värden).

    g_d = 1,35·10 = 13,5 kN/m på båda facken (bunden last), q_d = 1,5·10 = 15 kN/m.

    Största fältmoment, q_d bara i fack 1 (trestödsekvationen):
      M_B = −g_d·L²/8 − q_d·L²/16 = −60,75 − 33,75 = −94,5 kNm
      R_A = 28,5·6/2 − 94,5/6 = 69,75 kN, x = 69,75/28,5 = 2,447 m
      M_f = R_A²/(2·28,5) = 85,35 kNm  (utan mönsterlast bara 9/128·28,5·36 = 72,14 kNm)
    Största stödmoment, q_d i båda facken: M_B = −28,5·36/8 = −128,25 kNm
    Största reaktion i B, båda facken belastade: 5/4·28,5·6 = 213,75 kN
    """
    sys = system([L, L], [P, P, P])
    r = resolve_cases(two_span_cases(), sys.length)
    cs = generate_combinations(r.cases, annex=national.load("recommended"), method="6.10")
    de = design_effects(sys, r.cases, cs)
    e = de.get("6.10-Q1")
    assert e.M_max.magnitude == pytest.approx(69.75**2 / 57)
    assert e.x_M_max.magnitude == pytest.approx(69.75 / 28.5)
    assert e.loaded_spans_M == {"Q1": [0]}
    assert e.M_min.magnitude == pytest.approx(-128.25)
    assert e.support_M[1].magnitude == pytest.approx(-128.25)
    assert e.reactions[1][0].magnitude == pytest.approx(213.75)
    assert e.reactions[0][0].magnitude == pytest.approx(69.75)
    # Loggen visar vilka fack som är belastade
    step = de.log.find(r"M_{Ed,\mathrm{6.10-Q1}}")
    assert "Q1 på fack 1" in step.description
    assert step.result.magnitude == pytest.approx(85.3520, abs=1e-4)
    assert de.log.find(r"M_{B,\mathrm{G1}}").result.magnitude == pytest.approx(-45)

    # Utan mönsterbelastning: bara 9/128 · 28,5 · 36
    de2 = design_effects(sys, r.cases, cs, pattern=False)
    assert de2.get("6.10-Q1").M_max.magnitude == pytest.approx(9 / 128 * 28.5 * 36)
    assert de2.get("6.10-Q1").M_min.magnitude == pytest.approx(-128.25)


def test_overhang_uplift_and_negative_moment():
    """Fritt upplagd balk 6 m med 2 m överhäng, bara variabel last 10 kN/m, karakteristisk.

    Fält: överhänget obelastat -> M = 10·36/8 = 45 kNm
    Stöd B: bara överhänget belastat -> M_B = −10·2²/2 = −20 kNm, R_A = −20/6 = −3,33 kN
    """
    sys = system([L, 2], [P, P, X])
    cases = [LoadCase("Q", LoadKind.VARIABLE, psi=(0.7, 0.5, 0.3), loads=[udl(10)])]
    r = resolve_cases(cases, sys.length)
    cs = generate_combinations(r.cases)
    de = design_effects(sys, r.cases, cs)
    k = de.get("K-Q1")
    assert k.M_max.magnitude == pytest.approx(45)
    assert k.x_M_max.magnitude == pytest.approx(3)
    assert k.M_min.magnitude == pytest.approx(-20)
    assert k.reactions[0][1].magnitude == pytest.approx(-20 / 6)
    assert k.reactions[2] == (Q_(0, "kN"), Q_(0, "kN"))
    assert any("lyftande" in w for w in de.warnings)
    assert "överhäng" in sys.description


def test_cantilever_with_eks_combinations():
    """Konsol 2 m, g = 5 kN/m, q = 3 kN/m (kategori B), SK2. Handräknat:

    6.10b-Q1: q_d = 0,91·0,89·1,35·5 + 0,91·1,5·3 = 5,4668 + 4,095 = 9,5618 kN/m
    M_Ed = −q_d·L²/2 = −19,124 kNm, V_Ed = q_d·L = 19,124 kN
    """
    sys = BeamSystem.cantilever(Q_(2, "m"))
    cases = [
        LoadCase("G", LoadKind.PERMANENT, loads=[udl(5)]),
        LoadCase("Q", LoadKind.VARIABLE, category="B", loads=[udl(3)]),
    ]
    r = resolve_cases(cases, sys.length)
    cs = generate_combinations(r.cases, 2)
    de = design_effects(sys, r.cases, cs)
    qd = 0.91 * 0.89 * 1.35 * 5 + 0.91 * 1.5 * 3
    e = de.design("uls", "M_neg")
    assert e.combination.id == "6.10b-Q1"
    assert e.M_min.magnitude == pytest.approx(-qd * 2)
    assert e.M_max.magnitude == 0
    assert de.design("uls", "V").V_abs.magnitude == pytest.approx(qd * 2)
    assert de.system.description == "Konsol, inspänd i vänster ände"


def test_deflection_quasi_permanent():
    """Fritt upplagd, L = 6 m, g = 10, q = 10 kN/m med ψ2 = 0,3, EI = 10 000 kNm².

    Kvasipermanent: 10 + 0,3·10 = 13 kN/m, δ = 5·13·6⁴/(384·10 000) = 21,94 mm
    L/δ = 6000/21,94 = 273
    """
    sys = system([L], [P, P])
    r = resolve_cases(two_span_cases(), sys.length)
    cs = generate_combinations(r.cases)
    de = design_effects(sys, r.cases, cs, EI=Q_(EI, "kN*m^2"))
    qp = de.get("QP")
    expected = 5 * 13 * L**4 / (384 * EI) * 1000
    assert qp.w_max.to("mm").magnitude == pytest.approx(expected)
    assert qp.x_w.magnitude == pytest.approx(3, abs=1e-4)
    assert de.log.find(r"\delta_{k,\mathrm{QP}}").result.magnitude == pytest.approx(expected)
    assert de.log.find(r"L_{1}/\delta_{k,\mathrm{kvasi}}").result == round(6000 / expected)


def test_deflection_two_span_pattern():
    """Två fack, bara variabel last q = 10 kN/m i fack 1 (karakteristisk, ψ ointressant).

    Största nedböjningen i fack 1 fås med fack 2 obelastat. Med trestödsekvationen:
    M_B = −qL²/16. Nedböjning ur superposition (B.1): δ(x) = q x (L³ − 2Lx² + x³)/(24EI)
    + M_B · x (L² − x²)/(6 L EI). Maxvärdet söks numeriskt nedan och jämförs.
    """
    sys = system([L, L], [P, P, P])
    cases = [LoadCase("Q", LoadKind.VARIABLE, psi=(0.7, 0.5, 0.3), loads=[udl(10)])]
    r = resolve_cases(cases, sys.length)
    de = design_effects(sys, r.cases, generate_combinations(r.cases), EI=Q_(EI, "kN*m^2"))
    MB = -q * L**2 / 16

    def delta(x):
        return q * x * (L**3 - 2 * L * x**2 + x**3) / (24 * EI) + MB * x * (L**2 - x**2) / (
            6 * L * EI
        )

    hand = max(delta(i * L / 10000) for i in range(10001)) * 1000
    k = de.get("K-Q1")
    assert k.spans[0].w_max.value.magnitude == pytest.approx(hand, rel=1e-6)
    assert k.spans[0].w_max.loaded_spans == {"Q1": [0]}


def test_gross_stiffness():
    """C30/37: E_cm = 33 GPa (EN 1992-1-1 tabell 3.1). b = 300, h = 500 mm, handräknat:

    I_c = 300·500³/12 = 3,125·10⁹ mm⁴, EI = 33·10⁶ kN/m² · 3,125·10⁻³ m⁴ = 103 125 kNm²
    """
    from ecdesign.core.analysis.beam import gross_stiffness
    from ecdesign.core.calclog import CalcLog

    log = CalcLog("EI")
    EI_c = gross_stiffness(Q_(33, "GPa"), Q_(300, "mm"), Q_(500, "mm"), log)
    assert log.find("I_c").result.to("mm^4").magnitude == pytest.approx(3.125e9)
    assert EI_c.to("kN*m^2").magnitude == pytest.approx(103125)
