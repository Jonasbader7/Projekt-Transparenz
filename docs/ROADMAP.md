# Roadmap: vom Pilot zum weltweiten Bestand

Stand: 15.11.2026. Auftrag Jonas: alle börsenkotierten Aktien und Fonds weltweit erfassen,
Informationen dazu finden und zuordnen – weitgehend automatisch und so, dass daraus eine Firma
werden kann. Diese Datei ist der Plan; der aktuelle Stand steht in `STATUS.md`.

## Grundsätze

- **Jede Zahl ist nachvollziehbar:** Quelle, Datei-Prüfsumme, Abrufdatum und Version je Fakt.
- **Jede Quelle ist rechtlich haltbar** nach D-041 (benannte Lizenz oder ausdrückliche
  Gemeinfreiheit für gewerbliche Nutzung). Interne Messung ist zulässig, Veröffentlichung oder
  Verkauf erst nach schriftlicher Bestätigung.
- **Jeder Schritt ist wiederholbar** und durch Tests sowie Vergleichsläufe abgesichert.
- **Keine Einzelfallarbeit für Jonas:** Referenzen für Messungen kommen aus unabhängigen
  Kennungsquellen; Bewertungsregeln setzen wir mit begründetem Standard und bezeichnen sie als
  unsere Bewertungsentscheidung. Jonas entscheidet nur Grundsätzliches (Kosten, Lizenzen,
  Downloads, Veröffentlichung).

## Zielbild: fünf Schichten, nie vermischt

| Schicht | Inhalt | Quellen |
|---|---|---|
| 1. Unternehmen | Rechtsträger mit LEI und Konzernbeziehungen | GLEIF Golden Copy (CC0) |
| 2. Wertpapiere | ISIN → Emittent (LEI) → Konzernmutter | N-PORT-Meldungen, Wikidata, Registernummer; Namenssuche nur nach gemessener Freigabe |
| 3. Fonds und Positionen | was jeder Fonds hält | USA: SEC N-PORT; Schweden: FI; CH/EU: Nutzer-Upload, ab 2028 ESAP |
| 4. Belege | Fakten je Unternehmen mit Quelle | EU-Emissionshandel, GEM, SwissPRTR, weitere |
| 5. Bewertung | unser Profil | nur `criteria.toml`, als eigene Entscheidung bezeichnet |

Grenze: «alle Aktien» heisst jede Aktie, die mindestens ein meldender Fonds hält. Ausgewiesen
werden die Zahl der abgedeckten ISINs und der Anteil am Fondsgewicht, nie «100 %».

## Phasen

### Phase 0 – Fundament (15.11.2026)

| Schritt | Abschlusskriterium |
|---|---|
| Git-Stände zusammenführen | ein `main` ohne Abweichung zu GitHub ausser lokalen Commits |
| Datenordner ausserhalb OneDrive (`TRANSPARENZ_DATA_DIR`) | alle aktiven Datenstände gefunden, Prüfungen bestanden, Tests schreiben nie in echte Daten |
| Pilot-Skript in Paketmodule zerlegen | Vergleichslauf der sechs Pilotfonds vorher/nachher ohne Abweichung (`scripts/pilot_regression.py`) |
| Herkunft je Fakt | jede Position und jeder Beleg nennt Quelle, Datei-Prüfsumme und Abrufdatum |

### Phase 1 – SEC N-PORT importieren (umgesetzt 15.11.2026, D-054)

Stand: 2026q3 geladen und eingelesen, 0 abgelehnte Zeilen; gemeldete LEI gegen die
GLEIF-Liste Level 1 geprüft (D-055). Messwerte in STATUS.md.


- Download `2026q3_nport.zip` (440.95 MB, sec.gov), nur mit Zustimmung.
- Adapter mit Pydantic-Prüfung, abgelehnte Zeilen gezählt, jeder Lauf in `update_runs`.
- Gemessen: Fonds, Positionen, Anteil mit ISIN, mit LEI, mit gültiger Prüfziffer, LEI aktiv
  bei GLEIF. Prüfen, welche Monatsmeldungen öffentlich sind und welcher Stichtag gilt.
- N-PORT direkt aus dem ZIP lesen (Speicher).

### Phase 2 – Wertpapierstamm und Messung ohne Handarbeit

- Konsens: ISIN → LEI gilt als «bestätigt durch Fondsmeldungen», wenn mindestens zwei
  unabhängige Fondsgesellschaften denselben LEI melden und keine widerspricht.
- Gegenprüfungen: GLEIF (existiert, aktiv), Wikidata, Registernummer. Widersprüche separat.
- Messung der Namenssuche gegen diese Referenz: Testmenge vorab fest abgetrennt, Freigabe je
  Verfahren und je Region (D-046).

### Phase 3 – Fondsuniversum

- Alle US-Fonds und die schwedischen Fonds mit Abdeckungsbericht je Fonds.
- Gesellschaft ≠ Serie ≠ Anteilsklasse ≠ Listing (SEC-Klassenliste).

### Phase 4 – Belege auf den ganzen Bestand

- Bestehende Belegquellen einmal über alle LEIs inklusive Konzernketten rechnen.
- Danach die erste neue Belegquelle.

### Phase 5 – Firmentauglichkeit (parallel)

- Schriftliche Bestätigungen (SEC, FI, EU-Kommission) vor jeder Veröffentlichung; Entwürfe
  durch uns, Versand durch Jonas.
- Einmalige Prüfung durch eine Schweizer Anwältin oder einen Anwalt (Kosten: Entscheid Jonas).
- FIDLEG: Trennung von Beleg und Bewertung bleibt Kernprinzip.
- Server und grössere Datenbank erst bei Produktstart.
