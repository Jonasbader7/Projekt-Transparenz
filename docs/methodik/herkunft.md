# Herkunft: jede Zahl bis zur Originaldatei

Jede Aussage soll sich bis zur Datei zurückverfolgen lassen, aus der sie stammt. Deshalb
werden Rohdaten nie still verändert oder ersetzt.

## Wie das geprüft wird

- **Beim Herunterladen** wird jede Originaldatei unverändert abgelegt, zusammen mit einer
  Begleitdatei: Quelle, Adresse, Abrufzeit, Lizenzangaben und SHA-256-Prüfsumme.
- **Bei jeder Verwendung** wird die Datei neu gehasht und mit dieser Prüfsumme verglichen.
  Entpackte Dateien werden gegen den Eintrag im geprüften Archiv verglichen.
- **Im Update-System** gilt zusätzlich: Das Verzeichnis eines Datenstands (Manifest) muss die
  Prüfsumme tragen, die beim Aktivieren gespeichert wurde, und jede darin genannte
  Originaldatei muss mit Manifest und Begleitdatei übereinstimmen.
- **Weicht etwas ab, bricht die Verarbeitung ab.** Der letzte gültige Stand bleibt aktiv.
- Fehlt eine Begleitdatei, steht «nicht erfasst». Es wird nichts ergänzt oder erraten.

## Was ausgewiesen wird

Berichte und Qualitätsberichte führen jede Eingabe mit Pfad, Grösse, Prüfsumme, Status
(geprüft, aus geprüftem Archiv, von uns erzeugt, nicht erfasst), Lizenzangabe und Abrufdatum.

## Lizenzen

Verwendet wird nur, was an der Originalseite eine benannte Lizenz oder eine ausdrückliche
Gemeinfreiheit trägt. «Öffentlich abrufbar» genügt nicht. Im Update-System werden Quellen
ohne geprüfte Lizenz gar nicht erst abgerufen. Quellen, die nur im lokalen Pilot dienen und
keine benannte Lizenz tragen, sind im Bericht so gekennzeichnet und werden nicht
veröffentlicht. Details stehen auf der Seite «Datenquellen & Aktualität» und in
`docs/DATA_SOURCES.md`.
