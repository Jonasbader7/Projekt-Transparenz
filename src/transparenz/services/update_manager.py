"""DataUpdateManager: kontrollierte Aktualisierung aller Datenquellen.

Ablauf pro Quelle:

1. Fälligkeit prüfen (Intervall seit letzter erfolgreicher Prüfung), ausser ``force``.
2. Abrufen mit begrenzten Wiederholungen (nur bei vorübergehenden Fehlern),
   exponentielles Warten zwischen Versuchen.
3. Neuen Datenstand erkennen: HTTP 304 bzw. identischer SHA-256-Hash → «unverändert».
4. Rohdaten als Schnappschuss ablegen (``data/raw/<quelle>/``), auch bei Fehlern
   (``data/raw/<quelle>/abgelehnt/``) – für die Nachvollziehbarkeit.
5. Parsen und validieren. Bei mindestens einem Fehler wird der GESAMTE Datenstand
   abgelehnt. Der bisherige gültige Stand bleibt unverändert aktiv.
6. In EINER Transaktion: neue Version schreiben, alte auf «superseded» setzen.
   Scheitert etwas, wird zurückgerollt – der alte Stand bleibt aktiv.
7. Jeder Versuch wird als ``UpdateRun`` protokolliert (inkl. Fehlerliste).
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from transparenz.config.catalog import Catalog, SourceConfig
from transparenz.database.models import DatasetVersion, Source, UpdateRun
from transparenz.database.writers import write_dataset
from transparenz.entities.enums import UpdateStatus, VersionStatus
from transparenz.ingestion.adapters import SourceAdapter, build_adapter
from transparenz.ingestion.fetchers import FetchError, FetchResult
from transparenz.ingestion.parsing import ParsedDataset
from transparenz.utils.timeutil import utcnow

log = logging.getLogger(__name__)

MAX_STORED_ISSUES = 200


@dataclass
class UpdateOutcome:
    source_key: str
    status: UpdateStatus
    message: str
    attempts: int = 0
    version_id: int | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class SourceFreshness:
    config: SourceConfig
    active_version: DatasetVersion | None
    last_check_at: datetime | None
    last_run: UpdateRun | None
    data_as_of: date | None
    age_days: int | None
    is_stale: bool
    next_due_at: datetime | None


class DataUpdateManager:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        catalog: Catalog,
        project_root: Path,
        raw_dir: Path,
        user_agent: str = "transparenz-research-prototype/0.1",
        adapters: dict[str, SourceAdapter] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self.session_factory = session_factory
        self.catalog = catalog
        self.project_root = project_root
        self.raw_dir = raw_dir
        self.user_agent = user_agent
        self._adapters = dict(adapters or {})
        self._sleep = sleep
        self._clock = clock

    # ----------------------------------------------------------------- helpers
    def adapter(self, key: str) -> SourceAdapter:
        if key not in self._adapters:
            cfg = self.catalog.source(key)
            self._adapters[key] = build_adapter(
                cfg, self.catalog, self.project_root, self.user_agent
            )
        return self._adapters[key]

    def _register_source(self, session: Session, cfg: SourceConfig) -> None:
        row = session.get(Source, cfg.key) or Source(key=cfg.key)
        row.name = cfg.name
        row.kind = cfg.kind.value
        row.publisher = cfg.publisher
        row.location = cfg.location
        row.license = cfg.license
        row.commercial_use = cfg.commercial_use.value
        row.is_fictional = cfg.is_fictional
        row.interval_hours = cfg.interval_hours
        row.max_age_days = cfg.max_age_days
        row.updated_at = self._clock()
        session.add(row)

    @staticmethod
    def _active_version(session: Session, key: str) -> DatasetVersion | None:
        return session.scalars(
            select(DatasetVersion).where(
                DatasetVersion.source_key == key,
                DatasetVersion.status == VersionStatus.ACTIVE.value,
            )
        ).first()

    @staticmethod
    def _last_check(session: Session, key: str) -> UpdateRun | None:
        return session.scalars(
            select(UpdateRun)
            .where(
                UpdateRun.source_key == key,
                UpdateRun.status.in_(
                    [UpdateStatus.ERFOLGREICH.value, UpdateStatus.UNVERAENDERT.value]
                ),
            )
            .order_by(UpdateRun.finished_at.desc())
        ).first()

    def _save_raw(self, key: str, content: bytes, digest: str, rejected: bool, ext: str) -> Path:
        folder = self.raw_dir / key / ("abgelehnt" if rejected else "")
        folder.mkdir(parents=True, exist_ok=True)
        stamp = self._clock().strftime("%Y%m%dT%H%M%S")
        path = folder / f"{stamp}_{digest[:12]}.{ext}"
        path.write_bytes(content)
        return path

    def _fetch_with_retries(
        self, adapter: SourceAdapter, etag: str | None, last_modified: str | None
    ) -> tuple[FetchResult | None, int, str]:
        max_attempts = self.catalog.defaults.max_attempts
        backoff = self.catalog.defaults.backoff_seconds
        last_error = ""
        for attempt in range(1, max_attempts + 1):
            try:
                return adapter.fetch(etag=etag, last_modified=last_modified), attempt, ""
            except FetchError as exc:
                last_error = str(exc)
                log.warning(
                    "Abruf %s fehlgeschlagen (Versuch %d/%d): %s",
                    adapter.config.key, attempt, max_attempts, exc,
                )
                if not exc.transient:
                    return None, attempt, last_error
                if attempt < max_attempts:
                    self._sleep(backoff * (2 ** (attempt - 1)))
        return None, max_attempts, last_error

    # --------------------------------------------------------------- öffentlich
    def run_all(self, force: bool = False, trigger: str = "manuell") -> list[UpdateOutcome]:
        outcomes = []
        for cfg in self.catalog.sources:
            if not cfg.enabled:
                continue
            outcomes.append(self.run_source(cfg.key, force=force, trigger=trigger))
        return outcomes

    def run_source(self, key: str, force: bool = False, trigger: str = "manuell") -> UpdateOutcome:
        cfg = self.catalog.source(key)
        with self.session_factory() as session:
            self._register_source(session, cfg)
            run = UpdateRun(
                source_key=key,
                trigger=trigger,
                status=UpdateStatus.LAUFEND.value,
                started_at=self._clock(),
            )
            session.add(run)
            session.commit()
            try:
                outcome = self._run(session, cfg, run, force)
            except Exception as exc:  # unerwarteter Fehler: protokollieren, alten Stand behalten
                session.rollback()
                log.exception("Unerwarteter Fehler beim Update von %s", key)
                outcome = UpdateOutcome(
                    key, UpdateStatus.FEHLGESCHLAGEN, f"Unerwarteter Fehler: {exc}",
                    attempts=run.attempts or 0, errors=[repr(exc)],
                )
            run = session.merge(run)
            run.status = outcome.status.value
            run.finished_at = self._clock()
            run.attempts = outcome.attempts
            run.message = outcome.message
            run.dataset_version_id = outcome.version_id
            run.errors_json = json.dumps(outcome.errors[:MAX_STORED_ISSUES], ensure_ascii=False)
            run.warnings_json = json.dumps(
                outcome.warnings[:MAX_STORED_ISSUES], ensure_ascii=False
            )
            session.commit()
        level = logging.ERROR if outcome.status == UpdateStatus.FEHLGESCHLAGEN else logging.INFO
        log.log(level, "Update %s: %s – %s", key, outcome.status.value, outcome.message)
        return outcome

    def _run(
        self, session: Session, cfg: SourceConfig, run: UpdateRun, force: bool
    ) -> UpdateOutcome:
        key = cfg.key
        now = self._clock()
        active = self._active_version(session, key)
        last = self._last_check(session, key)
        if not force and active is not None and last is not None and last.finished_at:
            due = last.finished_at + timedelta(hours=cfg.interval_hours)
            if now < due:
                return UpdateOutcome(
                    key, UpdateStatus.UEBERSPRUNGEN,
                    f"Noch nicht fällig (nächste Prüfung ab {due:%d.%m.%Y %H:%M} UTC).",
                )

        adapter = self.adapter(key)
        fetched, attempts, fetch_error = self._fetch_with_retries(
            adapter,
            active.etag if active else None,
            active.last_modified if active else None,
        )
        if fetched is None:
            return UpdateOutcome(
                key, UpdateStatus.FEHLGESCHLAGEN,
                f"Abruf fehlgeschlagen nach {attempts} Versuch(en). Bisheriger Stand bleibt aktiv.",
                attempts=attempts, errors=[fetch_error],
            )
        if fetched.not_modified:
            return UpdateOutcome(
                key, UpdateStatus.UNVERAENDERT, "Quelle meldet keinen neuen Datenstand (HTTP 304).",
                attempts=attempts, version_id=active.id if active else None,
            )
        content = fetched.content or b""
        digest = hashlib.sha256(content).hexdigest()
        run.content_hash = digest
        if active is not None and active.content_hash == digest:
            return UpdateOutcome(
                key, UpdateStatus.UNVERAENDERT, "Inhalt identisch mit aktivem Datenstand.",
                attempts=attempts, version_id=active.id,
            )

        parsed: ParsedDataset = adapter.parse(content)
        errors = [str(i) for i in parsed.errors]
        warnings = [str(i) for i in parsed.warnings]
        if not parsed.is_valid:
            raw = self._save_raw(key, content, digest, rejected=True, ext=cfg.format)
            run.raw_path = str(raw)
            return UpdateOutcome(
                key, UpdateStatus.FEHLGESCHLAGEN,
                f"Validierung fehlgeschlagen ({len(errors)} Fehler). "
                "Datenstand abgelehnt, bisheriger Stand bleibt aktiv.",
                attempts=attempts, errors=errors, warnings=warnings,
            )

        raw = self._save_raw(key, content, digest, rejected=False, ext=cfg.format)
        run.raw_path = str(raw)
        try:
            version = DatasetVersion(
                source_key=key,
                status=VersionStatus.ACTIVE.value,
                content_hash=digest,
                fetched_at=now,
                activated_at=now,
                record_count=parsed.record_count,
                warning_count=len(warnings),
                data_as_of=parsed.data_as_of,
                raw_path=str(raw),
                etag=fetched.etag,
                last_modified=fetched.last_modified,
            )
            if active is not None:
                active.status = VersionStatus.SUPERSEDED.value
                active.superseded_at = now
                session.flush()
            session.add(version)
            session.flush()
            write_dataset(session, version.id, parsed)
            session.commit()
        except Exception as exc:
            session.rollback()
            log.exception("Schreiben von %s fehlgeschlagen – Rollback", key)
            return UpdateOutcome(
                key, UpdateStatus.FEHLGESCHLAGEN,
                f"Schreiben fehlgeschlagen, Rollback ausgeführt: {exc}",
                attempts=attempts, errors=[repr(exc)], warnings=warnings,
            )
        return UpdateOutcome(
            key, UpdateStatus.ERFOLGREICH,
            f"Neuer Datenstand mit {parsed.record_count} Datensätzen aktiviert"
            + (f" ({len(warnings)} Warnungen)." if warnings else "."),
            attempts=attempts, version_id=version.id, warnings=warnings,
        )

    def validate_source(self, key: str) -> ParsedDataset:
        """Trockenlauf: abrufen und validieren, nichts schreiben."""
        adapter = self.adapter(key)
        fetched = adapter.fetch()
        return adapter.parse(fetched.content or b"")

    def freshness(self) -> list[SourceFreshness]:
        now = self._clock()
        out = []
        with self.session_factory() as session:
            for cfg in self.catalog.sources:
                active = self._active_version(session, cfg.key)
                last_check = self._last_check(session, cfg.key)
                last_run = session.scalars(
                    select(UpdateRun)
                    .where(UpdateRun.source_key == cfg.key)
                    .order_by(UpdateRun.started_at.desc(), UpdateRun.id.desc())
                ).first()
                as_of = None
                age = None
                if active is not None:
                    as_of = active.data_as_of or active.fetched_at.date()
                    age = (now.date() - as_of).days
                check_at = last_check.finished_at if last_check else None
                out.append(
                    SourceFreshness(
                        config=cfg,
                        active_version=active,
                        last_check_at=check_at,
                        last_run=last_run,
                        data_as_of=as_of,
                        age_days=age,
                        is_stale=active is None or (age is not None and age > cfg.max_age_days),
                        next_due_at=(check_at + timedelta(hours=cfg.interval_hours))
                        if check_at else None,
                    )
                )
        return out
