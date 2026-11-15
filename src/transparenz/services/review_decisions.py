"""Entscheid-Speicher für unsichere Zuordnungen (Position → Unternehmen).

Jeder Entscheid ist eine Zeile «ISIN gehört zu LEI: ja/nein» mit Datum und dem Signal, das den
Fall unsicher machte. Die Datei wird nur ergänzt; der jüngste Entscheid je Paar gilt. Ein
Entscheid wirkt in jedem künftigen Lauf und für jeden Fonds, der dieselbe ISIN hält.

Bewusst kein lernendes Modell: Die Statistik je Signal (`decision_stats`) zeigt, wie oft
Menschen ein bestimmtes Signal bestätigen oder ablehnen. Erst wenn ein Signal oft genug und
immer gleich entschieden wurde, darf daraus später eine automatische Regel werden.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, field_validator

from transparenz.entities.identifiers import is_valid_isin, is_valid_lei

FIELDS = ("isin", "lei", "decision", "decided_on", "signal", "note")
Decision = Literal["yes", "no"]


class MappingDecision(BaseModel):
    """Menschlicher Entscheid: Gehört das Wertpapier mit dieser ISIN zum Rechtsträger mit LEI?"""

    isin: str
    lei: str
    decision: Decision
    decided_on: date
    signal: str = ""
    note: str = ""

    @field_validator("isin")
    @classmethod
    def _isin(cls, value: str) -> str:
        value = value.strip().upper()
        if not is_valid_isin(value):
            raise ValueError(f"ungültige ISIN-Prüfziffer: {value!r}")
        return value

    @field_validator("lei")
    @classmethod
    def _lei(cls, value: str) -> str:
        value = value.strip().upper()
        if not is_valid_lei(value):
            raise ValueError(f"ungültige LEI-Prüfziffer: {value!r}")
        return value

    @field_validator("signal", "note")
    @classmethod
    def _one_line(cls, value: str) -> str:
        return " ".join((value or "").split())


def load_decisions(path: Path) -> list[MappingDecision]:
    """Liest die Entscheid-Datei. Fehlt sie, gibt es noch keine Entscheide."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = set(FIELDS[:4]) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: Spalten fehlen: {sorted(missing)}")
        decisions = []
        for number, row in enumerate(reader, start=2):
            try:
                decisions.append(MappingDecision(**{k: row.get(k) or "" for k in FIELDS}))
            except ValueError as exc:
                raise ValueError(f"{path}, Zeile {number}: {exc}") from exc
    index_decisions(decisions)  # Widersprüche sofort melden, nicht erst beim Auswerten
    return decisions


def index_decisions(decisions: list[MappingDecision]) -> dict[str, dict[str, Decision]]:
    """ISIN → LEI → geltender Entscheid (der jüngste in Dateireihenfolge).

    Zwei verschiedene LEIs mit «ja» für dieselbe ISIN sind ein Widerspruch und brechen ab:
    Ein Wertpapier hat genau einen Emittenten.
    """
    index: dict[str, dict[str, Decision]] = defaultdict(dict)
    for item in decisions:
        index[item.isin][item.lei] = item.decision
    for isin, by_lei in index.items():
        approved = sorted(lei for lei, decision in by_lei.items() if decision == "yes")
        if len(approved) > 1:
            raise ValueError(f"Widerspruch: ISIN {isin} ist zwei LEIs zugeordnet "
                             f"({', '.join(approved)}). Einen der Entscheide auf «no» setzen.")
    return dict(index)


def append_decision(path: Path, decision: MappingDecision) -> None:
    """Hängt einen Entscheid an; prüft vorher, dass kein Widerspruch entsteht."""
    index_decisions([*load_decisions(path), decision])
    new_file = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow({**decision.model_dump(), "decided_on": decision.decided_on.isoformat()})


def decision_stats(decisions: list[MappingDecision]) -> dict[str, dict[str, int]]:
    """Je Signal: wie oft bestätigt, wie oft abgelehnt (nur der geltende Entscheid je Paar)."""
    latest: dict[tuple[str, str], MappingDecision] = {}
    for item in decisions:
        latest[(item.isin, item.lei)] = item
    stats: dict[str, dict[str, int]] = defaultdict(lambda: {"yes": 0, "no": 0})
    for item in latest.values():
        stats[item.signal or "unbekannt"][item.decision] += 1
    return dict(sorted(stats.items()))
