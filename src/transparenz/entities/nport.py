"""SEC Form N-PORT: geprüfte Zeilen der Quartalsdatensätze, so wie gemeldet («as filed»).

Gemeldete Kennungen bleiben unverändert erhalten (``*_reported``). Daneben steht die geprüfte
Kennung (nur bei gültiger Prüfziffer) und ein Status, warum sie fehlt. So bleibt jede Zahl bis
zur Originalzeile nachvollziehbar, und eine ungültige Kennung wird nie still korrigiert.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ACCESSION = r"^\d{10}-\d{2}-\d{6}$"
QUARTER = r"^\d{4}q[1-4]$"

IdentifierStatus = Literal["valid", "missing", "not_applicable", "invalid_format",
                           "invalid_checksum"]


class NportSubmission(BaseModel):
    """Eine Meldung (SUBMISSION + REGISTRANT + FUND_REPORTED_INFO, Schlüssel ACCESSION_NUMBER)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    quarter: str = Field(pattern=QUARTER)
    accession: str = Field(pattern=ACCESSION)
    filing_date: date
    sub_type: str = Field(min_length=1, max_length=15)
    report_date: date
    fiscal_year_end: date | None = None
    is_last_filing: bool | None = None
    cik: str | None = Field(default=None, pattern=r"^\d{10}$")
    registrant_name: str | None = None
    registrant_lei_reported: str | None = None
    registrant_lei: str | None = Field(default=None, pattern=r"^[A-Z0-9]{18}[0-9]{2}$")
    series_id: str | None = Field(default=None, pattern=r"^S\d{9}$")
    series_id_reported: str | None = None
    series_name: str | None = None
    series_lei_reported: str | None = None
    series_lei: str | None = Field(default=None, pattern=r"^[A-Z0-9]{18}[0-9]{2}$")
    total_assets: float | None = None
    net_assets: float | None = None


class NportHolding(BaseModel):
    """Eine Position (FUND_REPORTED_HOLDING, Schlüssel ACCESSION_NUMBER + HOLDING_ID)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    quarter: str = Field(pattern=QUARTER)
    accession: str = Field(pattern=ACCESSION)
    holding_id: int = Field(ge=0)
    issuer_name: str | None = None
    issuer_lei_reported: str | None = None
    issuer_lei: str | None = Field(default=None, pattern=r"^[A-Z0-9]{18}[0-9]{2}$")
    issuer_lei_status: IdentifierStatus
    title: str | None = None
    cusip: str | None = None
    balance: float | None = None
    unit: str | None = None
    currency: str | None = None
    value: float | None = None
    exchange_rate: float | None = None
    percentage: float | None = None
    payoff_profile: str | None = None
    asset_cat: str | None = None
    issuer_type: str | None = None
    country: str | None = None
    is_restricted: bool | None = None
    fair_value_level: str | None = None
    derivative_cat: str | None = None


class NportIdentifier(BaseModel):
    """Weitere Kennungen einer Position (IDENTIFIERS, Schlüssel HOLDING_ID + IDENTIFIERS_ID)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    quarter: str = Field(pattern=QUARTER)
    holding_id: int = Field(ge=0)
    identifier_id: int = Field(ge=0)
    isin_reported: str | None = None
    isin: str | None = Field(default=None, pattern=r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
    isin_status: IdentifierStatus
    ticker: str | None = None
    other_identifier: str | None = None
    other_identifier_desc: str | None = None
