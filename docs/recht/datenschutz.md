# Datenschutz (DSG) – Privacy by Design

*Arbeitsnotiz, **nicht rechtlich geprüft**.* Massgebend ist das revidierte Schweizer
Datenschutzgesetz (DSG, in Kraft seit 1. September 2023).

## Heutiger Stand

- Die Anwendung verarbeitet **keine Konten, Logins oder Depots**. Die lokale Streamlit-App
  trackt nicht (Nutzungsstatistik deaktiviert in `.streamlit/config.toml`).
- **Website (seit D-024, wirksam erst nach Veröffentlichung):** Auf
  `jonasbader7.github.io` läuft dieselbe cookielose Besuchszählung wie auf Portfolio und BORS
  (eigener Cloudflare Worker, Code im Repo `Portfoliopage/analytics/`):
  - zusammengefasste Zähler (Website-Aufrufe, Link-Kategorien, Dauer, Gerät, Browser, Land/Region/Stadt),
    keine Cookies, kein Local Storage, keine IDs; GPC/Do-Not-Track werden beachtet;
  - **Sicherheitsprotokoll mit voller IP-Adresse** je Seitenaufruf, 14 Tage. Das sind
    **Personendaten**. Bearbeitung bei Cloudflare (USA) → Bekanntgabe ins Ausland (Art. 16 ff. DSG).
  - Datenschutzhinweis: https://jonasbader7.github.io/Portfoliopage/analytics/datenschutz.html
  - Ausschalten: `endpoint: ""` in `src/transparenz/site/static/analytics-config.js`, dann
    `build-site`.
  - Offen (nicht rechtlich geprüft): Erforderlichkeit des IP-Protokolls, Rechtfertigung,
    EU-Besucher:innen (DSGVO), Hinweis ohne Einwilligungsbanner.
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
| Analytics | eingebaut (D-024): eigener Worker, kein Drittanbieter-Tracking; IP-Protokoll vor echten Nutzer:innen (Interviews) rechtlich prüfen |
