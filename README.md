# Projekt Transparenz (Arbeitstitel)

Fondspositionen mit nachvollziehbaren Quellen verbinden, damit Anlegerinnen und Anleger
selbst beurteilen können, ob ein «nachhaltiger» Fonds zu ihren Wertvorstellungen passt.

**Stand:** Website mit **fiktiven Demodaten**, zusätzlich ein separates lokales Schweizer
Rohdatenfundament aus GLEIF, Zefix/LINDAS und SwissPRTR. Keine Anlageberatung,
keine Empfehlungen, nicht rechtlich geprüft. Details: [STATUS.md](STATUS.md).

**Neu: lokaler Aktien-/Fonds-Katalog** mit SEC-Originaldaten, Suche und nachvollziehbaren
ETF-Nachweisen. Das weltweite Universum ist noch unvollständig.
Start und genaue Abdeckung: [Katalog-Anleitung](docs/GLOBAL_MARKET_CATALOG.md).

## Was der Prototyp heute kann

1. Eine ETF-Positionsliste (CSV) importieren und validieren
2. Positionen über ISIN → Wertpapier → Unternehmen (LEI) zuordnen, mit Vertrauensstatus
3. Pro Unternehmen und Ausschlusskriterium den **Belegstatus** zeigen: festgestellt, Verfahren
   laufend, dokumentiert (NGO/Institution), Medienbericht, Zuordnung unsicher, keine Hinweise,
   unbekannt – jeweils mit Quelle, Datum und Datenstand
4. Datenlücken sichtbar machen (fehlende Daten ≠ nachhaltig)
5. Einen Markdown-Bericht und eine CSV aller Belege exportieren

Kein Gesamtscore, keine Verrechnung zwischen Kriterien. Methodik: [docs/methodik/](docs/methodik/).

## Website ansehen (ohne Installation)

Im Explorer den Ordner `site` öffnen und **`index.html` doppelklicken**. Die Website ist ein
statischer Schnappschuss: Sie braucht weder Python noch Internet und lässt sich später
unverändert veröffentlichen (z. B. GitHub Pages, Workflow `pages.yml` – nur manuell).

Website nach Datenänderungen neu erzeugen (braucht die Einrichtung unten):

```powershell
.venv\Scripts\python -m transparenz build-site --update
```

## Lokale App und Werkzeuge (Windows PowerShell)

Alle Befehle im Projektordner ausführen (vorher `cd "…\Projekt Transparenz"`).

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
```

Danach im Browser: <http://localhost:8501>. `-ExecutionPolicy Bypass` gilt nur für diesen
einen Aufruf und ändert keine Systemeinstellung.

Ohne Skripte, Schritt für Schritt:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m transparenz update --force
.venv\Scripts\python -m streamlit run app\main.py
```

Linux/macOS: `bash scripts/setup.sh`, danach `.venv/bin/python -m streamlit run app/main.py`.

## Kommandozeile

Schweizer Rohdaten lokal aktualisieren (keine Veröffentlichung):

```powershell
cd "C:\Users\Bader\OneDrive\Desktop\Projekt Transparenz"
.venv\Scripts\python -m transparenz swiss-update
```

Nur eine Quelle: `swiss-update --source gleif_ch` bzw. `zefix_lindas` oder `swissprtr`.
Wikidata liefert in dieser Umgebung HTTP 403 und ist deshalb im Standardlauf deaktiviert;
ein bewusster neuer Versuch ist mit `--source wikidata_ch` möglich. Tatsächlich versuchte,
fehlgeschlagene Updates melden weiterhin Exitcode 1. Bei unveränderten Daten wird der fertige
Export wiederverwendet; aktuelle Laufmeldungen stehen in `data/processed/swiss/latest_status.json`.
`--export-only` baut den Export ausdrücklich vollständig ohne Netzwerk neu auf (mehrere Minuten).
Grosse Läufe **nacheinander**, mit mehreren GB freiem Speicher ausführen.
Originale: `data/raw/external/`; separate Datenbank: `data/processed/swiss.sqlite`;
Exportzeiger und Qualitätszahlen: `data/processed/swiss/current.json`.
Die Pfade bleiben Git-ignoriert. Übergabe: [CODEX_TO_CLAUDE_HANDOFF.md](docs/CODEX_TO_CLAUDE_HANDOFF.md).
Kein vollständiger Aktien-/ETF-Katalog; GLEIF-Fondsrechtsträger sind keine ETF-Anteilsklassen.

```text
python -m transparenz validate            # Quellen prüfen, nichts schreiben
python -m transparenz update [--force]    # Aktualisieren (fehlerhafte Daten werden abgelehnt)
python -m transparenz status              # Aktualität aller Quellen
python -m transparenz screen --fund ZZFIKETF0019 --out bericht.md
```

## Tests

```powershell
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m ruff check .
```

## Aufbau

Siehe [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/DATA_MODEL.md](docs/DATA_MODEL.md),
[docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) und das Entscheidungslog
[docs/DECISIONS.md](docs/DECISIONS.md).

## Lizenz

Noch nicht festgelegt (offene Frage, siehe STATUS.md). Bis dahin: alle Rechte vorbehalten.
