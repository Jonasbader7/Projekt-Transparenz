"""Abrufen von Rohdaten: lokale Datei oder HTTP.

Fehler werden als ``FetchError`` gemeldet. ``transient=True`` bedeutet: ein erneuter
Versuch kann helfen (Zeitüberschreitung, 5xx, 429). Dauerhafte Fehler (Datei fehlt,
404, 403) werden nicht wiederholt.

Der HTTP-Abruf nutzt bedingte Anfragen (ETag / Last-Modified), um unveränderte
Datenstände ohne erneuten Download zu erkennen. Er respektiert keine Umgehung von
Zugangsbeschränkungen: 401/403 werden als dauerhafter Fehler gemeldet.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx

log = logging.getLogger(__name__)


class FetchError(Exception):
    def __init__(self, message: str, *, transient: bool) -> None:
        super().__init__(message)
        self.transient = transient


@dataclass(frozen=True)
class FetchResult:
    origin: str
    content: bytes | None
    not_modified: bool = False
    etag: str | None = None
    last_modified: str | None = None


class Fetcher(Protocol):
    def fetch(self, etag: str | None = None, last_modified: str | None = None) -> FetchResult: ...


class LocalFileFetcher:
    def __init__(self, path: Path) -> None:
        self.path = path

    def fetch(self, etag: str | None = None, last_modified: str | None = None) -> FetchResult:
        try:
            content = self.path.read_bytes()
        except FileNotFoundError as exc:
            raise FetchError(f"Datei nicht gefunden: {self.path}", transient=False) from exc
        except IsADirectoryError as exc:
            raise FetchError(f"Pfad ist ein Ordner: {self.path}", transient=False) from exc
        except OSError as exc:
            raise FetchError(f"Datei nicht lesbar: {self.path} ({exc})", transient=True) from exc
        return FetchResult(origin=str(self.path), content=content)


class HttpFetcher:
    def __init__(
        self,
        url: str,
        *,
        timeout: float,
        user_agent: str,
        client: httpx.Client | None = None,
    ) -> None:
        self.url = url
        self.timeout = timeout
        self.user_agent = user_agent
        self._client = client

    def fetch(self, etag: str | None = None, last_modified: str | None = None) -> FetchResult:
        headers = {"User-Agent": self.user_agent}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        client = self._client or httpx.Client(timeout=self.timeout, follow_redirects=True)
        try:
            response = client.get(self.url, headers=headers)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise FetchError(f"Netzwerkfehler bei {self.url}: {exc}", transient=True) from exc
        finally:
            if self._client is None:
                client.close()

        status = response.status_code
        if status == 304:
            return FetchResult(
                origin=self.url, content=None, not_modified=True, etag=etag,
                last_modified=last_modified,
            )
        if status == 429 or status >= 500:
            raise FetchError(f"HTTP {status} bei {self.url}", transient=True)
        if status >= 400:
            raise FetchError(f"HTTP {status} bei {self.url}", transient=False)
        return FetchResult(
            origin=self.url,
            content=response.content,
            etag=response.headers.get("ETag"),
            last_modified=response.headers.get("Last-Modified"),
        )
