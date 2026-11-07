"""Zuordnungsquote: Wie viele Fondspositionen lassen sich sicher einem Unternehmen zuordnen?

Gemessen wird stufenweise, nach Anzahl UND nach Fondsgewicht (Prozentpunkte):

1. ``relevant``       – Positionen, die überhaupt einem Emittenten zugeordnet werden können
                        (Aktien, Anleihen; ohne Barmittel, Derivate, Sonstige)
2. ``with_isin``      – davon mit ISIN
3. ``resolved``       – davon ISIN → Unternehmen zugeordnet (Wertpapier-Stammdaten)
4. ``with_lei``       – davon Unternehmen mit LEI
5. ``lei_in_gleif``   – davon LEI in einem aktiven GLEIF-Datenstand gefunden

Stufe 5 zählt nur LEIs aus Quellen mit Format ``gleif_json`` – fiktive LEIs (``FIKT00…``)
können dort nie vorkommen. Rein funktional (keine Datenbank, keine Uhr).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from transparenz.entities.enums import AssetClass
from transparenz.entities.models import Position
from transparenz.entities.resolution import EntityResolver

RELEVANT_ASSET_CLASSES = frozenset({AssetClass.AKTIE, AssetClass.ANLEIHE})


@dataclass(frozen=True)
class Step:
    key: str  # siehe STEP_LABELS
    count: int
    weight_pct: float


@dataclass(frozen=True)
class Gap:
    position_name: str
    isin: str | None
    weight_pct: float
    reason: str


@dataclass
class MappingQuality:
    total_positions: int
    total_weight_pct: float
    steps: list[Step] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)

    def step(self, key: str) -> Step:
        for s in self.steps:
            if s.key == key:
                return s
        raise KeyError(key)

    def share(self, key: str, base: str = "relevant") -> tuple[float | None, float | None]:
        """Anteil (Anzahl, Gewicht) einer Stufe an der Basisstufe in Prozent; None bei 0."""
        s, b = self.step(key), self.step(base)
        by_count = 100.0 * s.count / b.count if b.count else None
        by_weight = 100.0 * s.weight_pct / b.weight_pct if b.weight_pct else None
        return by_count, by_weight


STEP_LABELS: dict[str, str] = {
    "relevant": "Aktien und Anleihen",
    "with_isin": "mit ISIN",
    "resolved": "ISIN → Unternehmen zugeordnet",
    "with_lei": "Unternehmen mit LEI",
    "lei_in_gleif": "LEI bei GLEIF gefunden",
}


def measure_mapping_quality(
    positions: Iterable[Position], resolver: EntityResolver, gleif_leis: set[str]
) -> MappingQuality:
    positions = list(positions)
    buckets: dict[str, list[Position]] = {k: [] for k in STEP_LABELS}
    gaps: list[Gap] = []
    for p in positions:
        if p.asset_class not in RELEVANT_ASSET_CLASSES:
            continue
        buckets["relevant"].append(p)
        if not p.isin:
            gaps.append(Gap(p.name, None, p.weight_pct, "keine ISIN"))
            continue
        buckets["with_isin"].append(p)
        res = resolver.resolve_security(p.isin)
        if not res.resolved or res.company_key is None:
            gaps.append(Gap(p.name, p.isin, p.weight_pct, res.note))
            continue
        buckets["resolved"].append(p)
        company = resolver.companies[res.company_key]
        if not company.lei:
            gaps.append(Gap(p.name, p.isin, p.weight_pct, "Emittent ohne LEI"))
            continue
        buckets["with_lei"].append(p)
        if company.lei not in gleif_leis:
            gaps.append(Gap(p.name, p.isin, p.weight_pct, "LEI nicht in GLEIF-Datenstand"))
            continue
        buckets["lei_in_gleif"].append(p)

    return MappingQuality(
        total_positions=len(positions),
        total_weight_pct=round(sum(p.weight_pct for p in positions), 4),
        steps=[
            Step(key, len(items), round(sum(p.weight_pct for p in items), 4))
            for key, items in buckets.items()
        ],
        gaps=sorted(gaps, key=lambda g: -g.weight_pct),
    )
