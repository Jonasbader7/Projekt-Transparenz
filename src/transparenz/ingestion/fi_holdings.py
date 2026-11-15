"""Finansinspektionen (Schweden), Register «Fondinnehav»: Quartalsbestände als XML lesen."""
from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from transparenz.entities.identifiers import is_valid_isin

FI_NS = "{http://schemas.fi.se/publika/vardepappersfonder/20200331}"

FI_ATTRIBUTION = "Finansinspektionen (FI), Register «Fondinnehav»"

FI_TERMS_URL = "https://www.fi.se/sv/om-fi/om-webbplatsen/oppen-data/"


# ------------------------------------------------------------------------ Positionen


@dataclass


class Position:
    name: str
    isin: str | None
    isin_valid: bool
    issuer_country: str | None
    currency: str | None
    asset_class: str | None
    market_value: float | None
    weight_percent: float | None


@dataclass


class Fund:
    quarter_end: str
    manager_name: str
    manager_lei: str | None
    fund_name: str
    fund_isin: str | None
    net_assets: float | None
    positions: list[Position] = field(default_factory=list)


def _number(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return None


def parse_fund(content: bytes) -> Fund:
    """Liest eine FI-Fondsdatei. Fehlende Pflichtangaben sind ein Fehler, kein Standardwert."""
    root = ET.fromstring(content)
    info = next((n for n in root.findall(FI_NS + "Fondinformation")
                 if n.find(FI_NS + "Fond_namn") is not None), None)
    quarter_end = root.findtext(f"{FI_NS}Rapportinformation/{FI_NS}Kvartalsslut")
    if info is None or not quarter_end:
        raise ValueError("FI-Datei ohne Fondinformation oder Kvartalsslut.")
    company = root.find(FI_NS + "Bolagsinformation")
    fund = Fund(
        quarter_end=quarter_end,
        manager_name=(company.findtext(FI_NS + "Fondbolag_namn") or "") if company is not None
        else "",
        manager_lei=company.findtext(FI_NS + "Fondbolag_LEI-kod") if company is not None else None,
        fund_name=info.findtext(FI_NS + "Fond_namn") or "",
        fund_isin=info.findtext(FI_NS + "Fond_ISIN-kod") or None,
        net_assets=_number(info.findtext(FI_NS + "Fondförmögenhet")),
    )
    for node in info.findall(f"{FI_NS}FinansiellaInstrument/{FI_NS}FinansielltInstrument"):
        isin = (node.findtext(FI_NS + "ISIN-kod_instrument") or "").strip().upper() or None
        fund.positions.append(Position(
            name=(node.findtext(FI_NS + "Instrumentnamn") or "").strip(),
            isin=isin,
            isin_valid=is_valid_isin(isin),
            issuer_country=node.findtext(FI_NS + "Landkod_Emittent") or None,
            currency=node.findtext(FI_NS + "Valuta") or None,
            asset_class=node.findtext(FI_NS + "Tillgångsslag_enligt_LVF_5_kap") or None,
            market_value=_number(node.findtext(FI_NS + "Marknadsvärde_instrument")),
            weight_percent=_number(node.findtext(FI_NS + "Andel_av_fondförmögenhet_instrument")),
        ))
    return fund


def find_fund(zip_path: Path, fund_name: str) -> tuple[str, Fund]:
    """Sucht genau einen Fonds über den exakten Namen (Gross-/Kleinschreibung egal)."""
    wanted = fund_name.strip().casefold()
    hits: list[tuple[str, Fund]] = []
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            if not member.filename.lower().endswith(".xml"):
                continue
            try:
                fund = parse_fund(archive.read(member))
            except (ET.ParseError, ValueError):
                continue
            if fund.fund_name.strip().casefold() == wanted:
                hits.append((member.filename, fund))
    if len(hits) != 1:
        raise ValueError(f"Fonds «{fund_name}»: {len(hits)} Treffer, genau einer erwartet.")
    return hits[0]
