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
    (DatasetKind.MARKET, "Wertpapierkatalog und Registerbeobachtungen"),
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


# ------------------------------------------------ Bericht zur Fondskette (Pilot)
# Schlüssel der Beziehungstypen wie in services/ownership.py (RELATIONSHIP_TYPES);
# als Text geschrieben, damit entities/ nicht von services/ abhängt (Test prüft Gleichheit).
GEM_PHASE_LABELS = {"ankuendigung": "angekündigt",
                    "genehmigung": "im Genehmigungsverfahren oder genehmigt",
                    "bau": "in Bauvorbereitung oder im Bau"}

GEM_CAPACITY_LABELS = {"foerderung": "Förderung (Kohleminen)", "kraftwerke": "Kraftwerke",
                       "lng": "LNG-Terminals", "transport": "Pipelines"}

CONFIDENCE_LABELS: dict[str, tuple[str, str]] = {
    "consistent": ("Widerspruchsfrei zugeordnet",
                   "Die ISIN führt zu genau einem Unternehmen mit genau einem LEI. GLEIF führt "
                   "den LEI, und der Name passt zum Positionsnamen."),
    "consistent_lapsed": ("Widerspruchsfrei, LEI nicht erneuert",
                          "Wie oben, aber die LEI-Registrierung wurde nicht erneuert. Die "
                          "Stammdaten bei GLEIF können veraltet sein."),
    "confirmed_by_decision": ("Von Hand bestätigt",
                              "Ein Mensch hat diese Zuordnung geprüft und bestätigt. Der "
                              "Entscheid ist gespeichert und gilt für jeden Fonds mit "
                              "dieser ISIN."),
    "confirmed_by_register": ("Automatisch über Registernummer",
                              "Wikidata nennt die Registernummer des Unternehmens, und GLEIF "
                              "führt genau einen aktiven Rechtsträger mit dieser Nummer in "
                              "derselben Rechtsordnung."),
    "confirmed_by_agreement": ("Automatisch: zwei Verfahren einig",
                               "Wikidata-Kennung und die unabhängige GLEIF-Namenssuche mit "
                               "Sitzland zeigen auf denselben LEI. Das löst eine "
                               "Namensabweichung oder Mehrdeutigkeit auf."),
    "auto_by_name": ("Automatisch über Namenssuche",
                     "Kein Kennungsweg vorhanden. Die GLEIF-Namenssuche findet genau einen "
                     "aktiven, gleichnamigen Rechtsträger im Sitzland; das Verfahren ist "
                     "freigegeben, weil seine gemessene Präzision die Schwelle erreicht."),
    "name_proposal": ("Vorschlag der Namenssuche",
                      "Die GLEIF-Namenssuche findet genau einen passenden Rechtsträger, das "
                      "Verfahren ist aber (noch) nicht freigegeben. Bleibt offen."),
    "rejected_by_decision": ("Von Hand abgelehnt",
                             "Ein Mensch hat die vorgeschlagene Zuordnung geprüft und "
                             "abgelehnt. Die Position bleibt ohne Unternehmen."),
    "name_mismatch": ("Prüffall: Name weicht ab",
                      "Die Kennungen passen zusammen, aber Positionsname und GLEIF-Namen "
                      "(inklusive früherer Namen) haben nichts gemeinsam. Oft eine Umbenennung, "
                      "manchmal eine andere Gesellschaft derselben Gruppe."),
    "lei_not_in_gleif": ("Prüffall: LEI bei GLEIF unbekannt",
                         "Wikidata nennt einen LEI, den GLEIF nicht führt."),
    "lei_not_checked": ("Nicht geprüft", "GLEIF wurde für diesen LEI nicht abgefragt."),
    "ambiguous": ("Mehrdeutig",
                  "Zur ISIN gibt es mehrere Einträge oder mehrere LEIs. "
                  "Es wird nichts ausgewählt."),
    "no_lei": ("Unternehmen ohne LEI",
               "Wikidata kennt das Unternehmen, nennt aber keinen LEI. Ohne LEI keine "
               "Verknüpfung mit Belegen."),
    "unknown": ("Keine Zuordnung",
                "Für diese ISIN gibt es in den verwendeten Quellen keinen Eintrag."),
    "no_valid_isin": ("Keine gültige ISIN",
                      "Die Fondsmeldung enthält keine prüfziffergültige ISIN."),
}

STATUS_LABELS = {
    "confirmed": "Zugeordnet",
    "identity_conflict": "Identitätskonflikt im Register",
    "position_mapping_unconfirmed": "Position nicht widerspruchsfrei zugeordnet",
    "relationship_start_unknown": "Beginn der Konzernbeziehung nicht gemeldet",
    "relationship_not_valid_at_fund_date": "Konzernbeziehung am Fondsstichtag nicht gültig",
    "outside_relationship_period": "Emissionsjahre vor Beginn der Konzernbeziehung",
}

KIND_LABELS = {"direct-parent": "direkte Mutter", "ultimate-parent": "oberste Mutter"}

CORROBORATION_LABELS = {"FULLY_CORROBORATED": "vollständig bestätigt",
                        "PARTIALLY_CORROBORATED": "teilweise bestätigt",
                        "ENTITY_SUPPLIED_ONLY": "nur vom Unternehmen gemeldet"}

SOURCE_LABELS = {"eu_ets": "EU-Emissionshandel", "swissprtr": "SwissPRTR (Schweiz)"}

GEM_STAKE_LABELS = {"control": "Eigentum: Kontrolle (ab 50 %)",
                    "significant": "Eigentum: bedeutende Beteiligung (20–50 %)",
                    "small": "Eigentum: kleine Beteiligung (unter 20 %)",
                    "unknown": "Eigentum: Anteil unbekannt",
                    "financial_stake_unclear": "Finanzbeteiligung, Rechnung ungeklärt",
                    "asset_management": "Vermögensverwaltung für Kunden oder Fonds",
                    "custody": "Verwahrung für Dritte",
                    "custodial": "Treuhänderisch gehalten (Regel bis Profil 1.0)"}

RELATIONSHIP_LABELS = {"own_account": "Eigentum auf eigene Rechnung",
                       "financial_stake_unclear": "Finanzbeteiligung, Rechnung ungeklärt",
                       "asset_management": "Vermögensverwaltung für Kunden oder Fonds",
                       "custody": "Verwahrung für Dritte", "financing": "Finanzierung",
                       "operation": "Betrieb", "supply_contract": "Liefervertrag"}

GEM_STATUS_LABELS = {"expansion": "im Ausbau", "operating": "in Betrieb",
                     "closed": "stillgelegt/aufgegeben", "unknown": "Status unbekannt"}

GEM_KIND_LABELS = {"coal_plant": "Kohlekraftwerk", "coal_mine": "Kohlemine",
                   "gas_plant": "Gas-/Ölkraftwerk", "lng_terminal": "LNG-Terminal",
                   "gas_pipeline": "Gaspipeline", "oil_pipeline": "Öl-/NGL-Pipeline"}

GEM_CATEGORY_LABELS = {"coal": "Kohle", "oil_gas": "Gas-/Öl-Kraftwerke und -Infrastruktur"}

OPEN_REASONS = {
    "unknown": "kein Wikidata-Eintrag zur ISIN",
    "no_lei": "Wikidata-Eintrag ohne LEI",
}

PROVENANCE_STATUS_LABELS = {
    "verified": "Prüfsumme bestätigt",
    "derived": "aus geprüftem Archiv entpackt, bestätigt",
    "generated": "von uns erzeugt, Prüfsumme festgehalten",
    "unrecorded": "nicht erfasst",
}
