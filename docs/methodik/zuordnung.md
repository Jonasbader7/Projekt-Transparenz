# Zuordnung: von der Fondsposition zum Unternehmen

Ein Fonds meldet Wertpapiere, keine Unternehmen. Bevor ein Beleg (zum Beispiel ein
Emissionswert) einer Position zugeordnet werden kann, muss feststehen, welcher Rechtsträger
das Wertpapier ausgegeben hat. Diese Seite beschreibt, wie das geschieht und wo die Grenzen
liegen.

## Grundsatz: Kennungen vor Namen

- **ISIN** bezeichnet ein Wertpapier, **LEI** einen Rechtsträger. Die beiden werden nie
  verwechselt.
- Ein Name ist nie ein Schlüssel. Gleiche Namen kommen bei verschiedenen Firmen vor, und
  dieselbe Firma erscheint unter verschiedenen Schreibweisen.
- Jede Zuordnung nennt ihren Weg. Präzision (wie oft ein Weg richtig liegt) und Abdeckung
  (wie viel Fondsgewicht zugeordnet ist) werden immer getrennt ausgewiesen.

## Reihenfolge der Wege

1. **Menschlicher Entscheid.** Wurde ein Fall einmal von Hand mit Ja oder Nein entschieden,
   gilt dieser Entscheid und dient zugleich als Referenzfall.
2. **Fondsmeldungen an die US-Aufsicht (SEC N-PORT).** US-registrierte Fonds melden je Position
   ISIN und LEI des Emittenten. Gilt nur, wenn mindestens zwei voneinander unabhängige
   Fondsgesellschaften denselben LEI melden, keine widerspricht und der LEI bei GLEIF
   existiert. «Unabhängig» heisst verschiedene Beratergruppen, nicht bloss verschiedene
   Fonds derselben Gruppe. Widersprüche bleiben offen und werden nie nach Mehrheit entschieden.
3. **Wikidata ISIN → LEI.** Gemeinschaftlich gepflegte Kennungen. Nennt Wikidata einen
   anderen LEI als die Fondsmeldungen, gilt die Fondsmeldung; die Abweichung wird angezeigt.
4. **Registernummer.** Dieselbe Handelsregisternummer bei Wikidata und GLEIF.
5. **GLEIF-Namenssuche** (gleicher Name, gleiches Sitzland, aktiver Rechtsträger, eindeutiger
   Treffer). Sie wirkt nur, wenn ihre an Referenzfällen gemessene Präzision die Freigabe
   erreicht: mindestens 100 Fälle und eine untere 95-%-Grenze von mindestens 97 %, gemessen
   **je Region**. Sie wirkt nie gegen einen bestätigten LEI aus den Fondsmeldungen.

Erreicht kein Weg ein Ergebnis, bleibt die Position «nicht zugeordnet». Das ist eine
Informationslücke, keine Entwarnung.

## Messung statt Annahme

Die Fondsmeldungen dienen als unabhängige Referenz: An ihnen wird gemessen, wie oft die
übrigen Wege richtig liegen. Die Messung ist von der Zuordnung getrennt; sie ändert sich
nicht dadurch, welcher Weg eine Position am Ende zuordnet. Sinkt die gemessene Präzision
unter die Schwelle, wird die Namenssuche für diese Region automatisch wieder gesperrt.

## Konzernbeziehungen

Belege betreffen oft eine Tochtergesellschaft, nicht die börsenkotierte Mutter. Eine
Verbindung über den Konzern zählt nur, wenn die Beziehung aus einer Quelle mit Kennungen
stammt (GLEIF-Beziehungsdaten) und nach Beziehungstyp eingeordnet ist: Nur Eigentum auf
eigene Rechnung gilt als Beteiligung; Vermögensverwaltung, Verwahrung, Finanzierung oder
Lieferverträge haben eigene Regeln.

Vor einem Beleg aus dem EU-Emissionshandel wird geprüft, ob der Name des Kontoinhabers zum
Rechtsnamen bei GLEIF passt. Weicht er klar ab, wird der Beleg gesperrt statt gezeigt.

## Grenzen

- Die Fondsmeldungen decken nur Papiere ab, die US-registrierte Fonds halten.
- Ein Konsens heisst «mehrere Gesellschaften melden dasselbe», nicht «geprüfte Wahrheit». Ein
  gemeinsam übernommener Fehler eines Datenlieferanten ist nicht erkennbar.
- Die Freigabe der Namenssuche gilt nur für Regionen mit genügend Referenzfällen.
