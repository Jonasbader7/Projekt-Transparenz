"""Zeitfunktionen. Intern werden Zeitpunkte als naive UTC-Werte gespeichert."""

from __future__ import annotations

from datetime import UTC, date, datetime


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def format_date(value: date | datetime | None) -> str:
    """Schweizer Datumsformat, z. B. 07.11.2026."""
    if value is None:
        return "–"
    return value.strftime("%d.%m.%Y")


def format_datetime(value: datetime | None) -> str:
    if value is None:
        return "–"
    return value.strftime("%d.%m.%Y %H:%M UTC")
