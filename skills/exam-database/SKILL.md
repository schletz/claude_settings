---
name: exam-database
description: Erstellt Musterdatenbanken für SQL-Prüfungen und -Übungen. Schema und Musterdaten bekommen gezielt eingebaute Edge Cases, sodass typische falsche Lösungen (INNER statt LEFT JOIN, COUNT(*) statt COUNT(spalte), NOT IN mit NULL, GROUP BY Name statt Id, BETWEEN auf Datetime …) sichtbar andere Ergebnisse liefern. Liefert einen in Docker geprüften SQL-Dump (Schema + Daten) für SQLite, SQL Server oder PostgreSQL, auf Wunsch die SQLite-Datei und Prüfungsaufgaben mit Ergebnistabelle bzw. Zeilenanzahl als Markdown, AsciiDoc/PDF und SQL-Abgabedatei, jeweils mit Musterlösung daneben. Nutze diesen Skill immer, wenn der Nutzer eine Datenbank, Musterdaten, Testdaten, Beispieldaten oder einen SQL-Dump für eine Prüfung, einen Test, eine Schularbeit, eine Übung oder den Unterricht braucht, oder SQL-Abfragebeispiele/Aufgaben zu einem Schema erstellen will — auch wenn er nur ein Thema nennt ("mach mir eine Prüfungs-DB zu E-Scootern") oder auf Englisch "sample database for an SQL exam", "seed data with edge cases" sagt. Wird oft zusammen mit dem Skill ideas verwendet.
---

# Prüfungsdatenbank erstellen

Eine Prüfungsdatenbank muss drei Dinge leisten. Sie entscheidet die häufigsten
SQL-Fehler: Eine falsche Abfrage liefert ein anderes Ergebnis als die richtige. Die
Ergebnisse sind klein genug, dass Studierende sie mit der Angabe vergleichen können.
Und der Dump läuft auf der Zieldatenbank ohne Nacharbeit.

Reine Zufallsdaten schaffen das nicht: Ob es einen Kunden ohne Bestellung gibt, ist dann
Glückssache. Deshalb läuft die Arbeit so: Du (das LLM) entwirfst Schema, Fachvokabular und
Edge Cases in einer JSON-Spec. Die Skripte erzeugen daraus mit Faker die Datenmenge.
Danach prüfst du mit Abfragen und bewusst falschen Varianten, ob die Daten die Fehler
wirklich aufdecken.

## Werkzeuge

Alle Skripte liegen in `<skill-dir>/scripts/` und werden mit `python <skill-dir>/scripts/<name>.py`
aufgerufen. Sie brauchen das Paket `faker` (falls der Import scheitert: `pip install faker`).
Für SQL Server und PostgreSQL brauchst du Docker; die Images
`mcr.microsoft.com/mssql/server:2025-latest` und `postgres` werden bei Bedarf geladen.

| Skript | Zweck |
|---|---|
| `build_db.py <spec.json>` | Baut `<spec>.db` neu und zeigt Statistik: kinderlose Eltern pro FK, NULLs, doppelte Namen |
| `check_queries.py <db> <queries.json> [--mode count]` | Führt Lösungen und falsche Varianten aus; FAIL = Fehler wird von den Daten nicht aufgedeckt |
| `run_sql.py <db> "<sql>"` | Daten erkunden (läuft auf einer Kopie, ändert nichts) |
| `export_dump.py <spec.json> <db> --dialect <d>` | Schreibt `<db>_<d>.sql` |
| `verify_dump.py <dump> --dialect <d> --db <db> --queries <queries.json>` | Lädt den Dump in einen frischen Container, vergleicht alle Lösungen mit SQLite, entfernt den Container |
| `render_tasks.py <db> <queries.json> --dialect <d> --mode result\|count\|both\|none --spec <spec.json> [--title <t>] [--intro <datei>] [--er-layout <datei.puml>] -o <datei.md\|datei.adoc>` | Aufgabenblatt mit Datenmodell und erwarteten Ergebnissen als Markdown oder AsciiDoc, dazu `<datei>_loesung.<endung>` |
| `render_answer_sheet.py <db> <queries.json> --dialect <d> --mode result\|count\|both\|none -o <datei.sql>` | SQL-Angabedatei, in die die Studierenden ihre Lösungen schreiben, dazu `<datei>_loesung.sql` |

Leg für jede Datenbank einen eigenen Ordner im Arbeitsverzeichnis an (z. B. `repair_cafe/`).
Spec und Abfragedatei sind Teil des Ergebnisses: Mit ihnen kann der Nutzer die Datenbank
später reproduzieren oder anpassen.

## 1. Rahmen klären

Du brauchst: Thema/Domäne, Zieldatenbank(en), ob Prüfungsaufgaben gewünscht sind (wie
viele, welche Themen) und was die Studierenden in der Angabe über die richtige Lösung
erfahren: die Ergebnistabelle, nur die Zeilenanzahl oder gar nichts. Das Letzte fragst
du bei Aufgaben immer nach, auch wenn der Rest klar ist. Es bestimmt, wie stark die
Prüfung selbstkontrolliert ist, und das kannst du nicht erraten. Was der Prompt sonst
nicht hergibt und das Ergebnis ändert, fragst du
in *einer* Rückfrage ab. Die Zieldatenbank gehört dazu. Fehlt nur das Thema und
der Nutzer will etwas Aktuelles, hol dir mit dem Skill `ideas` Vorschläge.

Auch wenn keine Aufgaben bestellt sind, schreibst du Prüfabfragen für die vier Themen
(JOIN, Aggregation, Unterabfragen, DML). Ohne sie gibt es keinen Nachweis, dass die
Edge Cases existieren.

## 2. Schema entwerfen

Ein gutes Prüfungsschema bietet Stoff für alle Themen, ohne zu überfordern:

- **4–7 Tabellen**, darunter eine 1:n-Kette über mindestens zwei Ebenen (für Mehrfach-Joins),
  eine n:m-Tabelle mit eigenem Attribut (z. B. Menge) und eine Lookup-Tabelle. Eine
  Selbstreferenz (Mentor, Vorgesetzte) ist eine gute Ergänzung für Fortgeschrittene.
- **Spalten für jedes Thema**: datetime/date (Zeiträume, Grenzen), decimal (SUM/AVG),
  Status oder Kategorie (GROUP BY), nullable Attribute und mindestens ein nullable
  Fremdschlüssel (NULL-Logik, NOT IN).
- **Größen**: Lookups 3–8, Stammdaten 10–40, Bewegungsdaten 50–200 Zeilen. Groß genug, dass
  falsche Abfragen auffallen, klein genug zum Nachprüfen.
- **Bezeichner** englisch, PascalCase, Einzahl, `Id` als PK, FKs als `<Tabelle>Id`, sofern
  der Nutzer keine eigene Konvention hat. Nur ASCII und keine reservierten Wörter; die
  Spec-Prüfung lehnt `Order`, `User` usw. ab, weil die Bezeichner unquotiert in allen
  Dialekten funktionieren sollen.
- **Fachvokabular kommt von dir** als `choice`-Listen (Produktnamen, Kategorien, Status).
  Faker liefert nur, was er gut kann: Namen, E-Mails, Adressen. Ein Faker-Wort als
  Produktname ergibt Unsinn, den Studierende sofort bemerken.
- **Jede Tabelle bekommt eine `description`** für die Studierenden: was eine Zeile ist,
  Einheiten, was NULL bedeutet. Sie erscheint im Datenmodell des Aufgabenblatts, sonst
  müssen die Studierenden die Bedeutung aus den Spaltennamen erraten.
- Daten sind österreichisch-realistisch (`locale` `de_AT`). Setz `reference_date`, damit der Build
  reproduzierbar bleibt.

Das Format steht in `references/spec-format.md`. Lies es, bevor du die erste Spec schreibst.

## 3. Edge Cases planen und bauen

Bevor du Daten generierst, überlege für jede geplante Aufgabe, welcher typische Fehler sie
verfehlen soll und welche Datenkonstellation ihn aufdeckt. Der Katalog in
`references/edge-cases.md` listet die gängigen Fälle samt passendem Spec-Mittel. Sichere
jeden Edge Case, von dem eine Aufgabe abhängt, gezielt ab: über Fixtures, `coverage`
oder `post_sql`. Zufällig vorhandene Konstellationen sind nicht garantiert.

Wo eine Aufgabe exakte Zahlen braucht (HAVING-Grenze, zwei gleichnamige Personen mit
bekannter Fallzahl), nimm einen `_childless`-Elternteil mit expliziter Id und gib ihm nur
Fixture-Kinder. Generierte Kinder kommen dann nicht dazu, und die Zahl steht exakt fest,
egal wie der Zufall fällt.

Zusammenhänge zwischen Spalten oder Tabellen, die Generatoren nicht ausdrücken (Kategorie
passt zur Jahreszeit, Mannschaft nur bei Einsätzen der eigenen Ortsstelle), stellst du mit
`post_sql` her. Unsinnige Kombinationen fallen Studierenden genauso auf wie Faker-Unsinn.
Muster dafür stehen in `references/spec-format.md`.

```
python <skill-dir>/scripts/build_db.py repair_cafe/repair_cafe.json
```

Lies die Statistik: Gibt es kinderlose Eltern dort, wo du LEFT JOINs prüfen willst? NULLs im
FK für die NOT-IN-Aufgabe? Doppelte Namen für die GROUP-BY-Falle? Mit `run_sql.py` siehst
du dir Verteilungen an, z. B. um einen HAVING-Schwellwert so zu wählen, dass eine Gruppe
genau darauf liegt.

## 4. Abfragen schreiben und prüfen

Schreib `queries.json` (Format: `references/queries-format.md`). Jede Abfrage bekommt
mindestens eine falsche Variante. Nimm die Fehler, die Studierende bei *dieser* Aufgabe
tatsächlich machen, nicht beliebige.

```
python <skill-dir>/scripts/check_queries.py repair_cafe/repair_cafe.db repair_cafe/queries.json
```

Bekommen die Studierenden nur die Zeilenanzahl, prüf mit `--mode count`. Eine falsche Lösung
mit anderen Werten, aber gleicher Zeilenzahl, fällt dann nämlich niemandem auf, und der
Check meldet sie als FAIL. Aggregationsfehler (COUNT(*), GROUP BY Name, fehlendes DISTINCT)
ändern meist nur Werte. Bau solche Aufgaben deshalb mit einem HAVING, das den falschen
Wert in eine andere Zeilenzahl übersetzt.

- **FAIL**: Die falsche Variante liefert dasselbe Ergebnis. Ändere die **Spec** (Fixture,
  `coverage`, `post_sql`), baue neu und prüfe erneut. Patch die `.db` nicht direkt: Die Spec
  ist die einzige Quelle, aus der Datenbank und Dumps reproduzierbar entstehen. Eine
  handgepatchte Datei geht beim nächsten Build verloren.
- **WARN zu viele/keine Zeilen**: Grenze die Aufgabe ein (Zeitraum, HAVING) oder passe die
  Daten an. Ziel sind 3–15 Zeilen.
- **WARN Fehler in Variante**: Prüfe, ob der Fehler gewollt ist (bei DML z. B. die
  FK-Verletzung beim Löschen von Eltern) oder ob die Variante nur falsch getippt ist.

Wiederhole, bis alle Abfragen ok sind. Jede generierte Zeile hat ihren eigenen Zufallsstrom:
Eine zusätzliche Fixture ändert die Werte der übrigen Zeilen nicht, und Kindzeilen bleiben
fast immer bei ihren Eltern. Ids können sich verschieben, bereits geprüfte Edge Cases
bleiben also erhalten, solange sie nicht an einer generierten Id hängen.

## 5. Dialekt beachten

Schreib `sql` direkt im Zieldialekt, sofern es auch auf SQLite läuft. Sonst ergänzt du
`sql_by_dialect` (Overrides für `sqlite`, `mssql`, `postgres`). Die häufigsten Fallen
(Bool-Literale, TOP/LIMIT, AVG über int in SQL Server, case-sensitives LIKE in PostgreSQL,
ROUND eines Mittelwerts, der genau auf …5 liegt) stehen am Ende von `references/edge-cases.md`. Datumsvergleiche mit ISO-Literalen
(`>= '2026-06-01'`) sind portabel; bevorzuge sie gegenüber Datumsfunktionen.

## 6. Exportieren und im Container prüfen

Für jede Zieldatenbank:

```
python <skill-dir>/scripts/export_dump.py repair_cafe/repair_cafe.json repair_cafe/repair_cafe.db --dialect mssql
python <skill-dir>/scripts/verify_dump.py repair_cafe/repair_cafe_mssql.sql --dialect mssql --db repair_cafe/repair_cafe.db --queries repair_cafe/queries.json
```

Der Dump enthält DROP/CREATE/INSERT und lässt sich mehrfach ausführen. Er legt keine
Datenbank an: Bei SQL Server wählt der Nutzer vorher eine Datenbank aus. Die Daten stammen
1:1 aus der geprüften SQLite-Datei, inklusive Fixtures und `post_sql`.

`verify_dump.py` startet einen frischen Container (SQL Server ca. 10 s), lädt den Dump,
vergleicht das Ergebnis jeder SELECT-Lösung mit SQLite und löscht den Container wieder.
DML-Lösungen laufen dort in einer zurückgerollten Transaktion. Verglichen wird nur die
Anzahl betroffener Zeilen, den Datenbestand danach prüft nur der SQLite-Check.

- **ERROR beim Laden**: Meist ein Spec-Problem (z. B. CHECK-Ausdruck mit SQLite-Syntax).
  Spec korrigieren, neu bauen, neu exportieren.
- **DIFF**: Die Lösung verhält sich im Zieldialekt anders. Ergänze einen `sql_by_dialect`-Override,
  sodass dasselbe Ergebnis herauskommt. Erst dann stimmen die Ergebnistabellen im
  Aufgabenblatt, denn sie werden aus SQLite erzeugt.
- Läuft Docker nicht, sag das dem Nutzer und liefere den Dump als *ungeprüft* aus.

## 7. Ausliefern

Im Ordner der Datenbank liegen am Ende:

- `<name>_<dialekt>.sql` – immer, für jede Zieldatenbank, auch für SQLite
- `<name>.db` – entsteht bei jedem Build und wird für Check und Aufgabenblatt gebraucht. Will
  der Nutzer SQLite, ist sie zusätzlich die fertige Datenbankdatei für die Studierenden
- `<name>_aufgaben.md` oder `<name>_aufgaben.adoc` – wenn Aufgaben gewünscht sind, erzeugt
  mit `render_tasks.py --spec`; die Endung von `-o` bestimmt das Format. `--mode` je nach
  Wunsch: `result` (Ergebnistabelle), `count` (nur Zeilenanzahl), `both` oder `none` (keine
  Information zur Lösung). Der Datenmodell-Abschnitt zeigt Typen, Schlüssel und die
  `description` jeder Tabelle aus der Spec. Was NULL in einer Spalte heißt oder welche
  Status-Werte es gibt, gehört dorthin. Ausgangslage und Abgabehinweise schreibst du in
  eine Datei im Zielformat und gibst sie mit `--intro` mit. Ändere die erzeugten Blätter
  nicht von Hand: Angabe und Lösung müssen gleich bleiben, und ein neuer Lauf überschreibt
  beide
- `<name>_angabe.sql` – wenn Aufgaben gewünscht sind, erzeugt mit `render_answer_sheet.py`
  und demselben `--mode` wie das Aufgabenblatt. Die Studierenden schreiben ihre Lösungen
  hinein und geben sie ab. Ändere das Layout nicht von Hand: Die Trennzeilen und die
  Überschriften `AUFGABE n von X` sind die Anker für die automatisierte Bewertung
- Spec und `queries.json` – zum Reproduzieren

Neben jeder Datei, die die Studierenden bekommen, liegt ihre Musterlösung:
`<datei>_loesung.<endung>`, also derselbe Inhalt mit „(Lösung)“ im Titel und dem
Lösungs-SQL im Zieldialekt direkt unter jeder Aufgabe. Die Angabe selbst enthält
dann keine Lösungen. So muss vor dem Austeilen nichts abgeschnitten werden, und beim
Korrigieren und Besprechen haben Lehrende und Studierende dieselbe Seite vor sich.
`render_tasks.py` und `render_answer_sheet.py` schreiben das Paar mit `-o` automatisch.
Machst du aus der Angabe ein anderes Format (PDF, Word), schreibst du die Lösung im
selben Format daneben.

### AsciiDoc und PDF

Will der Nutzer ein PDF oder AsciiDoc, erzeugst du `<name>_aufgaben.adoc` und konvertierst
Angabe und Lösung mit dem Skill `asciidoc`. Das Datenmodell ist dort ein PlantUML-ER-Diagramm
ohne Layout-Vorgaben. Wie PlantUML ein Schema anordnet, hängt von seiner Form ab: Dieselbe
Anweisung, die ein Diagramm rettet, macht ein anderes unlesbar. Sieh dir deshalb die
gerenderten Seiten an (z. B. mit `pypdfium2` als PNG). Erst wenn das Diagramm schlecht
aussieht (überkreuzte Linien, Beschriftungen auf Linien, zu kleine Schrift), schreibst du die
nötigen PlantUML-Zeilen in `<name>_er_layout.puml` (etwa `left to right direction`,
`A -[hidden]- B`) und renderst mit `--er-layout` neu. Die Datei bleibt erhalten, wenn du
neu renderst, und das Diagramm entsteht weiterhin aus der aktuellen Spec.

Die Lesbarkeit hat Vorrang vor der Seitenzahl. Die Studierenden lesen in der Prüfung
ständig Spaltennamen aus dem Diagramm ab, oft auf Papier. Die Schrift im Diagramm darf
deshalb nicht deutlich kleiner sein als der Text in den Ergebnistabellen. Wird sie das,
weil eine Layout-Anweisung das Diagramm in die Seitenbreite quetscht, nimm die Anweisung
zurück. Ein Diagramm auf einer eigenen Seite und eine halb leere Seite davor sind dann
in Ordnung. Verkleinere ein Diagramm nie, nur um Seiten zu sparen.

Fass für den Nutzer zusammen: Tabellen und Beziehungen in einem Satz pro Tabelle, welche
Edge Cases eingebaut sind (und welche Aufgabe sie prüfen) und das Ergebnis der
Container-Prüfung. Dass der Dump im Container geladen und alle Lösungen verglichen
wurden, ist die Zusage, auf die sich der Nutzer in der Prüfung verlässt. Nenn deshalb
ehrlich, was nicht geprüft werden konnte.
