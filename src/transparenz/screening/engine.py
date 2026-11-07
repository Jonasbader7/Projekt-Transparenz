"""Screening-Engine gemäss Belegmodell (docs/methodik/validierung.md).

Grundsätze, die hier im Code umgesetzt sind:

* **Kein Gesamtscore.** Jedes Kriterium wird pro Position einzeln beurteilt; es gibt
  keine Verrechnung zwischen Kriterien.
* **Beweisstatus statt Quellenanzahl.** Der Status ergibt sich aus dem stärksten
  sicher zugeordneten Beleg:

  ===================  =====================================================
  festgestellt         Gerichtsurteil/behördliche Feststellung, rechtskräftig
                       abgeschlossen, Originaldokument von uns geprüft
  pruefung_ausstehend  wie oben, aber unsere Dokumentprüfung fehlt noch
  verfahren_laufend    Gericht/Behörde, Verfahren laufend oder Status unbekannt
  dokumentiert         NGO-Recherche mit Belegen / Ausschlussentscheid Institution
  medienbericht        nur Medienberichte – mehrere Artikel heben die Stufe NICHT an
  zuordnung_unsicher   Belege vorhanden, Zuordnung zum Unternehmen unsicher
  ===================  =====================================================

  Unabhängige Herausgeber werden gezählt und angezeigt (Kontext), ändern die Stufe
  aber nicht: Zwei Artikel, die denselben Vorwurf wiederholen, sind kein Beweis.
* **Automatisierung bestätigt nichts.** «festgestellt» setzt voraus, dass ein Mensch
  das Originaldokument geprüft hat (``verification_level = dokument_geprueft``).
  Neu importierte Datensätze sind ``ungeprueft``.
* Stellungnahmen und Abhilfemassnahmen werden angezeigt, entkräften aber nichts.
* Fehlende Daten sind «unbekannt», nicht «unauffällig». «Keine Hinweise» gibt es
  nur, wenn eine Quelle das Unternehmen für das Kriterium nachweislich geprüft hat.
* Belege zu einer Muttergesellschaft werden nur über VERIFIZIERTE Konzernbeziehungen
  übernommen. Unverifizierte Beziehungen werden angezeigt, aber nicht übernommen.

Die Engine ist rein funktional (keine Datenbank, keine Uhr): alle Eingaben werden
übergeben. Das macht sie deterministisch und testbar.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta

from transparenz.config.catalog import Criterion
from transparenz.entities.enums import (
    CONFIDENCE_RANK,
    CONTEXT_EVIDENCE_TYPES,
    FINDING_STATUSES,
    STATUS_DISPLAY_ORDER,
    SUPPORTING_EVIDENCE_TYPES,
    AssessmentStatus,
    AssetClass,
    Confidence,
    EvidenceType,
    MappingMethod,
    ProceedingStatus,
    SourceTier,
    ThresholdCheck,
    VerificationLevel,
)
from transparenz.entities.identifiers import normalize_publisher
from transparenz.entities.models import (
    CompanyRecord,
    EvidenceRecord,
    FundInfo,
    Position,
    RelationshipRecord,
    SecurityRecord,
    SourcedCoverage,
    SourcedEvidence,
)
from transparenz.entities.resolution import EntityResolver, Resolution

MIN_CONFIDENCE = Confidence.MITTEL
SCREENABLE_ASSET_CLASSES = frozenset({AssetClass.AKTIE, AssetClass.ANLEIHE})
REVIEW_MAX_AGE = timedelta(days=365)
_FORMAL_TYPES = frozenset({EvidenceType.GERICHTSURTEIL, EvidenceType.BEHOERDLICHE_FESTSTELLUNG})


def _is_confident(conf: Confidence | None) -> bool:
    return conf is not None and CONFIDENCE_RANK[conf] >= CONFIDENCE_RANK[MIN_CONFIDENCE]


def evidence_level(record: EvidenceRecord) -> AssessmentStatus:
    """Stufe, die ein einzelner (sicher zugeordneter) stützender Beleg begründet."""
    if record.evidence_type in _FORMAL_TYPES:
        if record.proceeding_status == ProceedingStatus.ABGESCHLOSSEN:
            if record.verification_level == VerificationLevel.DOKUMENT_GEPRUEFT:
                return AssessmentStatus.FESTGESTELLT
            return AssessmentStatus.PRUEFUNG_AUSSTEHEND
        return AssessmentStatus.VERFAHREN_LAUFEND
    if record.tier == SourceTier.GERICHT_BEHOERDE:
        # z. B. Anklage oder Untersuchung einer Behörde (Art «vorwurf»)
        return AssessmentStatus.VERFAHREN_LAUFEND
    if record.tier == SourceTier.NGO_INSTITUTION:
        return AssessmentStatus.DOKUMENTIERT
    return AssessmentStatus.MEDIENBERICHT


@dataclass(frozen=True)
class EvidenceMatch:
    evidence: SourcedEvidence
    resolution: Resolution
    matched_company: CompanyRecord
    via_parent: CompanyRecord | None
    threshold_check: ThresholdCheck

    @property
    def record(self) -> EvidenceRecord:
        return self.evidence.record

    @property
    def source_key(self) -> str:
        return self.evidence.source_key

    @property
    def tier(self) -> SourceTier:
        return self.record.tier

    @property
    def confident(self) -> bool:
        return _is_confident(self.resolution.confidence)

    @property
    def level(self) -> AssessmentStatus:
        return evidence_level(self.record)


@dataclass
class CriterionAssessment:
    criterion: Criterion
    status: AssessmentStatus
    supporting: list[EvidenceMatch] = field(default_factory=list)
    context: list[EvidenceMatch] = field(default_factory=list)
    not_counted: list[EvidenceMatch] = field(default_factory=list)
    unverified_parent_evidence: list[EvidenceMatch] = field(default_factory=list)
    independent_publishers: list[str] = field(default_factory=list)
    covered_by: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    decisive: EvidenceMatch | None = None  # stärkster sicher zugeordneter Beleg

    @property
    def has_finding(self) -> bool:
        return self.status in FINDING_STATUSES


@dataclass
class PositionResult:
    position: Position
    applicable: bool
    company: CompanyRecord | None
    issuer_resolution: Resolution
    verified_parents: list[CompanyRecord] = field(default_factory=list)
    unverified_parents: list[tuple[CompanyRecord, RelationshipRecord]] = field(
        default_factory=list
    )
    assessments: dict[str, CriterionAssessment] = field(default_factory=dict)

    def statuses(self) -> list[AssessmentStatus]:
        return [a.status for a in self.assessments.values()]

    @property
    def strongest_status(self) -> AssessmentStatus:
        """Stärkster Beweisstatus über alle Kriterien – nur zur Sortierung/Anzeige."""
        return min(self.statuses(), key=lambda s: STATUS_DISPLAY_ORDER[s])

    @property
    def has_finding(self) -> bool:
        return any(a.has_finding for a in self.assessments.values())


@dataclass
class CriterionSummary:
    criterion: Criterion
    weight_by_status: dict[AssessmentStatus, float]
    count_by_status: dict[AssessmentStatus, int]


@dataclass
class FundScreeningResult:
    fund: FundInfo
    as_of: date
    criteria: list[Criterion]
    positions: list[PositionResult]
    summaries: dict[str, CriterionSummary]
    unresolved_evidence: list[tuple[SourcedEvidence, Resolution]]
    low_confidence_mappings: list[PositionResult]

    @property
    def total_weight(self) -> float:
        return sum(p.position.weight_pct for p in self.positions)

    @property
    def screenable_weight(self) -> float:
        return sum(p.position.weight_pct for p in self.positions if p.applicable)

    @property
    def unidentified_weight(self) -> float:
        return sum(
            p.position.weight_pct for p in self.positions if p.applicable and p.company is None
        )

    def weight_with_status(self, status: AssessmentStatus) -> float:
        """Gewicht der Positionen mit mind. einem Kriterium in diesem Status."""
        return sum(
            p.position.weight_pct
            for p in self.positions
            if p.applicable and status in p.statuses()
        )

    @property
    def weight_with_finding(self) -> float:
        return sum(p.position.weight_pct for p in self.positions if p.has_finding)


def _threshold_check(criterion: Criterion, record: EvidenceRecord) -> ThresholdCheck:
    if criterion.metric is None or record.metric_name != criterion.metric:
        return ThresholdCheck.KEINE_KENNZAHL
    if record.metric_value is None:
        return ThresholdCheck.KEINE_KENNZAHL
    if criterion.threshold is None:
        return ThresholdCheck.SCHWELLENWERT_OFFEN
    if record.metric_value >= criterion.threshold:
        return ThresholdCheck.UEBERSCHRITTEN
    return ThresholdCheck.NICHT_UEBERSCHRITTEN


class ScreeningEngine:
    def __init__(
        self,
        criteria: Sequence[Criterion],
        companies: Iterable[CompanyRecord],
        securities: Iterable[SecurityRecord],
        relationships: Iterable[RelationshipRecord],
        evidence: Iterable[SourcedEvidence],
        coverage: Iterable[SourcedCoverage],
        source_names: dict[str, str] | None = None,
    ) -> None:
        self.criteria = list(criteria)
        self.resolver = EntityResolver(companies, securities)
        self.source_names = source_names or {}
        self._parents: dict[str, list[RelationshipRecord]] = defaultdict(list)
        for rel in relationships:
            self._parents[rel.child_key].append(rel)

        # Sachverhalte einmal zuordnen
        self._evidence_by_company: dict[str, list[tuple[SourcedEvidence, Resolution]]] = (
            defaultdict(list)
        )
        self.unresolved_evidence: list[tuple[SourcedEvidence, Resolution]] = []
        for ev in evidence:
            res = self.resolver.resolve(ev.record.company_name, ev.record.lei, ev.record.isin)
            if res.company_key is None:
                self.unresolved_evidence.append((ev, res))
            else:
                self._evidence_by_company[res.company_key].append((ev, res))

        # Abdeckung: (company_key, criterion) -> prüfende Quellen
        self._coverage: dict[tuple[str, str], set[str]] = defaultdict(set)
        for cov in coverage:
            res = self.resolver.resolve(cov.record.company_name, cov.record.lei, cov.record.isin)
            if res.company_key is None or not _is_confident(res.confidence):
                continue  # unsichere Abdeckung darf kein «keine Hinweise» begründen
            label = self.source_names.get(cov.covers_source_key or cov.source_key, cov.source_key)
            self._coverage[(res.company_key, cov.record.criterion)].add(label)

    # ------------------------------------------------------------------ Konzern
    def _ancestors(
        self, company_key: str
    ) -> tuple[list[CompanyRecord], list[tuple[CompanyRecord, RelationshipRecord]]]:
        verified: list[CompanyRecord] = []
        unverified: list[tuple[CompanyRecord, RelationshipRecord]] = []
        seen = {company_key}
        stack = [company_key]
        while stack:
            current = stack.pop()
            for rel in self._parents.get(current, []):
                parent = self.resolver.companies.get(rel.parent_key)
                if parent is None or rel.parent_key in seen:
                    continue
                seen.add(rel.parent_key)
                if rel.verified:
                    verified.append(parent)
                    stack.append(rel.parent_key)
                else:
                    unverified.append((parent, rel))
        return verified, unverified

    # ------------------------------------------------------------- Bewertung
    def _matches(
        self, company: CompanyRecord, via_parent: CompanyRecord | None, criterion: Criterion
    ) -> list[EvidenceMatch]:
        target = via_parent or company
        out = []
        for ev, res in self._evidence_by_company.get(target.company_key, []):
            if ev.record.criterion != criterion.key:
                continue
            out.append(
                EvidenceMatch(
                    evidence=ev,
                    resolution=res,
                    matched_company=target,
                    via_parent=via_parent,
                    threshold_check=_threshold_check(criterion, ev.record),
                )
            )
        return out

    def assess(
        self,
        criterion: Criterion,
        company: CompanyRecord,
        verified_parents: list[CompanyRecord],
        unverified_parents: list[tuple[CompanyRecord, RelationshipRecord]],
        issuer_confidence: Confidence | None,
        as_of: date,
    ) -> CriterionAssessment:
        matches = self._matches(company, None, criterion)
        for parent in verified_parents:
            matches.extend(self._matches(company, parent, criterion))

        a = CriterionAssessment(criterion=criterion, status=AssessmentStatus.UNBEKANNT)
        for m in matches:
            if m.record.evidence_type in CONTEXT_EVIDENCE_TYPES:
                a.context.append(m)
            elif (
                m.record.evidence_type not in SUPPORTING_EVIDENCE_TYPES
                or m.tier == SourceTier.SELBSTAUSKUNFT
                or m.threshold_check == ThresholdCheck.NICHT_UEBERSCHRITTEN
            ):
                a.not_counted.append(m)
            else:
                a.supporting.append(m)

        for parent, _rel in unverified_parents:
            for m in self._matches(company, parent, criterion):
                if m.record.evidence_type in SUPPORTING_EVIDENCE_TYPES:
                    a.unverified_parent_evidence.append(m)

        covered: set[str] = set()
        for key in [company.company_key, *(p.company_key for p in verified_parents)]:
            covered |= self._coverage.get((key, criterion.key), set())
        # Eine Kennzahl unter dem Schwellenwert belegt ebenfalls eine Prüfung.
        covered |= {
            self.source_names.get(m.source_key, m.source_key)
            for m in a.not_counted
            if m.threshold_check == ThresholdCheck.NICHT_UEBERSCHRITTEN and m.confident
        }
        a.covered_by = sorted(covered)

        issuer_confident = _is_confident(issuer_confidence)
        usable = [m for m in a.supporting if m.confident and issuer_confident]
        a.independent_publishers = sorted(
            {normalize_publisher(m.record.publisher): m.record.publisher for m in usable}.values()
        )

        if usable:
            a.decisive = min(
                usable,
                key=lambda m: (STATUS_DISPLAY_ORDER[m.level], -m.record.published_date.toordinal()),
            )
            a.status = a.decisive.level
        elif a.supporting:
            a.status = AssessmentStatus.ZUORDNUNG_UNSICHER
        else:
            a.status = AssessmentStatus.KEINE_HINWEISE if covered else AssessmentStatus.UNBEKANNT

        a.flags = self._flags(a, issuer_confident, as_of)
        return a

    def _flags(self, a: CriterionAssessment, issuer_confident: bool, as_of: date) -> list[str]:
        flags: list[str] = []
        parents = sorted({m.via_parent.name for m in a.supporting if m.via_parent})
        if parents:
            flags.append(
                "Beleg betrifft die Muttergesellschaft "
                f"{', '.join(parents)} (verifizierte Konzernbeziehung)."
            )
        if any(not m.confident for m in a.supporting):
            flags.append(
                "Mindestens ein Beleg ist nur über den Namen zugeordnet – er bestimmt den "
                "Status nicht."
            )
        if a.supporting and not issuer_confident:
            flags.append("Zuordnung Wertpapier → Unternehmen ist unsicher.")
        if a.status == AssessmentStatus.PRUEFUNG_AUSSTEHEND:
            flags.append(
                "Ein abgeschlossenes Verfahren ist gemeldet, das Originaldokument wurde von uns "
                "aber noch nicht geprüft. Bis dahin gilt es nicht als festgestellt."
            )
        if any(
            m.record.evidence_type in _FORMAL_TYPES
            and m.record.proceeding_status == ProceedingStatus.UNBEKANNT
            for m in a.supporting
        ):
            flags.append("Verfahrensstatus unbekannt – wird wie ein laufendes Verfahren behandelt.")
        if a.status in {AssessmentStatus.DOKUMENTIERT, AssessmentStatus.MEDIENBERICHT}:
            flags.append(
                "Es handelt sich um Vorwürfe bzw. Einschätzungen Dritter, nicht um eine "
                "gerichtliche oder behördliche Feststellung."
            )
        if len(a.independent_publishers) >= 2:
            flags.append(
                f"Berichtet von {len(a.independent_publishers)} verschiedenen Herausgebern "
                "(Kontext – ändert den Beweisstatus nicht)."
            )
        if any(m.threshold_check == ThresholdCheck.SCHWELLENWERT_OFFEN for m in a.supporting):
            flags.append(
                "Kennzahl gemeldet, Schwellenwert aber noch nicht festgelegt – "
                "jede gemeldete Beteiligung wird vorerst angezeigt."
            )
        if any(m.threshold_check == ThresholdCheck.NICHT_UEBERSCHRITTEN for m in a.not_counted):
            flags.append("Gemeldete Kennzahl liegt unter dem festgelegten Schwellenwert.")
        types = {m.record.evidence_type for m in a.context}
        if EvidenceType.UNTERNEHMENSSTELLUNGNAHME in types:
            flags.append("Das Unternehmen hat Stellung genommen (siehe Belege).")
        if EvidenceType.ABHILFE in types:
            flags.append(
                "Abhilfemassnahmen sind dokumentiert – sie werden angezeigt, aber nicht verrechnet."
            )
        stale = [
            m for m in a.supporting
            if m.record.last_reviewed is not None
            and as_of - m.record.last_reviewed > REVIEW_MAX_AGE
        ]
        if stale:
            flags.append(f"{len(stale)} Beleg(e) seit über 12 Monaten nicht mehr überprüft.")
        never = [
            m for m in a.supporting
            if m.record.last_reviewed is None
            and m.record.verification_level != VerificationLevel.UNGEPRUEFT
        ]
        if never:
            flags.append(f"{len(never)} Beleg(e) ohne Datum der letzten Überprüfung.")
        unverified = [m for m in a.supporting if m.record.verification_level
                      == VerificationLevel.UNGEPRUEFT]
        if unverified:
            flags.append(f"{len(unverified)} Beleg(e) noch ungeprüft (nur importiert).")
        if a.unverified_parent_evidence:
            names = sorted({m.matched_company.name for m in a.unverified_parent_evidence})
            flags.append(
                f"Für die mögliche Muttergesellschaft {', '.join(names)} liegen Belege vor. "
                "Die Konzernbeziehung ist nicht verifiziert – Belege werden nicht übernommen."
            )
        return flags

    # --------------------------------------------------------------- Fonds
    def screen_position(self, position: Position, as_of: date) -> PositionResult:
        if position.asset_class not in SCREENABLE_ASSET_CLASSES:
            res = Resolution(
                None, MappingMethod.KEINE, None, "Anlageklasse wird nicht nach Emittent geprüft."
            )
            result = PositionResult(position, applicable=False, company=None, issuer_resolution=res)
            for c in self.criteria:
                result.assessments[c.key] = CriterionAssessment(c, AssessmentStatus.NICHT_ANWENDBAR)
            return result

        res = self.resolver.resolve_security(position.isin)
        company = self.resolver.companies.get(res.company_key) if res.company_key else None
        result = PositionResult(position, applicable=True, company=company, issuer_resolution=res)
        if company is None:
            for c in self.criteria:
                a = CriterionAssessment(c, AssessmentStatus.UNBEKANNT)
                a.flags.append(f"Emittent nicht identifiziert: {res.note}")
                result.assessments[c.key] = a
            return result

        verified, unverified = self._ancestors(company.company_key)
        result.verified_parents = verified
        result.unverified_parents = unverified
        for c in self.criteria:
            result.assessments[c.key] = self.assess(
                c, company, verified, unverified, res.confidence, as_of
            )
        return result

    def screen_fund(
        self, fund: FundInfo, positions: Sequence[Position], as_of: date
    ) -> FundScreeningResult:
        results = [self.screen_position(p, as_of) for p in positions]
        summaries: dict[str, CriterionSummary] = {}
        for c in self.criteria:
            weights = dict.fromkeys(AssessmentStatus, 0.0)
            counts = dict.fromkeys(AssessmentStatus, 0)
            for r in results:
                status = r.assessments[c.key].status
                weights[status] += r.position.weight_pct
                counts[status] += 1
            summaries[c.key] = CriterionSummary(c, weights, counts)
        low_conf = [
            r for r in results
            if r.company is not None and not _is_confident(r.issuer_resolution.confidence)
        ]
        results.sort(
            key=lambda r: (STATUS_DISPLAY_ORDER[r.strongest_status], -r.position.weight_pct)
        )
        return FundScreeningResult(
            fund=fund,
            as_of=as_of,
            criteria=self.criteria,
            positions=results,
            summaries=summaries,
            unresolved_evidence=list(self.unresolved_evidence),
            low_confidence_mappings=low_conf,
        )
