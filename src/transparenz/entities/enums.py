"""Aufzählungen des Belegmodells. Werte sind stabile Schlüssel (ASCII),
die deutschen Anzeigetexte stehen in ``transparenz.entities.labels``."""

from __future__ import annotations

from enum import IntEnum, StrEnum


class DatasetKind(StrEnum):
    HOLDINGS = "holdings"
    ENTITIES = "entities"
    EVIDENCE = "evidence"
    COVERAGE = "coverage"


class AssetClass(StrEnum):
    AKTIE = "aktie"
    ANLEIHE = "anleihe"
    BARMITTEL = "barmittel"
    DERIVAT = "derivat"
    SONSTIGE = "sonstige"


class EvidenceType(StrEnum):
    """Art eines Sachverhalts."""

    VORWURF = "vorwurf"
    BEHOERDLICHE_FESTSTELLUNG = "behoerdliche_feststellung"
    GERICHTSURTEIL = "gerichtsurteil"
    AUSSCHLUSSENTSCHEID = "ausschlussentscheid"
    UNTERNEHMENSSTELLUNGNAHME = "unternehmensstellungnahme"
    ABHILFE = "abhilfe"


# Arten, die einen möglichen Verstoss stützen. Stellungnahmen und Abhilfe sind
# Kontext: Sie werden angezeigt, verrechnen oder entkräften aber nichts.
SUPPORTING_EVIDENCE_TYPES: frozenset[EvidenceType] = frozenset(
    {
        EvidenceType.VORWURF,
        EvidenceType.BEHOERDLICHE_FESTSTELLUNG,
        EvidenceType.GERICHTSURTEIL,
        EvidenceType.AUSSCHLUSSENTSCHEID,
    }
)
CONTEXT_EVIDENCE_TYPES: frozenset[EvidenceType] = frozenset(
    {EvidenceType.UNTERNEHMENSSTELLUNGNAHME, EvidenceType.ABHILFE}
)


class ProceedingStatus(StrEnum):
    LAUFEND = "laufend"
    ABGESCHLOSSEN = "abgeschlossen"
    UNBEKANNT = "unbekannt"
    NICHT_ANWENDBAR = "nicht_anwendbar"


class PublisherType(StrEnum):
    GERICHT = "gericht"
    BEHOERDE = "behoerde"
    NGO = "ngo"
    INSTITUTION = "institution"
    MEDIEN = "medien"
    UNTERNEHMEN = "unternehmen"


class SourceTier(IntEnum):
    """Quellen-Hierarchie: tiefere Zahl = stärkere Quelle."""

    GERICHT_BEHOERDE = 1
    NGO_INSTITUTION = 2
    MEDIEN = 3
    SELBSTAUSKUNFT = 4


PUBLISHER_TIER: dict[PublisherType, SourceTier] = {
    PublisherType.GERICHT: SourceTier.GERICHT_BEHOERDE,
    PublisherType.BEHOERDE: SourceTier.GERICHT_BEHOERDE,
    PublisherType.NGO: SourceTier.NGO_INSTITUTION,
    PublisherType.INSTITUTION: SourceTier.NGO_INSTITUTION,
    PublisherType.MEDIEN: SourceTier.MEDIEN,
    PublisherType.UNTERNEHMEN: SourceTier.SELBSTAUSKUNFT,
}


class VerificationLevel(StrEnum):
    """Wie weit wir einen Datensatz selbst geprüft haben."""

    UNGEPRUEFT = "ungeprueft"  # nur importiert
    QUELLE_GESICHTET = "quelle_gesichtet"  # Quelle existiert, Link funktioniert
    DOKUMENT_GEPRUEFT = "dokument_geprueft"  # Inhalt gegen Originaldokument abgeglichen


class MappingMethod(StrEnum):
    LEI = "lei"
    ISIN = "isin"
    NAME = "name"
    MANUELL = "manuell"
    REGISTER = "register"  # z. B. GLEIF/OpenFIGI
    KEINE = "keine"


class Confidence(StrEnum):
    HOCH = "hoch"
    MITTEL = "mittel"
    TIEF = "tief"


CONFIDENCE_RANK: dict[Confidence, int] = {
    Confidence.HOCH: 3,
    Confidence.MITTEL: 2,
    Confidence.TIEF: 1,
}


class RelationshipType(StrEnum):
    DIREKTE_MUTTER = "direkte_mutter"
    OBERSTE_MUTTER = "oberste_mutter"


class AssessmentStatus(StrEnum):
    """Belegstatus pro Unternehmen und Kriterium.

    Massgebend ist die Art und Qualität des stärksten Belegs (Beweisstatus), nicht
    die Anzahl Quellen. Siehe docs/methodik/validierung.md.
    """

    # Gericht/Behörde, rechtskräftig abgeschlossen, Originaldokument von uns geprüft
    FESTGESTELLT = "festgestellt"
    # Gericht/Behörde, abgeschlossen gemeldet – unsere Dokumentprüfung steht noch aus
    PRUEFUNG_AUSSTEHEND = "pruefung_ausstehend"
    # Gericht/Behörde, Verfahren laufend oder Status unbekannt
    VERFAHREN_LAUFEND = "verfahren_laufend"
    # NGO-Recherche mit Belegen oder Ausschlussentscheid einer Institution
    DOKUMENTIERT = "dokumentiert"
    # nur Medienberichte (auch mehrere heben die Stufe nicht an)
    MEDIENBERICHT = "medienbericht"
    # Belege vorhanden, aber Zuordnung zum Unternehmen nicht sicher genug
    ZUORDNUNG_UNSICHER = "zuordnung_unsicher"
    # Quelle hat das Unternehmen geprüft, nichts gefunden
    KEINE_HINWEISE = "keine_hinweise"
    # keine Abdeckung oder Emittent nicht identifiziert
    UNBEKANNT = "unbekannt"
    # z. B. Barmittel, Derivate
    NICHT_ANWENDBAR = "nicht_anwendbar"


# Status, bei denen mindestens ein Beleg vorliegt
FINDING_STATUSES: frozenset[AssessmentStatus] = frozenset(
    {
        AssessmentStatus.FESTGESTELLT,
        AssessmentStatus.PRUEFUNG_AUSSTEHEND,
        AssessmentStatus.VERFAHREN_LAUFEND,
        AssessmentStatus.DOKUMENTIERT,
        AssessmentStatus.MEDIENBERICHT,
        AssessmentStatus.ZUORDNUNG_UNSICHER,
    }
)

# Reihenfolge nach Beweisstatus – nur für Auswahl des stärksten Belegs und die
# Sortierung in der Anzeige. KEIN Score, keine Verrechnung zwischen Kriterien.
STATUS_DISPLAY_ORDER: dict[AssessmentStatus, int] = {
    AssessmentStatus.FESTGESTELLT: 0,
    AssessmentStatus.PRUEFUNG_AUSSTEHEND: 1,
    AssessmentStatus.VERFAHREN_LAUFEND: 2,
    AssessmentStatus.DOKUMENTIERT: 3,
    AssessmentStatus.MEDIENBERICHT: 4,
    AssessmentStatus.ZUORDNUNG_UNSICHER: 5,
    AssessmentStatus.UNBEKANNT: 6,
    AssessmentStatus.KEINE_HINWEISE: 7,
    AssessmentStatus.NICHT_ANWENDBAR: 8,
}


class ThresholdCheck(StrEnum):
    UEBERSCHRITTEN = "ueberschritten"
    NICHT_UEBERSCHRITTEN = "nicht_ueberschritten"
    SCHWELLENWERT_OFFEN = "schwellenwert_offen"
    KEINE_KENNZAHL = "keine_kennzahl"


class UpdateStatus(StrEnum):
    LAUFEND = "laufend"
    ERFOLGREICH = "erfolgreich"
    UNVERAENDERT = "unveraendert"
    FEHLGESCHLAGEN = "fehlgeschlagen"
    UEBERSPRUNGEN = "uebersprungen"


class VersionStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"


class CommercialUse(StrEnum):
    JA = "ja"
    NEIN = "nein"
    UNKLAR = "unklar"
