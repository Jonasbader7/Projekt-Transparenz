"""Lizenzsperre: Nur Quellen mit geprüfter, kommerziell nutzbarer Lizenz werden abgerufen.

Grundsatz (siehe docs/DATA_SOURCES.md): Eine echte Quelle darf nur genutzt werden, wenn
ihre Lizenz kommerzielle Nutzung UND Weiterveröffentlichung ausdrücklich erlaubt (oder die
Daten klar dokumentiert gemeinfrei sind), die Originalseite der Nutzungsbedingungen
hinterlegt ist und die Prüfung nicht älter als ``LICENSE_REVIEW_MAX_DAYS`` ist.
Fehlt etwas, ist die Quelle **gesperrt**: Der DataUpdateManager ruft sie nicht ab.

Fiktive Demoquellen sind ausgenommen (sie enthalten keine Daten Dritter).

Rein funktional: Das Datum wird übergeben (keine Uhr), damit es testbar bleibt.
"""

from __future__ import annotations

from datetime import date

from transparenz.config.catalog import SourceConfig
from transparenz.entities.enums import CommercialUse

# Lizenzen und Nutzungsbedingungen ändern sich (z. B. behält sich die WBA Änderungen vor).
# Nach einem Jahr muss die Prüfung wiederholt und `license_checked_on` nachgeführt werden.
LICENSE_REVIEW_MAX_DAYS = 365


def license_block_reasons(cfg: SourceConfig, today: date) -> list[str]:
    """Alle Gründe, warum die Quelle gesperrt ist. Leere Liste = freigegeben."""
    if cfg.is_fictional:
        return []
    reasons: list[str] = []
    if cfg.commercial_use != CommercialUse.JA:
        reasons.append(f"kommerzielle Nutzung «{cfg.commercial_use.value}» (verlangt: ja)")
    if cfg.redistribution != CommercialUse.JA:
        reasons.append(f"Weiterveröffentlichung «{cfg.redistribution.value}» (verlangt: ja)")
    if cfg.storage != CommercialUse.JA:
        reasons.append(f"Speicherung «{cfg.storage.value}» (verlangt: ja)")
    if cfg.derivatives != CommercialUse.JA:
        reasons.append(f"Ableitungen «{cfg.derivatives.value}» (verlangt: ja)")
    if not cfg.license_url:
        reasons.append("Offizielle Lizenz-URL (license_url) fehlt")
    if not cfg.terms_url:
        reasons.append("Originalseite der Nutzungsbedingungen (terms_url) fehlt")
    if not cfg.license.strip():
        reasons.append("Lizenzbezeichnung fehlt")
    if cfg.license_checked_on is None:
        reasons.append("Prüfdatum der Lizenz (license_checked_on) fehlt")
    else:
        age = (today - cfg.license_checked_on).days
        if age > LICENSE_REVIEW_MAX_DAYS:
            reasons.append(
                f"Lizenzprüfung vom {cfg.license_checked_on:%d.%m.%Y} ist {age} Tage alt "
                f"(höchstens {LICENSE_REVIEW_MAX_DAYS})"
            )
        elif age < 0:
            reasons.append("Prüfdatum der Lizenz liegt in der Zukunft")
    return reasons


def is_license_cleared(cfg: SourceConfig, today: date) -> bool:
    return not license_block_reasons(cfg, today)


class SourceBlockedError(Exception):
    """Abruf einer Quelle, deren Lizenz nicht freigegeben ist."""

    def __init__(self, key: str, reasons: list[str]) -> None:
        super().__init__(f"Quelle {key} gesperrt: " + "; ".join(reasons))
        self.key = key
        self.reasons = reasons
