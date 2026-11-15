# Kriterien und Bewertungsprofil

Die Kriterien stehen an genau einer Stelle: `src/transparenz/config/criteria.toml`
(Schema 2). Screening-Engine, Pilotbericht und Website lesen dieselbe Datei. Die Tabelle oben
auf dieser Seite wird direkt daraus erzeugt.

## Zwei Dinge, die getrennt bleiben

1. **Belege** stammen aus Quellen. Jede Aussage nennt Quelle und Datum («Laut … vom …»).
2. **Die Bewertung** ist unsere Entscheidung. Das Profil legt fest, welcher belegte Sachverhalt
   als «Konflikt mit dem Profil» gilt. Das ist kein Urteil einer Quelle und kein Urteil über
   ein Unternehmen als Ganzes.

Wer anders werten will, braucht ein anderes Profil, nicht andere Belege.

## Startprofil «streng»

Zwölf aktive Kriterien in vier Themen:

| Thema | Kriterien |
|---|---|
| Klima | Kohle · Fossile Expansion |
| Umwelt | Entwaldung · Biodiversität und Ökosysteme · Wasser und Meeresressourcen · Umweltverschmutzung und gefährliche Stoffe · Ressourcen, Abfall und Kreislaufwirtschaft |
| Soziales | Waffen · Zwangs- und Kinderarbeit · Arbeitsrechte und Arbeitsschutz · Menschenrechte und Landrechte |
| Unternehmensführung | Korruption |

Zwei Arten von Kriterien:

- **Tätigkeit oder Beteiligung** (Kohle, fossile Expansion, Waffen): Ein dokumentierter
  Sachverhalt genügt, zum Beispiel eine belegte Beteiligung an einer Anlage.
- **Verhalten** (alle übrigen): Nur eine bestätigte Feststellung eines Gerichts oder einer
  Behörde, deren Dokument wir geprüft haben, ist ein Konflikt. Verdacht, laufende Verfahren
  und Medienberichte werden gezeigt, zählen aber nicht.

## Grundsätze

- Kriterien werden **einzeln** beurteilt. Es gibt keinen Gesamtwert und keine Verrechnung.
- «Unbekannt» heisst: Keine freigegebene Quelle deckt das Kriterium ab. Das ist nie
  «unbedenklich». Für echte Daten ist das heute bei zehn der zwölf Kriterien der Stand; nur
  Kohle und fossile Expansion haben eine freigegebene Quelle. (Die Website zeigt fiktive
  Demodaten.)
- Länder- und Branchenrisiken sind Kontext, nie ein Beleg gegen ein Unternehmen.
- Sanktionen sind Belege mit ihrem amtlichen Sanktionsgrund, kein eigenes Kriterium.
- Emissionen und andere Mengen sind **Kennzahlen** mit Jahr, Abgrenzung, Einheit, Methode und
  Abdeckung. Sie haben keinen Ausschlusswert, solange Vergleichbarkeit fehlt.
- **Kategorien entscheiden mit.** Hat ein Kriterium Kategorien mit unterschiedlicher Wirkung
  (zum Beispiel Waffenarten, Dual-Use-Güter, Handel), löst nur ein Beleg mit einer
  konfliktauslösenden Kategorie einen Konflikt aus. Nennt ein Beleg keine Kategorie, bleibt
  die Wirkung offen: kein Konflikt, mit Hinweis.
- Historische Fälle wirken nicht ewig. Bei Korruption beginnt die Wirkung mit dem Abschluss
  des Verfahrens (oder dem späteren Ende der Tat) und dauert fünf Jahre, so lange wie die
  Höchstdauer des Ausschlusses von öffentlichen Aufträgen im EU-Vergaberecht. Solange Folgen
  fortbestehen (Auflagen, Aufsicht, Sperre), endet sie nicht. Hat eine Behörde die Abhilfe
  bestätigt, endet sie frühestens nach drei Jahren. (Vorschlag, zu bestätigen.)
- Regeln mit dem Vermerk «Vorschlag» sind noch nicht bestätigt. Das betrifft die Ausschlüsse
  je Waffenkategorie und die Konfliktregeln der sechs neueren Kriterien.

## Beziehung zwischen Unternehmen und Anlage

Eine Besitzkette sagt, wer an wem wie viel hält, aber nicht auf wessen Rechnung. Deshalb hat
jede Art von Beziehung ihre eigene Regel:

| Beziehung | Wirkung im Profil |
|---|---|
| Eigentum auf eigene Rechnung (direkt, über Töchter oder eigene Projektbeteiligung) | Konflikt bei Kohle und fossiler Expansion |
| Finanzbeteiligung eines Finanzinstituts, Rechnung ungeklärt (unter 20 % an einer kotierten Gesellschaft) | gesondert, kein Konflikt (Vorschlag) |
| Vermögensverwaltung für Kunden oder Fonds | gesondert, kein Konflikt |
| Verwahrung von Wertpapieren für Dritte | gesondert, kein Konflikt |
| Kreditvergabe und Projektfinanzierung | gesondert, kein Konflikt (eigene Regel offen) |
| Betrieb einer Anlage | gesondert (Vorschlag: Konflikt bei Kohle, noch offen) |
| Stromabnahme und andere Lieferverträge | gesondert, keine Regel |

Ein Anteil an einer Vermögensverwaltungsgesellschaft ist kein anteiliges Eigentum an den
Anlagen ihrer Kunden. Eine mögliche Verantwortung durch Verwaltung oder Finanzierung braucht
eine eigene, offengelegte Regel; sie ist noch nicht festgelegt.

## Änderungen

Jede inhaltliche Änderung erhöht `profile_version` in `criteria.toml` und wird in
`docs/DECISIONS.md` begründet. Die Website zeigt Profilname, Version und Datum.

## Vorgeschlagen, noch nicht aktiv

Ölsand, Arktis und Fracking · Tabak · Irreführende Umweltaussagen (Greenwashing) · Tierwohl.
Sie werden nicht ausgewertet, bis ein Entscheid vorliegt.
