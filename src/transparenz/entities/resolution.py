"""Zuordnung von Quell-Datensätzen zu Unternehmen (Entity Resolution).

Reihenfolge und Vertrauen:
1. LEI-Treffer                         → Vertrauen hoch
2. ISIN → Wertpapier → Emittent        → Vertrauen der Wertpapier-Zuordnung
3. Eindeutiger normalisierter Name     → Vertrauen tief (zählt nie zur Bestätigung)
4. kein Treffer                        → nicht zugeordnet (wird sichtbar gemacht)
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from transparenz.entities.enums import Confidence, MappingMethod
from transparenz.entities.identifiers import normalize_company_name
from transparenz.entities.models import CompanyRecord, SecurityRecord


@dataclass(frozen=True)
class Resolution:
    company_key: str | None
    method: MappingMethod
    confidence: Confidence | None
    note: str = ""

    @property
    def resolved(self) -> bool:
        return self.company_key is not None


UNRESOLVED = Resolution(None, MappingMethod.KEINE, None, "Kein passendes Unternehmen gefunden.")


class EntityResolver:
    def __init__(
        self, companies: Iterable[CompanyRecord], securities: Iterable[SecurityRecord]
    ) -> None:
        self.companies: dict[str, CompanyRecord] = {c.company_key: c for c in companies}
        self.securities: dict[str, SecurityRecord] = {s.isin: s for s in securities}
        self._by_lei = {c.lei: c.company_key for c in self.companies.values() if c.lei}
        names: dict[str, list[str]] = defaultdict(list)
        for c in self.companies.values():
            names[normalize_company_name(c.name)].append(c.company_key)
        self._by_name = names

    def resolve_security(self, isin: str | None) -> Resolution:
        """Wertpapier → Emittent, ausschliesslich über die Wertpapier-Stammdaten."""
        if not isin:
            return Resolution(None, MappingMethod.KEINE, None, "Position ohne ISIN.")
        sec = self.securities.get(isin)
        if sec is None:
            return Resolution(None, MappingMethod.KEINE, None, "ISIN nicht in Stammdaten.")
        if sec.issuer_company_key is None or sec.issuer_company_key not in self.companies:
            return Resolution(
                None, MappingMethod.KEINE, None, f"Emittent für {isin} nicht zugeordnet."
            )
        return Resolution(
            sec.issuer_company_key,
            sec.mapping_method,
            sec.mapping_confidence,
            f"Zuordnung laut {sec.mapping_source}",
        )

    def resolve(self, name: str, lei: str | None = None, isin: str | None = None) -> Resolution:
        """Ordnet einen Quell-Datensatz (Name, ggf. LEI/ISIN) einem Unternehmen zu."""
        if lei and lei in self._by_lei:
            return Resolution(self._by_lei[lei], MappingMethod.LEI, Confidence.HOCH, "LEI-Treffer")
        if isin:
            sec_res = self.resolve_security(isin)
            if sec_res.resolved:
                return Resolution(
                    sec_res.company_key,
                    MappingMethod.ISIN,
                    sec_res.confidence,
                    f"über Wertpapier {isin}; {sec_res.note}",
                )
        candidates = self._by_name.get(normalize_company_name(name), [])
        if lei:
            # Schutz vor Fehlzuordnung: Nennt die Quelle einen LEI und hat das
            # namensgleiche Unternehmen einen ANDEREN LEI, ist es ein anderer Rechtsträger.
            conflicting = [k for k in candidates if self.companies[k].lei not in (None, lei)]
            if conflicting:
                return Resolution(
                    None,
                    MappingMethod.KEINE,
                    None,
                    f"Name passt zu {self.companies[conflicting[0]].name}, aber der LEI der "
                    "Quelle widerspricht – keine Zuordnung.",
                )
        if len(candidates) == 1:
            return Resolution(
                candidates[0],
                MappingMethod.NAME,
                Confidence.TIEF,
                "Nur Namensabgleich – Zuordnung unsicher.",
            )
        if len(candidates) > 1:
            return Resolution(
                None, MappingMethod.KEINE, None, f"Name «{name}» ist mehrdeutig."
            )
        return UNRESOLVED
