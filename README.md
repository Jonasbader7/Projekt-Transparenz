# Projekt Transparenz (Arbeitstitel)

Fondspositionen mit nachvollziehbaren Quellen verbinden, damit Anlegerinnen und Anleger
selbst beurteilen können, ob ein «nachhaltiger» Fonds zu ihren Wertvorstellungen passt.

**Stand:** Forschungsprototyp mit ausschliesslich **fiktiven Demodaten**. Keine Anlageberatung,
keine Empfehlungen, nicht rechtlich geprüft. Details: [STATUS.md](STATUS.md).

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
