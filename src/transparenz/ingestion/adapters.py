"""Ein Adapter pro Quelle: verbindet Abruf (Fetcher) und Parser mit den Quellen-Metadaten."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from transparenz.config.catalog import Catalog, SourceConfig
from transparenz.ingestion.fetchers import Fetcher, FetchResult, HttpFetcher, LocalFileFetcher
from transparenz.ingestion.gleif import GLEIF_PARSERS, GleifApiFetcher
from transparenz.ingestion.parsing import PARSERS, ParsedDataset

ALL_PARSERS = {**PARSERS, **GLEIF_PARSERS}


@dataclass
class SourceAdapter:
    config: SourceConfig
    fetcher: Fetcher
    criteria_keys: set[str]

    def fetch(self, etag: str | None = None, last_modified: str | None = None) -> FetchResult:
        return self.fetcher.fetch(etag=etag, last_modified=last_modified)

    def parse(self, content: bytes) -> ParsedDataset:
        parser = ALL_PARSERS.get((self.config.kind, self.config.format))
        if parser is None:
            raise ValueError(
                f"Kein Parser für {self.config.kind}/{self.config.format} ({self.config.key})."
            )
        return parser(content, self.criteria_keys)


def build_adapter(
    config: SourceConfig,
    catalog: Catalog,
    project_root: Path,
    user_agent: str,
) -> SourceAdapter:
    fetcher: Fetcher
    if config.fetcher == "local":
        path = Path(config.location)
        fetcher = LocalFileFetcher(path if path.is_absolute() else project_root / path)
    elif config.fetcher == "gleif_api":
        assert config.lei_list is not None  # durch SourceConfig geprüft
        lei_list = Path(config.lei_list)
        fetcher = GleifApiFetcher(
            lei_list if lei_list.is_absolute() else project_root / lei_list,
            base_url=config.location,
            timeout=catalog.defaults.http_timeout_seconds,
            user_agent=user_agent,
        )
    else:
        fetcher = HttpFetcher(
            config.location,
            timeout=catalog.defaults.http_timeout_seconds,
            user_agent=user_agent,
        )
    return SourceAdapter(config=config, fetcher=fetcher, criteria_keys=catalog.criterion_keys)
