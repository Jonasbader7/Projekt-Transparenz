"""Beziehungstypen zwischen einem Unternehmen und einer Anlage (rein funktional, ohne Datei/Uhr).

Eine Besitzkette aus einer Quelle (z. B. Global Energy Monitor) sagt, wer an wem wie viel hält.
Sie sagt nicht, **auf wessen Rechnung**. Ein Vermögensverwalter, der 6 % eines Stromkonzerns
für seine Kunden hält, ist wirtschaftlich nicht an dessen Kraftwerken beteiligt; eine Bank,
die Aktien verwahrt, ebenso wenig. Dieses Modul trennt deshalb jede Kette in genau einen
Beziehungstyp und begründet die Einordnung mit dem Glied der Kette, das sie auslöst.

Regeln (in dieser Reihenfolge, die erste zutreffende gilt):

1. **Verwahrung** – ein Glied der Kette ist eine Verwahr-, Nominee- oder Treuhandbank.
2. **Vermögensverwaltung** – ein Glied ist ein Fonds, eine Fonds- oder
   Vermögensverwaltungsgesellschaft, eine Pensionskasse oder eine Treuhandgesellschaft.
3. **Finanzbeteiligung, Rechnung ungeklärt** – das Unternehmen ist ein Finanzinstitut, und
   die Kette verlässt seinen Konzern (erstes Glied unter 50 %) mit einem Anteil unter 20 % an
   einer börsenkotierten Gesellschaft. Solche gemeldeten Bestände sind typischerweise
   Kundenvermögen oder Handelsbestand; die Quelle belegt keine eigene Rechnung.
4. **Eigentum auf eigene Rechnung** – alles Übrige: direkt, über Tochtergesellschaften oder
   als eigene Beteiligung an einer Projekt- oder Betriebsgesellschaft.

Die Namensmuster dienen nur der Einordnung einer bereits über Kennungen zugeordneten Kette,
nie der Zuordnung eines Unternehmens. Jede Einordnung nennt ihren Grund und bleibt prüfbar.
Finanzierung, Betrieb und Lieferverträge sind eigene Beziehungstypen; sie entstehen nie aus
einer Besitzkette, sondern nur aus einer Quelle, die genau diese Beziehung belegt.
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

# ASCII-Schlüssel; deutsche Anzeigetexte stehen in criteria.toml (Bewertungsregel) und im Bericht.
OWN_ACCOUNT = "own_account"
FINANCIAL_STAKE = "financial_stake_unclear"
ASSET_MANAGEMENT = "asset_management"
CUSTODY = "custody"
FINANCING = "financing"
OPERATION = "operation"
SUPPLY_CONTRACT = "supply_contract"
RELATIONSHIP_TYPES = (OWN_ACCOUNT, FINANCIAL_STAKE, ASSET_MANAGEMENT, CUSTODY, FINANCING,
                      OPERATION, SUPPLY_CONTRACT)
# Typen, die aus einer Besitzkette entstehen können.
OWNERSHIP_TYPES = (OWN_ACCOUNT, FINANCIAL_STAKE, ASSET_MANAGEMENT, CUSTODY)

CONTROL_SHARE = 50.0        # ab hier gilt ein Glied als Tochtergesellschaft (Konzern)
PORTFOLIO_SHARE = 20.0      # darunter: Finanzbeteiligung, wenn Halter ein Finanzinstitut ist

CUSTODY_RE = re.compile(
    r"nominee|custod|securities clearing|depositor|depositar|master trust bank|"
    r"trust and banking|trust & banking|bank and trust|bank & trust|settlement", re.I)
ASSET_MANAGEMENT_RE = re.compile(
    r"asset management|investment management|wealth management|global advisors|"
    r"\badvis[eo]rs?\b|\bfunds?\b|\bfondi?\b|\bsgr\b|\bsicav\b|\bucits\b|\betf\b|"
    r"pension|superannuation|\btrust (co|corp|corporation|company)\b|\btrustees?\b|"
    # Polnische Pensions- und Fondsgesellschaften beginnen mit «PTE»/«TFI»; «Pte Ltd» am Ende
    # ist dagegen die Rechtsform in Singapur. Kotierte «… Partners LP» sind keine Verwalter.
    r"towarzystwo emerytalne|^pte\s|^tfi\s|private equity", re.I)
# Wörter, an denen die Branchenangabe einer Quelle ein Finanzinstitut erkennen lässt.
FINANCIAL_SECTOR_RE = re.compile(
    r"\bbank|insur|asset manage|investment manage|financial (services|institution)|"
    r"investment (company|firm|bank)|broker|private equity|pension|reinsur|"
    r"financial conglomerate|stock exchange|custodian", re.I)

_HOP_RE = re.compile(r"^(?P<name>.*?)\s*\[(?P<share>[^\]]*)\]\s*$")


@dataclass(frozen=True)
class Hop:
    """Ein Glied der Kette: ``holder`` hält ``share`` Prozent an ``name``."""
    holder: str
    name: str
    share: float | None  # None = Anteil unbekannt

    @property
    def controlled(self) -> bool:
        return self.share is not None and self.share >= CONTROL_SHARE


@dataclass(frozen=True)
class ChainClass:
    relationship: str
    reason: str
    deciding_hop: int | None  # Index des auslösenden Glieds, None = keines (Eigenbesitz)
    group_exit_hop: int | None  # erstes Glied unter 50 % (Konzerngrenze), None = keine


def parse_share(text: str | None) -> float | None:
    """«5.8%», «100.0%» → Zahl; «unknown %» oder leer → ``None`` (nie 0)."""
    cleaned = (text or "").replace("%", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_path(path: str | None) -> list[Hop]:
    """Zerlegt «A -> B [100.0%] -> C [5.8%] -> Anlage [100.0%]» in Glieder.

    Das letzte Glied ist die Anlage. Ein Pfad ohne Glieder ergibt eine leere Liste.
    """
    parts = [p.strip() for p in (path or "").split(" -> ") if p.strip()]
    if len(parts) < 2:
        return []
    hops: list[Hop] = []
    holder = parts[0]
    for part in parts[1:]:
        match = _HOP_RE.match(part)
        name = match.group("name").strip() if match else part
        hops.append(Hop(holder=holder, name=name,
                        share=parse_share(match.group("share")) if match else None))
        holder = name
    return hops


def is_financial_sector(labels: Iterable[str] | None) -> bool | None:
    """Finanzinstitut laut Branchenangaben einer Quelle? ``None``: keine Angabe vorhanden."""
    values = [label for label in (labels or []) if label]
    if not values:
        return None
    return any(FINANCIAL_SECTOR_RE.search(label) for label in values)


def classify_chain(hops: list[Hop], *, holder_is_financial: bool | None,
                   listed: Mapping[str, bool] | None = None) -> ChainClass:
    """Ordnet eine Besitzkette genau einem Beziehungstyp zu (Regeln im Modulkopf).

    ``listed`` sagt je Gesellschaftsname, ob die Quelle sie als börsenkotiert führt. Fehlt die
    Angabe, gilt die Gesellschaft als nicht kotiert (Regel 3 greift dann nicht).
    """
    listed = listed or {}
    exit_hop = next((i for i, hop in enumerate(hops[:-1]) if not hop.controlled), None)
    if not hops:
        return ChainClass(OWN_ACCOUNT, "Keine Kette angegeben.", None, None)
    names = [hops[0].holder, *(hop.name for hop in hops[:-1])]  # ohne die Anlage selbst
    for index, name in enumerate(names):
        if CUSTODY_RE.search(name):
            return ChainClass(CUSTODY, f"«{name}» ist eine Verwahr- oder Nominee-Gesellschaft: "
                              "Sie hält Wertpapiere für Dritte.", max(index - 1, 0), exit_hop)
    for index, name in enumerate(names):
        if ASSET_MANAGEMENT_RE.search(name):
            return ChainClass(
                ASSET_MANAGEMENT, f"«{name}» ist ein Fonds oder eine Vermögens- bzw. "
                "Treuhandverwaltung: Die Anlagen gehören den Anlegern oder Begünstigten.",
                max(index - 1, 0), exit_hop)
    if exit_hop is not None and holder_is_financial:
        # Ab der Konzerngrenze: erster Minderheitsanteil an einer börsenkotierten Gesellschaft.
        portfolio = next((i for i in range(exit_hop, len(hops) - 1)
                          if listed.get(hops[i].name) and not hops[i].controlled
                          and (hops[i].share is None or hops[i].share < PORTFOLIO_SHARE)), None)
        if portfolio is not None:
            hop = hops[portfolio]
            share = "unbekanntem Anteil" if hop.share is None else f"{hop.share:g} %"
            return ChainClass(
                FINANCIAL_STAKE, f"Finanzinstitut mit {share} an der börsenkotierten «{hop.name}». "
                "Die Quelle belegt nicht, ob der Bestand eigenes Vermögen oder Kundenvermögen ist.",
                portfolio, exit_hop)
    if exit_hop is None:
        reason = "Direkt oder über Tochtergesellschaften (jedes Glied ab 50 %)."
    else:
        hop = hops[exit_hop]
        share = "unbekanntem Anteil" if hop.share is None else f"{hop.share:g} %"
        reason = f"Eigene Beteiligung von {share} an «{hop.name}»."
    return ChainClass(OWN_ACCOUNT, reason, None, exit_hop)


def stake_tier(share: float | None) -> str:
    """Stufe des durchgerechneten Anteils: control, significant, small oder unknown."""
    if share is None:
        return "unknown"
    return "control" if share >= CONTROL_SHARE else (
        "significant" if share >= PORTFOLIO_SHARE else "small")
