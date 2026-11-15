"""Anzeigetexte der Fondskette: Schlüssel bleiben deckungsgleich mit den Beziehungstypen."""

from __future__ import annotations

from transparenz.entities.labels import GEM_STAKE_LABELS, RELATIONSHIP_LABELS
from transparenz.ingestion.gem import GEM_STAKES
from transparenz.services.ownership import RELATIONSHIP_TYPES


def test_every_relationship_type_has_a_label() -> None:
    assert set(RELATIONSHIP_LABELS) == set(RELATIONSHIP_TYPES)


def test_every_gem_stake_has_a_label() -> None:
    assert set(GEM_STAKES) <= set(GEM_STAKE_LABELS)
