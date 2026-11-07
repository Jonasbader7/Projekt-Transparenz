"""Kennungen: ISIN (Wertpapier) und LEI (Rechtsträger) – bewusst getrennt.

* ISIN (ISO 6166) identifiziert ein **Wertpapier**, nicht ein Unternehmen.
* LEI (ISO 17442) identifiziert einen **Rechtsträger**.

Fiktive Kennungen: ISINs mit Länderpräfix ``ZZ`` (ISO-3166 «user-assigned», nie ein
echtes Land) und LEIs mit Präfix ``FIKT00``. So kann keine Demo-Kennung mit einer
realen verwechselt werden.
"""

from __future__ import annotations

import re
import unicodedata

FICTIONAL_ISIN_PREFIX = "ZZ"
FICTIONAL_LEI_PREFIX = "FIKT00"

_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
_LEI_RE = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")


def _alnum_to_digits(value: str) -> str:
    return "".join(str(int(ch, 36)) for ch in value)


def isin_check_digit(body: str) -> int:
    """Prüfziffer für die ersten 11 Zeichen einer ISIN (Luhn über Ziffernfolge)."""
    if len(body) != 11 or not body.isalnum():
        raise ValueError("ISIN-Körper muss 11 alphanumerische Zeichen haben.")
    digits = _alnum_to_digits(body.upper())
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return (10 - total % 10) % 10


def is_valid_isin(value: str | None) -> bool:
    if not value:
        return False
    value = value.strip().upper()
    if not _ISIN_RE.match(value):
        return False
    return isin_check_digit(value[:11]) == int(value[11])


def make_isin(body: str) -> str:
    """Hängt die korrekte Prüfziffer an einen 11-stelligen Körper an."""
    body = body.upper()
    return f"{body}{isin_check_digit(body)}"


def is_fictional_isin(value: str) -> bool:
    return value.upper().startswith(FICTIONAL_ISIN_PREFIX)


def lei_check_digits(base: str) -> str:
    """Prüfziffern (ISO 7064 MOD 97-10) für die ersten 18 Zeichen eines LEI."""
    if len(base) != 18 or not base.isalnum():
        raise ValueError("LEI-Basis muss 18 alphanumerische Zeichen haben.")
    remainder = int(_alnum_to_digits(base.upper() + "00")) % 97
    return f"{98 - remainder:02d}"


def is_valid_lei(value: str | None) -> bool:
    if not value:
        return False
    value = value.strip().upper()
    if not _LEI_RE.match(value):
        return False
    return int(_alnum_to_digits(value)) % 97 == 1


def make_lei(base: str) -> str:
    base = base.upper()
    return f"{base}{lei_check_digits(base)}"


def is_fictional_lei(value: str) -> bool:
    return value.upper().startswith(FICTIONAL_LEI_PREFIX)


_LEGAL_FORMS = {
    "ag",
    "sa",
    "se",
    "plc",
    "inc",
    "corp",
    "corporation",
    "ltd",
    "limited",
    "gmbh",
    "nv",
    "bv",
    "spa",
    "co",
    "holding",
    "holdings",
    "group",
    "gruppe",
}


def normalize_company_name(name: str) -> str:
    """Normalisiert einen Firmennamen für den (unsicheren) Namensabgleich."""
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    text = text.replace(".", "")  # «S.A.» → «SA», «Inc.» → «Inc»
    text = re.sub(r"[^a-zA-Z0-9 ]+", " ", text.lower())
    tokens = [t for t in text.split() if t not in _LEGAL_FORMS]
    return " ".join(tokens)


def normalize_publisher(name: str) -> str:
    """Normalisiert Herausgebernamen, um Unabhängigkeit von Quellen zu beurteilen."""
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", text.lower())).strip()
