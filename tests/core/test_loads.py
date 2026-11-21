"""Laster och lastkombinationer (EN 1990 med EKS).

Källor:
* Bärande konstruktioner del 1 (Chalmers, 2020), avsnitt K1.4.2, exempel s. K25–K26:
  fritt upplagd balk, g_k = 3,0, q_1k = 2,5 (ψ = 0,7/0,5/0,2), q_2k = 3,0 (ψ = 0,7/0,7/0,6).
  Boken använder ekv. 6.10 med 1,35/1,5 utan γ_d, dvs. rekommenderade värden.
* Samma exempel med EKS (6.10a/6.10b, γ_d) är handräknat nedan.
* EN 1991-1-1 tabell A.1: armerad betong 25 kN/m³. EN 1991-1-3 ekv. (5.1), tabell 5.2.
"""

import pytest

from ecdesign.core import national
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

L6 = Q_(6, "m")


def textbook_cases() -> list[LoadCase]:
    return [
        LoadCase("Permanent last g", LoadKind.PERMANENT, loads=[DistributedLoad(Q_(3.0, "kN/m"))]),
        LoadCase(
            "Variabel last q1, bunden",
            LoadKind.VARIABLE,
            psi=(0.7, 0.5, 0.2),
            loads=[DistributedLoad(Q_(2.5, "kN/m"))],
        ),
        LoadCase(
            "Variabel last q2, fri",
            LoadKind.VARIABLE,
            psi=(0.7, 0.7, 0.6),
            loads=[DistributedLoad(Q_(3.0, "kN/m"))],
        ),
    ]


def qd(cs, cid: str) -> float:
    return cs.log.find(rf"q_{{d,\mathrm{{{cid}}}}}").result.to("kN/m").magnitude


def test_textbook_example_k142():
    """Bärande konstruktioner del 1, s. K25–K26."""
    r = resolve_cases(textbook_cases(), L6)
    cs = generate_combinations(r.cases, annex=national.load("recommended"), method="6.10")
    # Alternativ 1: 1,35·3,0 + 1,5·2,5 + 1,5·0,7·3,0 = 10,95 kN/m
    assert qd(cs, "6.10-Q1") == pytest.approx(10.95)
    # Alternativ 2: 1,35·3,0 + 1,5·3,0 + 1,5·0,7·2,5 = 11,175 ≈ 11,2 kN/m (farligast)
    assert qd(cs, "6.10-Q2") == pytest.approx(11.175)
    # Karakteristisk, q2 huvudlast: 3,0 + 3,0 + 0,7·2,5 = 7,75 kN/m
    assert qd(cs, "K-Q2") == pytest.approx(7.75)
    # Långtidslast: 3,0 + 0,2·2,5 + 0,6·3,0 = 5,30 kN/m
    assert qd(cs, "QP") == pytest.approx(5.30)

    de = design_effects(L6, r.cases, cs)
    assert de.governing["uls"]["M"] == "6.10-Q2"
    # M = q_d L² / 8 = 11,175 · 36 / 8 = 50,2875 kNm
    assert de.design("uls").M_max.to("kN*m").magnitude == pytest.approx(50.2875)
    assert de.design("uls").x_M_max.magnitude == pytest.approx(3.0)
    assert de.design("quasi_permanent").M_max.magnitude == pytest.approx(5.30 * 36 / 8)
    assert de.log.find(r"M_{Ed}").result.magnitude == pytest.approx(50.2875)


def test_textbook_example_with_eks():
    """Samma laster med EKS, säkerhetsklass 2 (γ_d = 0,91), handräknat:

    6.10a:       0,91·1,35·3,0 + 0,91·1,5·0,7·(2,5 + 3,0)            = 8,94075 kN/m
    6.10b (q1):  0,91·0,89·1,35·3,0 + 0,91·1,5·2,5 + 0,91·1,5·0,7·3,0 = 9,55910 kN/m
    6.10b (q2):  0,91·0,89·1,35·3,0 + 0,91·1,5·3,0 + 0,91·1,5·0,7·2,5 = 9,76385 kN/m
    """
    r = resolve_cases(textbook_cases(), L6)
    cs = generate_combinations(r.cases, safety_class=2)
    assert cs.log.find(r"\gamma_d").result == 0.91
    assert cs.log.find(r"\xi").result == 0.89
    assert cs.log.find(r"\psi_{0,\mathrm{Q2}}").result == 0.7
    assert qd(cs, "6.10a") == pytest.approx(8.94075)
    assert qd(cs, "6.10b-Q1") == pytest.approx(9.55910)
    assert qd(cs, "6.10b-Q2") == pytest.approx(9.76385)
    # Bruksgräns påverkas inte av γ_d
    assert qd(cs, "K-Q2") == pytest.approx(7.75)
    assert qd(cs, "QP") == pytest.approx(5.30)
    # Handräkningen syns i loggen
    step = cs.log.find(r"q_{d,\mathrm{6.10b-Q2}}")
    assert step.substituted == (
        r"0{,}91 \cdot 0{,}89 \cdot 1{,}35 \cdot 3 + 0{,}91 \cdot 1{,}5 \cdot 0{,}7 \cdot 2{,}5"
        r" + 0{,}91 \cdot 1{,}5 \cdot 3"
    )
    de = design_effects(L6, r.cases, cs)
    assert de.governing["uls"]["M"] == de.governing["uls"]["V"] == "6.10b-Q2"
    # V = q_d L / 2 = 9,76385 · 3 = 29,29 kN
    assert de.design("uls", "V").V_abs.magnitude == pytest.approx(9.76385 * 3)
    assert all(s.ref for s in [*cs.log, *de.log])


def test_safety_class_3_and_permanent_only():
    # Bara permanent last, SK3: 6.10a (1,35) styr över 6.10b (0,89·1,35 = 1,2015)
    cases = [LoadCase("G", LoadKind.PERMANENT, loads=[DistributedLoad(Q_(10, "kN/m"))])]
    r = resolve_cases(cases, L6)
    cs = generate_combinations(r.cases, safety_class=3)
    assert qd(cs, "6.10a") == pytest.approx(13.5)
    assert qd(cs, "6.10b") == pytest.approx(12.015)
    de = design_effects(L6, r.cases, cs)
    assert de.governing["uls"]["M"] == "6.10a"
    assert [c.id for c in cs.combinations] == ["6.10a", "6.10b", "K", "F", "QP"]


def test_method_610_not_allowed_in_eks():
    r = resolve_cases(textbook_cases(), L6)
    with pytest.raises(ValueError, match="inte tillåten"):
        generate_combinations(r.cases, method="6.10")


def test_self_weight_area_load_and_snow():
    cases = [
        LoadCase("Egentyngd och golv", LoadKind.PERMANENT, self_weight=True,
                 loads=[DistributedLoad(Q_(1.0, "kN/m^2"))]),
        LoadCase("Kontor", LoadKind.VARIABLE, category="B",
                 loads=[DistributedLoad(Q_(2.5, "kN/m^2"))]),
        LoadCase("Snö", LoadKind.VARIABLE, snow_sk=Q_(2.5, "kN/m^2")),
    ]  # fmt: skip
    r = resolve_cases(cases, L6, width=Q_(4, "m"), b=Q_(300, "mm"), h=Q_(500, "mm"))
    # g = 25 · 0,3 · 0,5 = 3,75 kN/m (EN 1991-1-1 tabell A.1)
    assert r.log.find(r"g_{k,\mathrm{G1},\mathrm{egen}}").result.magnitude == pytest.approx(3.75)
    # Golv 1,0 kN/m² · 4 m = 4 kN/m; kontor 2,5 · 4 = 10 kN/m
    assert r.log.find(r"q_{k,\mathrm{G1}}").result.magnitude == pytest.approx(4.0)
    assert r.log.find(r"q_{k,\mathrm{Q1}}").result.magnitude == pytest.approx(10.0)
    # Snö: s = 0,8 · 1,0 · 1,0 · 2,5 = 2,0 kN/m², 2 ≤ s_k < 3 -> ψ0 = 0,7, ψ1 = 0,4, ψ2 = 0,2
    assert r.log.find(r"s_{\mathrm{Q2}}").result.magnitude == pytest.approx(2.0)
    assert r.log.find(r"q_{k,\mathrm{Q2}}").result.magnitude == pytest.approx(8.0)
    snow = r.cases[2]
    assert snow.category == "snow_mid"
    cs = generate_combinations(r.cases)
    assert cs.psi["Q2"] == (0.7, 0.4, 0.2)


@pytest.mark.parametrize(
    ("sk", "cat"), [(1.0, "snow_low"), (1.99, "snow_low"), (2.0, "snow_mid"), (3.5, "snow_high")]
)
def test_snow_psi_category(sk, cat):
    from ecdesign.core.loads import snow_category

    assert snow_category(Q_(sk, "kN/m^2"), national.load("eks")) == cat


def test_point_and_partial_loads():
    """Elementarfall, fritt upplagd balk (Diverse utdrag 2018, bilaga B.1), handräknat:

    P = 10 kN i a = 2 m:            R_A = 10·4/6 = 6,667 kN
    q = 4 kN/m på 1–4 m, F = 12 kN: R_A = 12·(6 − 2,5)/6 = 7,0 kN
    R_A = 13,667 kN, R_B = 22 − 13,667 = 8,333 kN
    M(2) = 13,667·2 − 4·1²/2 = 25,333 kNm
    """
    from ecdesign.core.analysis.simply_supported import forces_at, reactions

    loads = [
        PointLoad(Q_(10, "kN"), Q_(2, "m")),
        DistributedLoad(Q_(4, "kN/m"), Q_(1, "m"), Q_(4, "m")),
    ]
    RA, RB = reactions(L6, loads)
    assert RA.magnitude == pytest.approx(13.6667, abs=1e-4)
    assert RB.magnitude == pytest.approx(8.3333, abs=1e-4)
    M, V_left = forces_at(6, loads, 2, right=False)
    _, V_right = forces_at(6, loads, 2, right=True)
    assert M == pytest.approx(25.3333, abs=1e-4)
    assert V_left - V_right == pytest.approx(10)  # språng = punktlasten


def test_exact_position_of_max_moment():
    """q = 10 kN/m och P = 20 kN i x = 2 m, L = 6 m. Handräknat:

    R_A = 30 + 20·4/6 = 43,333 kN. V = 0 där 43,333 − 10x − 20 = 0 -> x = 2,333 m
    M = 43,333·2,333 − 10·2,333²/2 − 20·0,333 = 67,22 kNm
    """
    cases = [
        LoadCase("G", LoadKind.PERMANENT,
                 loads=[DistributedLoad(Q_(10, "kN/m")), PointLoad(Q_(20, "kN"), Q_(2, "m"))]),
    ]  # fmt: skip
    r = resolve_cases(cases, L6)
    de = design_effects(L6, r.cases, generate_combinations(r.cases, 3))
    qp = de.get("QP")
    assert qp.x_M_max.magnitude == pytest.approx(7 / 3)
    assert qp.M_max.magnitude == pytest.approx(67.2222, abs=1e-4)
    assert qp.R_A.magnitude == pytest.approx(43.3333, abs=1e-4)


def test_favourable_loads():
    """Vindsug uppåt (−5 kN/m) och egentyngd 2 kN/m, SK3, ψ0 vind = 0,3 (EKS).

    Största positiva moment: vinden är gynnsam och tas inte med (faktor 0).
    Största negativa moment (lyft): 6.10b med vind som huvudlast, permanent last gynnsam
    med 1,0:  q = 1,0·2 + 1,0·1,5·(−5) = −5,5 kN/m -> M = −5,5·36/8 = −24,75 kNm
    """
    cases = [
        LoadCase("G", LoadKind.PERMANENT, loads=[DistributedLoad(Q_(2, "kN/m"))]),
        LoadCase("Vind", LoadKind.VARIABLE, category="wind",
                 loads=[DistributedLoad(Q_(-5, "kN/m"))]),
    ]  # fmt: skip
    r = resolve_cases(cases, L6)
    cs = generate_combinations(r.cases, 3)
    de = design_effects(L6, r.cases, cs)
    b = de.get("6.10b-Q1")
    assert b.M_max.magnitude == pytest.approx(0.89 * 1.35 * 2 * 36 / 8)
    assert b.M_min.magnitude == pytest.approx(-24.75)
    assert de.governing["uls"]["M"] == "6.10b-Q1"  # |−24,75| > 1,35·9 = 12,15
    # q_d i loggen gäller nedåtriktad last: vinden gynnsam (0), G ogynnsam: 0,89·1,35·2
    assert qd(cs, "6.10b-Q1") == pytest.approx(2.403)


def test_load_outside_span_is_rejected():
    cases = [LoadCase("G", LoadKind.PERMANENT, loads=[PointLoad(Q_(5, "kN"), Q_(7, "m"))])]
    with pytest.raises(ValueError, match="utanför spannet"):
        resolve_cases(cases, L6)
    cases = [LoadCase("Q", LoadKind.VARIABLE, category="B",
                      loads=[DistributedLoad(Q_(5, "kN/m"), Q_(4, "m"), Q_(2, "m"))])]  # fmt: skip
    with pytest.raises(ValueError, match="inom spannet"):
        resolve_cases(cases, L6)


def test_area_load_needs_width():
    cases = [LoadCase("G", LoadKind.PERMANENT, loads=[DistributedLoad(Q_(1, "kN/m^2"))])]
    with pytest.raises(ValueError, match="belastningsbredd"):
        resolve_cases(cases, L6)
