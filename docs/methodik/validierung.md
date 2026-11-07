# Belegmodell und Validierung

*Version 0.2 vom 07.11.2026 – Entwurf, nicht extern geprüft.*

## Grundidee

Wir vergeben **keinen Nachhaltigkeits-Score**. Für jedes Unternehmen in einem Fonds und jedes
Ausschlusskriterium zeigen wir, **welche Belege es gibt, von wem sie stammen und wie belastbar
sie sind**. Das Urteil, ob ein Fonds zu den eigenen Werten passt, treffen die Nutzerinnen und
Nutzer selbst.

## Der Sachverhalt (ein Datensatz)

Jeder Beleg ist ein nachvollziehbarer Datensatz mit:

| Feld | Bedeutung |
|---|---|
| Unternehmen, Kennung | Name wie in der Quelle, LEI und/oder ISIN, falls angegeben |
| Kriterium | z. B. Kohle, Entwaldung |
| Beschreibung | was die Quelle sagt – keine eigene Wertung |
| Art | Vorwurf · behördliche Feststellung · Gerichtsurteil · Ausschlussentscheid einer Institution · Unternehmensstellungnahme · Abhilfemassnahme |
| Verfahrensstatus | laufend · abgeschlossen (rechtskräftig) · unbekannt · nicht anwendbar |
| Herausgeber, Herausgebertyp | wer es veröffentlicht hat (Gericht, Behörde, NGO, Institution, Medien, Unternehmen) |
| Quelle, URL | Titel und Link des Originaldokuments |
| Veröffentlichungs- und Ereignisdatum | wann publiziert, wann passiert |
| Importzeitpunkt, Datenstand | wann und aus welcher Version unserer Datenquelle importiert |
| Verifizierungsgrad | ungeprüft (nur importiert) · Quelle gesichtet · Dokument geprüft |
| Letzte Überprüfung | wann wir den Datensatz zuletzt kontrolliert haben |
| Kennzahl (optional) | z. B. Umsatzanteil Kohle in % |

## Belegstatus: Beweisstatus statt Quellenanzahl

Massgebend ist der **stärkste sicher zugeordnete Beleg** – nicht, wie viele Quellen dasselbe
berichten. Zwei Zeitungsartikel, die denselben unbelegten Vorwurf wiederholen, sind kein Beweis.
Ein rechtskräftiges Gerichtsurteil kann dagegen allein genügen, um eine gerichtliche
Feststellung wiederzugeben.

| Status | Bedingung |
|---|---|
| **Gerichtlich/behördlich festgestellt** | Gerichtsurteil oder behördliche Feststellung, Verfahren rechtskräftig abgeschlossen, **Originaldokument von uns geprüft** |
| **Entscheid gemeldet – Prüfung ausstehend** | wie oben, aber unsere Dokumentprüfung fehlt noch |
| **Verfahren laufend** | Gericht/Behörde, Verfahren nicht abgeschlossen oder Status unbekannt; auch Anklagen und Untersuchungen |
| **Dokumentiert durch NGO/Institution** | Recherche einer NGO mit Belegen oder Ausschlussentscheid einer Institution |
| **Nur Medienberichte** | ausschliesslich Medienberichte – auch mehrere heben die Stufe nicht an |
| **Beleg vorhanden, Zuordnung unsicher** | Belege existieren, aber die Zuordnung zum Unternehmen bzw. Wertpapier ist nicht sicher genug |
| **Keine Hinweise in geprüften Quellen** | eine Quelle hat das Unternehmen für dieses Kriterium nachweislich geprüft und nichts gefunden |
| **Unbekannt** | keine Quelle deckt das Unternehmen ab, oder der Emittent ist nicht identifiziert |
| **Nicht anwendbar** | z. B. Barmittel, Devisentermingeschäfte |

Wie viele **verschiedene Herausgeber** berichten, wird als Kontext angezeigt, ändert die Stufe
aber nicht.

## Regeln

1. **Kein Gesamtwert, keine Verrechnung.** Jedes Kriterium steht für sich. Ein schwerer
   Befund (z. B. Zwangsarbeit) wird nie durch gute Werte anderswo (z. B. CO₂) ausgeglichen.
2. **Ein Vorwurf ist kein bewiesener Verstoss.** Texte nennen immer Art, Herausgeber und Datum
   («Laut Gerichtsurteil … vom …», «Vorwurf laut NGO … – nicht bestätigt»).
3. **Automatisierung bestätigt nichts.** Neu importierte Datensätze sind «ungeprüft».
   «Festgestellt» setzt eine menschliche Prüfung des Originaldokuments voraus.
4. **Fehlende Daten sind kein Nachhaltigkeitsnachweis.** «Keine Hinweise» gibt es nur mit
   nachgewiesener Abdeckung, sonst «unbekannt».
5. **Stellungnahmen und Abhilfe** werden neben dem Befund gezeigt, entkräften ihn aber nicht.
6. **Selbstauskünfte** der Unternehmen begründen keinen Befund (weder belastend noch entlastend).
7. **Konzernstrukturen:** Belege zur Muttergesellschaft werden nur über **verifizierte**
   Beziehungen übernommen. Unverifizierte Beziehungen werden angezeigt, aber nicht übernommen.
8. **Schwellenwerte:** Solange ein Schwellenwert nicht festgelegt ist, wird eine gemeldete
   Kennzahl angezeigt und als Beleg behandelt (mit Hinweis). Liegt sie unter einem
   festgelegten Schwellenwert, zählt sie nicht als Befund.

## Zuordnung zu Unternehmen

ISIN (Wertpapier) und LEI (Rechtsträger) werden strikt getrennt. Zuordnungen haben eine
Methode und ein Vertrauen:

| Methode | Vertrauen | zählt für Status |
|---|---|---|
| LEI-Treffer | hoch | ja |
| ISIN → Wertpapier → Emittent | Vertrauen der Wertpapier-Zuordnung | ab «mittel» |
| nur Namensabgleich | tief | nein → «Zuordnung unsicher» |
| Name gleich, LEI widerspricht | – | keine Zuordnung (anderer Rechtsträger) |
| mehrdeutiger Name | – | keine Zuordnung |

Nicht zuordenbare Sachverhalte werden in der Analyse separat aufgelistet.

## Datenqualität beim Import

- Pflichtfelder, Formate, ISIN- und LEI-Prüfziffern, gültige Kriterien, keine Zukunftsdaten
- Gerichtsurteile nur von Gerichten, behördliche Feststellungen nur von Behörden
- Fondsgewichte: Summe muss zwischen 95 und 105 % liegen (Warnung ausserhalb 99,5–100,5 %)
- Duplikate: exakte Duplikate werden entfernt (Warnung), widersprüchliche Einträge mit
  gleichem Schlüssel lehnen die Datei ab, inhaltliche Duplikate werden gemeldet
- **Ein einziger Fehler lehnt den gesamten neuen Datenstand ab.** Der letzte gültige Stand
  bleibt aktiv. Abgelehnte Rohdaten werden zur Nachvollziehbarkeit aufbewahrt.

## Bekannte Grenzen der Methodik

- Ob zwei Berichte unabhängig recherchiert sind, kann das System nicht erkennen. Es zählt
  Herausgeber, nicht unabhängige Recherchen. Deshalb hebt die Anzahl die Stufe nicht an.
- Freisprüche oder aufgehobene Urteile sind noch nicht als eigene Art modelliert.
- Die Abdeckung einer Quelle wird pro Unternehmen und Kriterium erfasst. Für echte Quellen
  muss das Abdeckungsuniversum pro Quelle sorgfältig dokumentiert werden.
