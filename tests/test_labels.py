"""Jeder Aufzählungswert hat eine eigene deutsche Bezeichnung – auch bei gleichlautenden Werten."""

from __future__ import annotations

from enum import Enum

import pytest

from transparenz.entities import enums
from transparenz.entities.labels import _BY_TYPE, SHORT_STATUS, label

ENUMS = [
    obj for obj in vars(enums).values()
    if isinstance(obj, type) and issubclass(obj, Enum) and obj.__module__ == enums.__name__
]


@pytest.mark.parametrize("enum_type", ENUMS, ids=lambda e: e.__name__)
def test_every_member_has_a_label(enum_type: type[Enum]) -> None:
    for member in enum_type:
        assert (enum_type, member.value) in _BY_TYPE, f"{enum_type.__name__}.{member.name}"
        assert label(member)


def test_same_values_in_different_enums_get_their_own_label() -> None:
    assert label(enums.AssessmentStatus.UNBEKANNT) == "Unbekannt (keine Datenabdeckung)"
    assert label(enums.ProceedingStatus.UNBEKANNT) == "unbekannt"
    assert label(enums.AssessmentStatus.NICHT_ANWENDBAR) == "Nicht anwendbar"
    assert label(enums.ProceedingStatus.NICHT_ANWENDBAR) == "–"


def test_short_status_complete() -> None:
    assert set(SHORT_STATUS) == set(enums.AssessmentStatus)
