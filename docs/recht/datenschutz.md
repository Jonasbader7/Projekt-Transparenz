# Datenschutz (DSG) – Privacy by Design

*Arbeitsnotiz, **nicht rechtlich geprüft**.* Massgebend ist das revidierte Schweizer
Datenschutzgesetz (DSG, in Kraft seit 1. September 2023).

## Heutiger Stand

- Die Anwendung verarbeitet **keine Personendaten** von Nutzerinnen und Nutzern: keine
  Konten, keine Logins, keine Depots, kein Tracking (Streamlit-Nutzungsstatistik deaktiviert in
  `.streamlit/config.toml`).
- Nur fiktive Daten im Repository. Echte Depotauszüge sind ausgeschlossen (`.gitignore`).
- Interview-Notizen bleiben lokal und pseudonymisiert (`docs/kundengespraeche/notizen/`).

## Personendaten in Quellen

Sachverhalte betreffen Unternehmen. Medien- und Gerichtsdokumente können aber Namen natürlicher
Personen enthalten (z. B. Geschäftsleitung). Grundsatz: **keine Personennamen in unseren
Datensätzen**, nur Unternehmen und Dokumentlinks.

## Vor künftigen Funktionen

| Funktion | Datenschutzfrage |
|---|---|
| Portfolio-Upload | Finanzdaten = heikel; lokal im Browser verarbeiten? Speicherdauer? Einwilligung? |
| Benutzerkonten | Datenschutzerklärung, Auskunfts- und Löschrechte, Hosting-Standort |
| Hosting (Cloud) | Bekanntgabe ins Ausland (Art. 16 ff. DSG), Auftragsbearbeitung |
| Analytics | nur datensparsam, ohne Drittanbieter-Tracking |
