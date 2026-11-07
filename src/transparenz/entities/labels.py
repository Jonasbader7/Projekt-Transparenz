"""Deutsche Anzeigetexte für alle Aufzählungen (eine Stelle für spätere Übersetzungen)."""

from __future__ import annotations

from enum import Enum

from transparenz.entities.enums import (
    AssessmentStatus,
    AssetClass,
    CommercialUse,
    Confidence,
    DatasetKind,
    EvidenceType,
    MappingMethod,
    ProceedingStatus,
    PublisherType,
    RelationshipType,
    SourceTier,
    ThresholdCheck,
    UpdateStatus,
    VerificationLevel,
    VersionStatus,
)

# Liste statt Dict: StrEnum-Werte verschiedener Aufzählungen können gleich lauten
# («unbekannt», «nicht_anwendbar») und würden sich als Dict-Schlüssel überschreiben.
_LABEL_ITEMS: tuple[tuple[Enum, str], ...] = (
    (AssessmentStatus.FESTGESTELLT, "Gerichtlich/behördlich festgestellt"),
    (AssessmentStatus.PRUEFUNG_AUSSTEHEND, "Entscheid gemeldet – unsere Prüfung ausstehend"),
    (AssessmentStatus.VERFAHREN_LAUFEND, "Verfahren laufend (nicht entschieden)"),
    (AssessmentStatus.DOKUMENTIERT, "Dokumentiert durch NGO/Institution"),
    (AssessmentStatus.MEDIENBERICHT, "Nur Medienberichte (unbestätigt)"),
    (AssessmentStatus.ZUORDNUNG_UNSICHER, "Beleg vorhanden, Zuordnung unsicher"),
    (AssessmentStatus.KEINE_HINWEISE, "Keine Hinweise in geprüften Quellen"),
    (AssessmentStatus.UNBEKANNT, "Unbekannt (keine Datenabdeckung)"),
    (AssessmentStatus.NICHT_ANWENDBAR, "Nicht anwendbar"),
    (EvidenceType.VORWURF, "Vorwurf"),
    (EvidenceType.BEHOERDLICHE_FESTSTELLUNG, "Behördliche Feststellung"),
    (EvidenceType.GERICHTSURTEIL, "Gerichtsurteil"),
    (EvidenceType.AUSSCHLUSSENTSCHEID, "Ausschlussentscheid einer Institution"),
    (EvidenceType.UNTERNEHMENSSTELLUNGNAHME, "Unternehmensstellungnahme"),
    (EvidenceType.ABHILFE, "Abhilfemassnahme"),
    (ProceedingStatus.LAUFEND, "laufend"),
    (ProceedingStatus.ABGESCHLOSSEN, "abgeschlossen (rechtskräftig)"),
    (ProceedingStatus.UNBEKANNT, "unbekannt"),
    (ProceedingStatus.NICHT_ANWENDBAR, "–"),
    (PublisherType.GERICHT, "Gericht"),
    (PublisherType.BEHOERDE, "Behörde"),
    (PublisherType.NGO, "NGO"),
    (PublisherType.INSTITUTION, "Institution"),
    (PublisherType.MEDIEN, "Medien"),
    (PublisherType.UNTERNEHMEN, "Unternehmen (Selbstauskunft)"),
    (SourceTier.GERICHT_BEHOERDE, "Stufe 1 – Gericht/Behörde"),
    (SourceTier.NGO_INSTITUTION, "Stufe 2 – NGO/Institution mit Belegen"),
    (SourceTier.MEDIEN, "Stufe 3 – Medienbericht"),
    (SourceTier.SELBSTAUSKUNFT, "Selbstauskunft Unternehmen"),
    (VerificationLevel.UNGEPRUEFT, "ungeprüft (nur importiert)"),
    (VerificationLevel.QUELLE_GESICHTET, "Quelle gesichtet"),
    (VerificationLevel.DOKUMENT_GEPRUEFT, "Dokument geprüft"),
    (MappingMethod.LEI, "über LEI"),
    (MappingMethod.ISIN, "über ISIN"),
    (MappingMethod.NAME, "nur über Namen"),
    (MappingMethod.MANUELL, "manuell zugeordnet"),
    (MappingMethod.REGISTER, "über Register"),
    (MappingMethod.KEINE, "nicht zugeordnet"),
    (Confidence.HOCH, "hoch"),
    (Confidence.MITTEL, "mittel"),
    (Confidence.TIEF, "tief"),
    (AssetClass.AKTIE, "Aktie"),
    (AssetClass.ANLEIHE, "Anleihe"),
    (AssetClass.BARMITTEL, "Barmittel"),
    (AssetClass.DERIVAT, "Derivat"),
    (AssetClass.SONSTIGE, "Sonstige"),
    (ThresholdCheck.UEBERSCHRITTEN, "Schwellenwert erreicht/überschritten"),
    (ThresholdCheck.NICHT_UEBERSCHRITTEN, "unter Schwellenwert"),
    (ThresholdCheck.SCHWELLENWERT_OFFEN, "Schwellenwert noch nicht festgelegt"),
    (ThresholdCheck.KEINE_KENNZAHL, "keine Kennzahl"),
    (UpdateStatus.LAUFEND, "läuft"),
    (UpdateStatus.ERFOLGREICH, "erfolgreich (neuer Datenstand)"),
    (UpdateStatus.UNVERAENDERT, "erfolgreich (unverändert)"),
    (UpdateStatus.FEHLGESCHLAGEN, "fehlgeschlagen"),
    (UpdateStatus.UEBERSPRUNGEN, "übersprungen (noch nicht fällig)"),
    (UpdateStatus.GESPERRT, "gesperrt (Lizenz nicht freigegeben)"),
    (CommercialUse.JA, "ja"),
    (CommercialUse.NEIN, "nein"),
    (CommercialUse.UNKLAR, "unklar"),
    (DatasetKind.HOLDINGS, "Fondspositionen"),
    (DatasetKind.ENTITIES, "Stammdaten"),
    (DatasetKind.EVIDENCE, "Sachverhalte"),
    (DatasetKind.COVERAGE, "Abdeckung"),
    (RelationshipType.DIREKTE_MUTTER, "direkte Muttergesellschaft"),
    (RelationshipType.OBERSTE_MUTTER, "oberste Muttergesellschaft"),
    (VersionStatus.ACTIVE, "aktiv"),
    (VersionStatus.SUPERSEDED, "ersetzt"),
)


SHORT_STATUS: dict[AssessmentStatus, str] = {
    AssessmentStatus.FESTGESTELLT: "Festgestellt",
    AssessmentStatus.PRUEFUNG_AUSSTEHEND: "Prüfung ausstehend",
    AssessmentStatus.VERFAHREN_LAUFEND: "Verfahren laufend",
    AssessmentStatus.DOKUMENTIERT: "Dokumentiert (NGO/Inst.)",
    AssessmentStatus.MEDIENBERICHT: "Medienbericht",
    AssessmentStatus.ZUORDNUNG_UNSICHER: "Zuordnung unsicher",
    AssessmentStatus.KEINE_HINWEISE: "Keine Hinweise",
    AssessmentStatus.UNBEKANNT: "Unbekannt",
    AssessmentStatus.NICHT_ANWENDBAR: "–",
}

# Nachschlagen über (Typ, Wert) – eindeutig auch bei gleichlautenden Werten.
_BY_TYPE: dict[tuple[type, object], str] = {(type(k), k.value): v for k, v in _LABEL_ITEMS}


def label(value: Enum | str | None) -> str:
    """Anzeigetext für einen Aufzählungswert; unbekannte Werte werden unverändert gezeigt."""
    if value is None:
        return "–"
    if isinstance(value, Enum):
        return _BY_TYPE.get((type(value), value.value), str(value.value))
    return str(value)
