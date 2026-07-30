# Edge Cases und typische falsche Lösungen

Eine Prüfungsdatenbank ist dann gut, wenn eine falsche Abfrage ein *sichtbar anderes*
Ergebnis liefert. Zufallsdaten erfüllen das nur zufällig. Plane deshalb für jede Aufgabe:
welcher Fehler ist typisch, und welche Datenkonstellation deckt ihn auf? Die Spalte
„Daten“ sagt, wie du die Konstellation in der Spec herstellst.

## JOIN

| Typischer Fehler | Daten, die ihn aufdecken | Herstellen mit |
|---|---|---|
| INNER statt LEFT JOIN | Elternzeilen ohne Kinder | `_childless`-Fixture oder `coverage` < 1 |
| LEFT JOIN von der falschen Seite / Kinder ohne Eltern fehlen | Kindzeilen mit NULL im FK | nullable FK mit `null_ratio` |
| Bedingung auf rechte Tabelle im WHERE statt im ON (LEFT wird INNER) | Eltern, die Kinder haben, aber keine, die die Bedingung erfüllen | Fixture-Kinder nur außerhalb des gefragten Zeitraums |
| LEFT JOIN, aber zweiter JOIN in der Kette als INNER | Mittlere Tabelle hat Zeilen ohne Kinder in der dritten | `coverage` < 1 auf dem zweiten FK |
| Fan-out: SUM über Elternspalte nach JOIN mit zwei Kindtabellen | Eltern mit ≥ 2 Kindern in *beiden* Tabellen | Fixtures |

## Aggregation

| Typischer Fehler | Daten, die ihn aufdecken | Herstellen mit |
|---|---|---|
| COUNT(*) statt COUNT(spalte) nach LEFT JOIN | Kinderlose Eltern (zeigen 1 statt 0) | wie oben |
| COUNT(spalte) statt COUNT(DISTINCT spalte) | Wiederholte Werte innerhalb einer Gruppe (Kunde mietet dasselbe Gerät zweimal) | kleiner Wertepool, `skew` |
| GROUP BY Name statt Id | Zwei verschiedene Personen mit gleichem Namen, **beide** mit Kindern | zwei Fixtures mit gleichem Namen und expliziten Ids, Fixture-Kinder für beide |
| `>` statt `>=` im HAVING | Gruppe genau auf dem Schwellwert | Schwellwert nach dem Build aus der Statistik wählen oder per Fixture erzeugen |
| WHERE statt HAVING (oder umgekehrt) | Gruppen, die erst aggregiert über/unter der Grenze liegen | Aufgabe passend formulieren |
| AVG ignoriert NULL (vs. als 0 gezählt) | NULLs in der gemittelten Spalte | `null_ratio` |
| SUM liefert NULL statt 0 | Gruppe, deren Werte alle NULL sind, oder kinderlose Eltern | Fixture bzw. `_childless` |
| TOP 1 / LIMIT 1 statt „alle mit Maximum“ | Gleichstand beim Maximum | `post_sql` nach Blick auf die Verteilung |

## Unterabfragen

| Typischer Fehler | Daten, die ihn aufdecken | Herstellen mit |
|---|---|---|
| NOT IN statt NOT EXISTS | Ein NULL in der Spalte der Unterabfrage (dann liefert NOT IN nichts) | nullable FK mit `null_ratio` |
| JOIN statt EXISTS (Duplikate) | Eltern mit ≥ 2 passenden Kindern | Standard bei `skew` > 0 |
| „Alle Kinder erfüllen X“ als EXISTS statt NOT EXISTS … NOT X | Eltern mit gemischten Kindern (X und nicht X) **und** kinderlose Eltern (erfüllen „alle“ trivial) | Fixtures; Aufgabentext muss festlegen, ob Kinderlose dazugehören |
| Korrelation vergessen | Unterschiedliche Werte pro Eltern | meist automatisch gegeben |
| Skalare Unterabfrage liefert mehrere Zeilen | Lookup per Name, wenn der Name doppelt ist | doppelter Name per Fixture (dann Aufgabe per Id stellen oder bewusst prüfen) |

## DML

| Typischer Fehler | Daten, die ihn aufdecken | Herstellen mit |
|---|---|---|
| Eltern löschen ohne vorher Kinder zu löschen | Der zu löschende Elternteil hat Kinder → FK-Fehler | Aufgabe auf einen Elternteil mit Kindern beziehen |
| WHERE zu weit/eng (fehlende Bedingung) | Zeilen, die nur eine der Bedingungen erfüllen | Daten mit gemischten Merkmalen |
| `= NULL` statt `IS NULL` | NULLs in der Filterspalte | `null_ratio` |
| INSERT mit Lookup per Name, Name nicht eindeutig | doppelter Name | Fixture |
| UPDATE mit korrelierter Unterabfrage setzt NULL statt 0 | Zeilen ohne passende Kinder | `_childless` |

## Datum und Zeit

| Typischer Fehler | Daten, die ihn aufdecken | Herstellen mit |
|---|---|---|
| `BETWEEN '2026-06-01' AND '2026-06-30'` auf datetime | Wert am letzten Tag nach 00:00 | Fixture mit z. B. `"2026-06-30 16:30:00"` |
| `>` statt `>=` an der Untergrenze | Wert genau um 00:00 am ersten Tag | Fixture |
| Monat ohne Jahr gefiltert | Daten über mehr als ein Jahr | `range` über Jahresgrenze |

## Exakte Zahlen statt Zufall

Viele Fälle hängen an einer genauen Zahl: Die Gruppe liegt *genau* auf dem HAVING-Wert,
beide „Maria Huber“ überschreiten die Grenze erst gemeinsam. Mit generierten Kindern
schwanken solche Zahlen. Robust ist ein `_childless`-Elternteil mit expliziter Id, der nur
Fixture-Kinder bekommt. Seine Zählwerte stehen dann exakt fest.

## Wenn die Studierenden nur die Zeilenanzahl bekommen

Dann deckt die Datenbank einen Fehler nur auf, wenn sich die **Zeilenzahl** ändert. Die
meisten Aggregationsfehler (COUNT(*), GROUP BY Name, fehlendes DISTINCT, AVG mit NULL)
ändern aber nur Werte. Formuliere solche Aufgaben mit einem Filter auf das Aggregat
(`HAVING COUNT(…) >= 4`), sodass der falsche Wert eine Gruppe über oder unter die Grenze
schiebt. Prüf mit `check_queries.py --mode count`.

## Gestaltung der Abfragen

- **3–15 Ergebniszeilen.** Studierende vergleichen Ergebnisse optisch. Bei 0 oder 1 Zeile
  liefern viele falsche Abfragen zufällig auch das richtige Ergebnis, bei 40 Zeilen prüft
  niemand mehr nach.
- **Feste Datumswerte statt CURRENT_DATE/GETDATE().** Sonst ändert sich das Ergebnis mit dem
  Prüfungstag, und die Lösung in der Angabe stimmt nicht mehr.
- **ORDER BY eindeutig machen** (Tie-Breaker wie `, Id`), wenn die Reihenfolge zählt. Bei
  Gleichständen sortiert jede Datenbank anders.
- **Aufgabentext eindeutig formulieren.** „Kategorien ohne Fall mit 0 anzeigen“ statt sich
  darauf zu verlassen, dass Studierende den LEFT JOIN erraten. Der Edge Case prüft das
  Können, nicht das Rätselraten.

## Dialekt-Fallen

Diese Unterschiede meldet `verify_dump.py` als DIFF oder ERROR. Löse sie über
`sql_by_dialect`.

| Thema | SQLite | SQL Server | PostgreSQL |
|---|---|---|---|
| Bool-Literal | `1`/`0` oder `TRUE`/`FALSE` | nur `1`/`0` | nur `TRUE`/`FALSE` |
| Erste n Zeilen | `LIMIT n` | `TOP n` / `OFFSET … FETCH` | `LIMIT n` |
| AVG über int | Kommazahl | **ganzzahlig** → `AVG(CAST(x AS DECIMAL(10,2)))` | Kommazahl |
| Ganzzahl-Division `a / b` | ganzzahlig | ganzzahlig | ganzzahlig |
| Jahr aus Datum | `strftime('%Y', d)` (Text!) | `YEAR(d)` | `EXTRACT(YEAR FROM d)` |
| String-Verkettung | `\|\|` | `+` oder `CONCAT` | `\|\|` oder `CONCAT` |
| LIKE | case-insensitiv (ASCII) | case-insensitiv (Standard-Collation) | **case-sensitiv** (`ILIKE`) |
| ROUND-Ergebnis | REAL | behält Scale (`12.50`) | NUMERIC |
| ROUND(AVG(dezimal)) genau auf …5 | AVG rechnet binär: −24,35 ist −24,3499…, ROUND(…, 1) ergibt **−24,3** | exakt, ergibt −24,4 | exakt, ergibt −24,4 |

Die letzte Zeile ist tückisch, weil sie nur bei einzelnen Gruppen auftritt. Das Aufgabenblatt
wird aus SQLite erzeugt und zeigt dann einen anderen Wert, als die Studierenden auf der
Zieldatenbank sehen. `verify_dump.py` meldet das als DIFF. Runde auf so viele Stellen, dass der
exakte Wert ohne Rundung darstellbar ist (meist eine Stelle mehr). Alternativ änderst du die
Daten, sodass kein Mittelwert auf der Grenze liegt.

Datumsvergleiche mit ISO-Literalen (`BroughtAt >= '2026-06-01'`) funktionieren in allen drei
Systemen gleich. Bevorzuge sie gegenüber Datumsfunktionen.
