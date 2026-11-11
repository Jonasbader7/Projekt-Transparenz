# KI-Nutzung, Skills und Werkzeuge

Stand: 11.11.2026. Diese Übersicht macht die Entwicklung des Projekts nachvollziehbar.
Sie unterscheidet dokumentierte Beiträge, technische Abhängigkeiten und tatsächlich
verwendete Skills. Installierte oder verfügbare Fähigkeiten gelten nicht automatisch als verwendet.

## KI-Assistenten und Verantwortung

| Beteiligte | Dokumentierter Beitrag | Beleg |
|---|---|---|
| Jonas Bader | Projektziele, Anforderungen und Freigaben | [Projektgedächtnis](../CLAUDE.md), [Entscheidungslog](DECISIONS.md) |
| Claude / Claude Code | SwissPRTR-Emissionen normalisieren; Wikidata-Abfragen, User-Agent und Wertpapierkandidatensuche reparieren | [Sessionlog vom 08.11.2026](LOG.md), Entscheide D-032 und D-034 in [DECISIONS.md](DECISIONS.md) |
| OpenAI Codex | Schweizer Rohdatenfundament; lokaler SEC-Aktien-/Fonds-Katalog; diese Transparenzdokumentation | [Sessionlog](LOG.md), Entscheide D-028 bis D-031 und D-033 in [DECISIONS.md](DECISIONS.md), [Codex-Übergabe](CODEX_TO_CLAUDE_HANDOFF.md) |

Die Zuordnung folgt den vorhandenen Projektaufzeichnungen. Sie ist keine vollständige
Urheberschaftsliste für jede Codezeile. Historische Modellversionen, Prompts, Skill-Aufrufe,
Zeitaufwände und Nutzungsanteile sind nicht lückenlos erfasst und werden nicht geschätzt.
KI-Unterstützung allein belegt weder Datenrichtigkeit noch eine rechtliche Prüfung.

## Skills

Ein Skill ist eine Arbeitsanleitung für einen KI-Assistenten, beispielsweise zum Einrichten
einer Umgebung oder zum Prüfen einer Oberfläche. Er ist weder eine Python-Bibliothek noch
ein fachlicher Beleg für eine Fondsbewertung.

| Skill | Einsatz / Status | Nachweis und Grenze |
|---|---|---|
| `cloud-environment:cloud-environment-runtime` | In der Codex-Sitzung vom 11.11.2026 gelesen und für die Cloud-Arbeitsumgebung verwendet; einschliesslich Netzwerk- und Paketinstallationshinweisen | [Skill-Quelle](skill://plugin_connector_1p_c5b7d5df5d7081918f2c4be5a633ed5d/cloud-environment-runtime/SKILL.md); sitzungsgebundene Quelle, ausserhalb von ChatGPT eventuell nicht zugänglich |
| Weitere Skills früherer Claude-/Codex-Sessions | Nicht dokumentiert | Aus dem Repository nicht zuverlässig rekonstruierbar; keine Behauptung, dass keine verwendet wurden |

`CLAUDE.md` ist eine versionierte Projektanweisung, kein Nachweis für einen installierten
Skill. Ein verfügbarer Figma-, Browser- oder anderer Skill wird hier erst eingetragen,
wenn er für dieses Projekt tatsächlich verwendet wurde.

## Werkzeuge und technischer Rahmen

| Werkzeug / Technik | Zweck | Nachweis |
|---|---|---|
| Python, pandas | Datenaufbereitung und Auswertung | [pyproject.toml](../pyproject.toml) |
| Pydantic | Validierung importierter Daten | [Entitäten](../src/transparenz/entities/models.py) |
| SQLAlchemy und SQLite | Datenhaltung und Versionierung | [Datenbankschicht](../src/transparenz/database/) |
| httpx | HTTP-Abrufe externer Datenquellen | [Importmodule](../src/transparenz/ingestion/) |
| Jinja2 und Markdown | Statische Website und Methodiktexte | [Website-Generator](../src/transparenz/site/), [pyproject.toml](../pyproject.toml) |
| Streamlit | Lokale App | [app/](../app/) |
| pytest und Ruff | Automatisierte Tests und statische Codeprüfung | [tests/](../tests/), [CI](../.github/workflows/ci.yml) |
| Git, GitHub und GitHub Actions | Versionsgeschichte, Zusammenarbeit, Tests und manuelle Veröffentlichung | [Workflows](../.github/workflows/) |
| GitHub-Connector und Shell in Codex | Repository lesen, Änderungen vorbereiten und auf GitHub bereitstellen | Dokumentationssitzung vom 11.11.2026 im [Sessionlog](LOG.md) |

Die Bibliotheken sind im Projekt deklariert; daraus folgt nicht, dass jede in jeder Session
aufgerufen wurde. Prüfberichte im Sessionlog gelten jeweils für den dort genannten Stand.
Aktuelle CI-Ergebnisse stehen unter [GitHub Actions](https://github.com/Jonasbader7/Projekt-Transparenz/actions).

## Datenquellen und KI-Ausgaben

GLEIF, Zefix/LINDAS, SwissPRTR, Wikidata und SEC sind Datenquellen, keine KI-Skills.
Abdeckung, Lizenzstatus und Grenzen stehen im [Quellenregister](DATA_SOURCES.md).
Die öffentliche Demo enthält fiktive Beispieldaten; echte lokale Datenbestände sind davon
getrennt. Die Screening-Engine verwendet explizite Regeln und Belege; die hier dokumentierte
KI-Unterstützung beschreibt die Entwicklung und ist keine zusätzliche Datenquelle.

## Pflege pro Session

Bei neuen Einträgen im [Sessionlog](LOG.md) festhalten:

- Datum, Assistent und konkrete Aufgabe; Modellversion nur, wenn bekannt.
- Tatsächlich gelesene/verwendete Skills mit exaktem Namen und zugänglicher Quelle,
  oder «keine verwendet» bzw. «nicht erfasst».
- Wesentliche Werkzeuge und deren Zweck; Unteragenten nur, wenn tatsächlich eingesetzt.
- Geänderte Dateien, ausgeführte Prüfungen, Ergebnisse und offene Grenzen.
- Veröffentlichungen mit Commit-/PR-Verweis, sobald vorhanden.

Keine Zugangsdaten, privaten Kontaktangaben oder vertraulichen Prompts veröffentlichen.
Diese Übersicht wird manuell gepflegt; sie erfasst keine Tool-Aufrufe automatisch.
