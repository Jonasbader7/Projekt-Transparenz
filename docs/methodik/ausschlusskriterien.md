# Ausschlusskriterien (Startliste)

*Die Schwellenwerte legt Jonas fest. Bis dahin sind sie bewusst offen: gemeldete Kennzahlen
werden angezeigt, aber nicht gegen eine Grenze bewertet.* Technische Quelle der Kriterien:
`src/transparenz/config/criteria.toml`.

| Kriterium | Schwere | Kennzahl | Schwellenwert | Offene Definitionsfragen |
|---|---|---|---|---|
| Kohle | hoch | Umsatzanteil Kohle (%) | `[OFFEN: z. B. 0 %, 5 %, 10 %?]` | Abbau und Verstromung getrennt? Ausbaupläne unabhängig vom Umsatz ausschliessen? |
| Öl-/Gas-Expansion | hoch | – | `[OFFEN]` | Was gilt als «Expansion» (neue Felder, neue Lizenzen, Investitionen)? Stichtag? |
| Geächtete Waffen | schwer | – | `[OFFEN: Vorschlag Null-Toleranz]` | Umfang: Streumunition, Antipersonenminen, B- und C-Waffen; Atomwaffen? Schlüsselkomponenten? |
| Zwangs- und Kinderarbeit | schwer | – | `[OFFEN]` | Eigene Tätigkeit vs. Lieferkette; wie tief in der Lieferkette? |
| Entwaldung | hoch | – | `[OFFEN]` | Cut-off-Datum; Rohstoffe (Soja, Palmöl, Rind, Kakao, Holz); Lieferkette? |

## Grundsätze

- Kriterien werden **einzeln** beurteilt; es gibt keine Gewichtung untereinander.
- «Schwer» heisst: Grundrechte oder internationale Verbote betroffen. Auch das führt nicht zu
  einem Score – es dient der Priorisierung in der Recherche und Darstellung.
- Ein Schwellenwert gilt als **erreicht ab** dem festgelegten Wert (≥).
- Änderungen an Kriterien und Schwellenwerten werden in `docs/DECISIONS.md` begründet.

## Später zu prüfen (nicht Teil des ersten Meilensteins)

Tabak, konventionelle Waffen, Atomwaffen, Glücksspiel, Fracking/Ölsand, Menschenrechte allgemein
(z. B. Landrechte, Gewerkschaftsfreiheit), Korruption, Biodiversität.
