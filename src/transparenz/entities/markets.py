"""Validated source observations; registrant, fund series and class stay distinct."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MarketObservation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    record_type: Literal["listed_ticker", "fund_class", "ncen_fund", "ncen_class"]
    record_key: str = Field(min_length=1, max_length=255)
    cik: str = Field(pattern=r"^\d{10}$")
    series_id: str | None = Field(default=None, pattern=r"^S\d{9}$")
    class_id: str | None = Field(default=None, pattern=r"^C\d{9}$")
    reported_series_id: str | None = None
    reported_class_id: str | None = None
    name: str | None = None
    class_name: str | None = None
    ticker: str | None = None
    exchange: str | None = None
    fund_id: str | None = None
    accession: str | None = Field(default=None, pattern=r"^\d{10}-\d{2}-\d{6}$")
    report_date: date | None = None
    filing_date: date | None = None
    series_is_etf: bool | None = None
    series_is_etmf: bool | None = None
    source_url: str
    original_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
