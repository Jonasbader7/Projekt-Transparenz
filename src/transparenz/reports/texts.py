"""Quellenbasierte Formulierungen.

Regel: Wir urteilen nie selbst. Jede Aussage nennt Art, Herausgeber und Datum der
Quelle («Laut Gerichtsurteil … vom …»). Vorwürfe werden als Vorwürfe bezeichnet.
"""

from __future__ import annotations

from transparenz.entities.enums import AssessmentStatus, EvidenceType
from transparenz.entities.labels import label
from transparenz.screening.engine import CriterionAssessment, EvidenceMatch
from transparenz.utils.timeutil import format_date, format_datetime


def finding_sentence(m: EvidenceMatch) -> str:
    r = m.record
    when = format_date(r.published_date)
    who = r.publisher
    match r.evidence_type:
        case EvidenceType.GERICHTSURTEIL:
            prefix = f"Laut Gerichtsurteil ({who}, {when})"
        case EvidenceType.BEHOERDLICHE_FESTSTELLUNG:
            prefix = f"Laut behördlicher Feststellung ({who}, {when})"
        case EvidenceType.AUSSCHLUSSENTSCHEID:
            prefix = f"Laut Ausschlussentscheid ({who}, {when})"
        case EvidenceType.UNTERNEHMENSSTELLUNGNAHME:
            prefix = f"Laut Stellungnahme des Unternehmens ({who}, {when})"
        case EvidenceType.ABHILFE:
            prefix = f"Laut Angaben zu Abhilfemassnahmen ({who}, {when})"
        case _:
            prefix = f"Vorwurf laut {label(r.publisher_type)} «{who}» ({when}) – nicht bestätigt"
    text = f"{prefix}: {r.description}"
    if r.metric_name and r.metric_value is not None:
        text += f" Gemeldete Kennzahl: {r.metric_name} = {r.metric_value:g} {r.metric_unit or ''}."
    if m.via_parent is not None:
        text += f" (Betrifft die Muttergesellschaft {m.via_parent.name}.)"
    return text.strip()


def provenance(m: EvidenceMatch, source_names: dict[str, str] | None = None) -> str:
    """Herkunft im eigenen System: welcher Datenstand liegt der Anzeige zugrunde."""
    ev = m.evidence
    name = (source_names or {}).get(ev.source_key, ev.source_key)
    parts = [f"Datenquelle: {name}"]
    if ev.version_id is not None:
        parts.append(f"Version #{ev.version_id}")
    if ev.version_hash:
        parts.append(f"Hash {ev.version_hash[:10]}")
    if ev.imported_at is not None:
        parts.append(f"importiert {format_datetime(ev.imported_at)}")
    parts.append(f"Datensatz {m.record.evidence_id}")
    return " · ".join(parts)


def _names(names: list[str]) -> str:
    return "; ".join(names)


def status_explanation(a: CriterionAssessment) -> str:
    d = a.decisive
    match a.status:
        case AssessmentStatus.FESTGESTELLT:
            assert d is not None
            return (
                f"{label(d.record.evidence_type)} ({d.record.publisher}, "
                f"{format_date(d.record.published_date)}), Verfahren rechtskräftig "
                "abgeschlossen, Originaldokument von uns geprüft."
            )
        case AssessmentStatus.PRUEFUNG_AUSSTEHEND:
            assert d is not None
            return (
                f"{label(d.record.evidence_type)} ({d.record.publisher}, "
                f"{format_date(d.record.published_date)}) als abgeschlossen gemeldet; "
                "unsere Prüfung des Originaldokuments steht aus."
            )
        case AssessmentStatus.VERFAHREN_LAUFEND:
            assert d is not None
            return f"Verfahren bei {d.record.publisher} – kein abschliessender Entscheid."
        case AssessmentStatus.DOKUMENTIERT:
            return (
                "Vorwurf bzw. Einschätzung von NGO/Institution mit Belegen "
                f"({_names(a.independent_publishers)}) – keine gerichtliche Feststellung."
            )
        case AssessmentStatus.MEDIENBERICHT:
            return (
                f"Nur Medienberichte ({_names(a.independent_publishers)}) – "
                "unbestätigter Vorwurf."
            )
        case AssessmentStatus.ZUORDNUNG_UNSICHER:
            return "Es gibt Belege, aber die Zuordnung zu diesem Unternehmen ist nicht gesichert."
        case AssessmentStatus.KEINE_HINWEISE:
            return f"Geprüft durch: {_names(a.covered_by)} – dort keine Hinweise gefunden."
        case AssessmentStatus.UNBEKANNT:
            return (
                "Keine der angebundenen Quellen hat dieses Unternehmen für dieses Kriterium "
                "geprüft. Das ist KEIN Hinweis auf Unbedenklichkeit."
            )
        case _:
            return "Für diese Anlageklasse nicht anwendbar."
