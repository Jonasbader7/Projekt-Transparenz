# Projektstand

Stand: 20. November 2026. Nebenprojekt im Aufbau, kein fertiges Produkt.

**Warum die Website nur fiktive Fonds zeigt:** Die Auswertung echter Fonds läuft bisher lokal.
Sie wird erst veröffentlicht, wenn die Lizenzen aller beteiligten Quellen schriftlich geklärt
und die Ergebnisse geprüft sind. Was die Website heute zeigt, ist die Darstellung und die
Methode; die Zahlen unten beschreiben, wie gut die Methode an echten Daten funktioniert,
ohne einzelne Fonds oder Firmen zu nennen.

## Was steht

| Baustein | Stand |
|---|---|
| Fundament | Datenordner, Update-System mit Versionierung, Prüfsumme jeder Rohdatei bei jeder Verwendung |
| Fondspositionen USA | Quartalsarchiv der SEC mit den Positionsmeldungen US-registrierter Fonds (N-PORT), 3. Quartal 2026, eingelesen und geprüft |
| Wertpapierstamm ISIN → LEI | aus übereinstimmenden Meldungen unabhängiger Fondsgesellschaften, Widersprüche bleiben offen |
| Zuordnung im Pilot | sechs echte Fonds, lokal: Position → Unternehmen → Beleg |
| Belege im Pilot | EU-Emissionshandel, Schweizer Schadstoffregister, Beteiligungen aus Global Energy Monitor |
| Website | fiktive Demodaten, offene Methodik, Datenquellen mit Aktualität |

## Messwerte (ohne Namen)

| Messgrösse | Wert |
|---|---|
| N-PORT 3. Quartal 2026 | 14'066 Meldungen, rund 5.6 Mio. Positionen, 0 Zeilen abgelehnt |
| Gemeldete Emittenten-LEI bei GLEIF vorhanden | 99.97 % |
| Wertpapiere mit bestätigtem LEI | 116'216 ISIN; sie stehen für 73 % der Positionen mit gültiger ISIN |
| Widersprüchliche Meldungen | 2'707 ISIN, bleiben offen |
| Namenssuche, an den Fondsmeldungen gemessen | 645 von 649 richtig; freigegeben in Europa und Asien-Pazifik, übrige Regionen noch zu wenige Fälle |
| Zugeordnetes Fondsgewicht im Pilot | 90–98 % je Fonds (vor den Fondsmeldungen: 44–81 %) |
| Belege aus dem EU-Emissionshandel mit Namensprüfung | alle |
| Herkunftsprüfung der aktiven Datenstände | 171 von 171 Dateien bestätigt |
| Automatische Tests | 398 bestanden |

## Nächste Schritte

1. Doppelte Fondsmeldungen am selben Tag inhaltlich vergleichen: nur bei identischen
   Positionen eine übernehmen, sonst offen lassen.
2. Auch gespeicherte Abfragen (Wikidata, GLEIF) mit Prüfsumme beim Abruf festhalten.
3. Danach: weitere Länder und Fondsquellen, schriftliche Lizenzbestätigungen, erst dann
   echte Ergebnisse auf der Website.

## Grenzen

- «Alle Aktien» heisst vorerst: jede Aktie, die mindestens ein an die SEC meldender Fonds hält.
- Fondsmeldungen sind Angaben der Fonds («as filed»); die SEC garantiert ihre Richtigkeit nicht.
- Keine Anlageempfehlung, kein Gesamtscore, keine Renditeaussage.

Der ausführliche Verlauf steht im Repository: `STATUS.md`, `docs/ROADMAP.md`,
`docs/DECISIONS.md`.
