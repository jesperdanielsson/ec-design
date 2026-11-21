"""Beständighet: exponeringsklass, högsta vct och täckande betongskikt.

Ref: EN 1992-1-1 4.2 (exponeringsklasser, tabell 4.1), 4.4.1 (täckande betongskikt,
ekv. (4.1) och (4.2)). Tabellen för c_min,dur och vct är ett nationellt val och läses
från ``national/data/*.toml`` (EKS: tabell D-1, CEN: tabell 4.4N och EN 206 bilaga F).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..calclog import CalcLog
from ..national import NationalAnnex
from ..national import load as load_annex
from ..units import Q_

# Exponeringsklasser för korrosion, EN 1992-1-1 tabell 4.1 (EN 206 tabell 1).
# Frost (XF) och kemiskt angrepp (XA) påverkar inte c_min,dur och hanteras senare.
EXPOSURE_CLASSES: dict[str, dict[str, str]] = {
    "X0": {
        "group": "Ingen risk",
        "text": "Ingen risk för korrosion, t.ex. torr inomhusmiljö utan armering",
    },
    "XC1": {
        "group": "Karbonatisering",
        "text": "Torrt eller ständigt vått, t.ex. inomhus med låg luftfuktighet",
    },
    "XC2": {
        "group": "Karbonatisering",
        "text": "Vått, sällan torrt, t.ex. grundläggning, ytor i långvarig vattenkontakt",
    },
    "XC3": {
        "group": "Karbonatisering",
        "text": "Måttlig fuktighet, t.ex. utomhus skyddat från regn, fuktiga lokaler",
    },
    "XC4": {
        "group": "Karbonatisering",
        "text": "Cykliskt vått och torrt, t.ex. utomhus utsatt för regn",
    },
    "XD1": {
        "group": "Klorider (ej havsvatten)",
        "text": "Måttlig fuktighet, t.ex. ytor nära vägar med tösalt i luften",
    },
    "XD2": {
        "group": "Klorider (ej havsvatten)",
        "text": "Vått, sällan torrt, t.ex. simbassänger, industrivatten med klorider",
    },
    "XD3": {
        "group": "Klorider (ej havsvatten)",
        "text": "Cykliskt vått och torrt, t.ex. brodelar, parkeringsdäck med tösalt",
    },
    "XS1": {
        "group": "Klorider från havsvatten",
        "text": "Salt i luften utan direktkontakt, t.ex. byggnader nära kusten",
    },
    "XS2": {
        "group": "Klorider från havsvatten",
        "text": "Ständigt under vatten, t.ex. delar av marina konstruktioner",
    },
    "XS3": {
        "group": "Klorider från havsvatten",
        "text": "Tidvatten-, skvalp- och stänkzon",
    },
}

SERVICE_LIVES = {
    "L100": "100 år (t.ex. broar, monumentala byggnader)",
    "L50": "50 år (normala byggnader)",
    "L20": "20 år (tillfälliga eller kortlivade byggnader)",
}

C_MIN_ABS = Q_(10, "mm")  # EN 1992-1-1 4.4.1.2(2)P, ekv. (4.2): "10 mm"


@dataclass
class Cover:
    """Resultat av täckskiktsberäkningen. ``vct_max`` är högsta tillåtna ekvivalenta vct."""

    exposure: list[str]
    life: str
    binder: str
    vct: float | None
    vct_max: float
    vct_ok: bool
    cmin_dur: Q_
    cmin_b: Q_
    cmin: Q_
    delta_c_dev: Q_
    cnom: Q_
    warnings: list[str]
    log: CalcLog = field(repr=False)


def _rows(annex: NationalAnnex, cls: str, binder: str) -> list[dict[str, Any]]:
    rows = [
        r
        for r in annex.get("cover.cmin_dur")
        if cls in r["classes"] and r["binder"] in ("alla", binder)
    ]
    if not rows:
        raise ValueError(
            f"Exponeringsklassen {cls} finns inte i tabellen för c_min,dur ({annex.name}). "
            f"Välj bland {', '.join(EXPOSURE_CLASSES)}."
        )
    return rows


def _sv(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")


def _num(x: float) -> str:
    return f"{x:.2f}".replace(".", "{,}")


def concrete_cover(
    exposure: str | list[str],
    bar_diameter: Q_,
    life: str = "L50",
    binder: str = "pc80",
    vct: float | None = None,
    annex: NationalAnnex | None = None,
) -> Cover:
    """Högsta vct och nominellt täckande betongskikt c_nom för en eller flera exponeringsklasser.

    ``bar_diameter`` är diametern på den stång täckskiktet mäts till (normalt bygeln).
    ``vct`` är betongens ekvivalenta vct; utan värde används högsta tillåtna vct, vilket
    ger det största täckskiktet. Lägre vct än kravet kan ge mindre c_min,dur.

    Ref: EN 1992-1-1 4.4.1.1(2)P ekv. (4.1), 4.4.1.2(1)–(5) ekv. (4.2) och tabell 4.2
    (c_min,b = φ för enkla stänger), 4.4.1.3(1)P (Δc_dev). Nationellt: EKS tabell D-1
    (BFS 2011:10 avd. D, i lydelse BFS 2022:4).

    Gäller inte spännarmering eller armering < 4 mm (EKS: +10 mm), buntade stänger,
    stenstorlek > 32 mm (+5 mm), frost (XF) eller kemiskt angrepp (XA).
    """
    annex = annex or load_annex("eks")
    classes = [exposure] if isinstance(exposure, str) else list(exposure)
    if not classes:
        raise ValueError("Ange minst en exponeringsklass.")
    if life not in SERVICE_LIVES:
        raise ValueError(f"Okänd livslängdsklass {life!r}. Välj {', '.join(SERVICE_LIVES)}.")
    binders = annex.get("cover.binders")
    if binder not in binders:
        raise ValueError(f"Okänt bindemedel {binder!r}. Välj {', '.join(binders)}.")

    log = CalcLog(title=f"Täckande betongskikt, {' + '.join(classes)}, {life}")
    warnings: list[str] = []
    table_ref = "EKS tabell D-1 (BFS 2022:4)" if annex.code == "eks" else "EN 1992-1-1 tabell 4.4N"

    # Högsta tillåtna vct per klass: raden med högst vct_max.
    vct_max = 99.0
    for cls in classes:
        rows = _rows(annex, cls, binder)
        limit = max(r["vct_max"] for r in rows)
        if limit < 1.5:  # X0 har inget vct-krav
            log.step(
                symbol=rf"\mathrm{{vct}}_{{max,{cls}}}",
                description=f"Högsta ekvivalenta vct för {cls} ({binders[binder]})",
                formula=rf"\text{{tabell: {cls}}}",
                result=limit,
                ref=table_ref,
            )
        vct_max = min(vct_max, limit)

    vct_ok = vct is None or vct <= vct_max
    if not vct_ok:
        warnings.append(
            f"vct {_sv(vct)} är högre än tillåtet {_sv(vct_max)}. Välj en tätare betong "
            "(lägre vct, normalt högre hållfasthetsklass)."
        )
    vct_used = vct if vct is not None and vct_ok else vct_max

    cmin_dur_vals = []
    for cls in classes:
        rows = _rows(annex, cls, binder)
        ok = [r for r in rows if r["vct_max"] >= vct_used - 1e-9]
        row = min(ok, key=lambda r: r[life])
        vct_txt = "" if row["vct_max"] > 1.5 else rf",\ \mathrm{{vct}} \le {_num(row['vct_max'])}"
        cmin_dur_vals.append(
            log.step(
                symbol=rf"c_{{min,dur,{cls}}}",
                description=f"Minsta täckskikt för beständighet, {cls}, {SERVICE_LIVES[life]}",
                formula=rf"\text{{tabell: {cls}, {life}}}{vct_txt}",
                result=Q_(row[life], "mm"),
                ref=f"EN 1992-1-1 4.4.1.2(5), {table_ref}",
            )
        )
    if len(cmin_dur_vals) == 1:
        cmin_dur = cmin_dur_vals[0]
    else:
        syms = [rf"c_{{min,dur,{cls}}}" for cls in classes]
        cmin_dur = log.step(
            symbol=r"c_{min,dur}",
            description="Den mest krävande exponeringsklassen styr",
            formula=r"\max(" + "; ".join(syms) + ")",
            values=dict(zip(syms, cmin_dur_vals, strict=True)),
            result=max(cmin_dur_vals),
            ref="EN 1992-1-1 4.4.1.2(5)",
        )

    cmin_b = log.step(
        symbol=r"c_{min,b}",
        description="Minsta täckskikt för vidhäftning: stångdiametern (enkel stång)",
        formula=r"\phi",
        values={r"\phi": bar_diameter.to("mm")},
        result=bar_diameter.to("mm"),
        substituted="",
        ref="EN 1992-1-1 4.4.1.2(3), tabell 4.2",
    )
    d_g = Q_(float(annex.get("cover.delta_c_dur_gamma")), "mm")
    d_st = Q_(float(annex.get("cover.delta_c_dur_st")), "mm")
    d_add = Q_(float(annex.get("cover.delta_c_dur_add")), "mm")
    cmin = log.step(
        symbol=r"c_{min}",
        description=f"Minsta täckande betongskikt ({annex.name})",
        formula=(
            r"\max\left(c_{min,b};\ c_{min,dur} + \Delta c_{dur,\gamma} - \Delta c_{dur,st}"
            r" - \Delta c_{dur,add};\ 10\right)"
        ),
        values={
            r"c_{min,b}": cmin_b,
            r"c_{min,dur}": cmin_dur,
            r"\Delta c_{dur,\gamma}": d_g,
            r"\Delta c_{dur,st}": d_st,
            r"\Delta c_{dur,add}": d_add,
        },
        result=max(cmin_b, cmin_dur + d_g - d_st - d_add, C_MIN_ABS),
        ref="EN 1992-1-1 4.4.1.2(2)P, ekv. (4.2)",
    )
    dc_dev = Q_(float(annex.get("cover.delta_c_dev")), "mm")
    cnom = log.step(
        symbol=r"c_{nom}",
        description="Nominellt täckskikt att ange på ritning (minimimått + tolerans)",
        formula=r"c_{min} + \Delta c_{dev}",
        values={r"c_{min}": cmin, r"\Delta c_{dev}": dc_dev},
        result=cmin + dc_dev,
        ref="EN 1992-1-1 4.4.1.1(2)P ekv. (4.1), 4.4.1.3(1)P",
    )
    return Cover(
        exposure=classes,
        life=life,
        binder=binder,
        vct=vct,
        vct_max=vct_max,
        vct_ok=vct_ok,
        cmin_dur=cmin_dur,
        cmin_b=cmin_b,
        cmin=cmin,
        delta_c_dev=dc_dev,
        cnom=cnom,
        warnings=warnings,
        log=log,
    )
