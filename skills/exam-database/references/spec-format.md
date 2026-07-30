# Schema-Spec (`<name>.json`)

Die Spec ist die einzige Quelle für Schema und Daten. `build_db.py` erzeugt daraus
die SQLite-Datenbank, `export_dump.py` die DDL für jeden Dialekt. Unbekannte Schlüssel
werden abgelehnt, damit Tippfehler nicht still ignoriert werden.

## Inhalt

- [Aufbau](#aufbau)
- [Tabellen](#tabellen)
- [Spalten](#spalten)
- [Generatoren (`gen`)](#generatoren-gen)
- [Fixtures](#fixtures)
- [post_sql](#post_sql)
- [Beispiel](#beispiel)

## Aufbau

| Schlüssel | Bedeutung |
|---|---|
| `name` | Name der Datenbank, wird für Dateinamen und den Dump-Header verwendet |
| `seed` | Zufallsstartwert. Gleiche Spec + gleicher Seed = gleiche Daten |
| `locale` | Faker-Locale, Standard `de_AT` |
| `reference_date` | Fixes „heute“ (ISO-Datum) für Standard-Datumsbereiche. Setzen, sonst ändern sich die Daten mit dem Build-Tag |
| `tables` | Liste der Tabellen, Reihenfolge beliebig (wird nach FK-Abhängigkeiten sortiert) |
| `fixtures` | Handgeschriebene Zeilen pro Tabelle (siehe unten) |
| `post_sql` | SQLite-Statements, die nach dem Generieren laufen |

Jede generierte Zeile hat einen eigenen Zufallsstrom (Seed, Tabelle, Position). Fügst du
eine Fixture hinzu, behalten alle generierten Zeilen ihre Werte, und Kindzeilen zeigen fast
immer weiter auf dieselben Eltern. Nur die Id-Nummern können sich verschieben. Änderst du
dagegen die Spalten einer Tabelle (neue Spalte, andere `gen`-Regel), werden deren Zeilen neu
gewürfelt.

## Tabellen

| Schlüssel | Bedeutung |
|---|---|
| `name` | ASCII, keine reservierten Wörter (`Order`, `User`, `Group` … werden abgelehnt) |
| `rows` | Anzahl generierter Zeilen **zusätzlich** zu den Fixtures. `0` für reine Fixture-Tabellen (Lookups) |
| `columns` | Spalten. Generatoren dürfen nur auf *frühere* Spalten derselben Zeile verweisen |
| `primary_key` | Zusammengesetzter PK als Namensliste (alternativ `"pk": true` an einer Spalte) |
| `unique` | Mehrspaltige UNIQUE-Constraints, z. B. `[["CourseId", "Semester"]]` |
| `checks` | Portable CHECK-Ausdrücke, z. B. `"EndAt IS NULL OR EndAt > StartAt"`. Spalten, die ein CHECK vergleicht, erzeugst du mit `offset_from` voneinander abhängig. Zwei unabhängige `range`-Werte verletzen den CHECK früher oder später, und der Build bricht ab |
| `description` | Bedeutung der Tabelle für die Studierenden: was eine Zeile ist, Einheiten, was NULL in einer Spalte heißt, welche Werte ein Status annimmt. `render_tasks.py` zeigt sie im Datenmodell, in Markdown und AsciiDoc. Spaltennamen in Backticks |

## Spalten

| Schlüssel | Bedeutung |
|---|---|
| `name` | ASCII, nicht reserviert |
| `type` | `int`, `bigint`, `decimal`, `float`, `string`, `text`, `bool`, `date`, `datetime` |
| `length` | Pflicht bei `string` |
| `precision`, `scale` | Für `decimal`, Standard 10/2 |
| `pk` | Teil des Primärschlüssels |
| `identity` | Auto-Increment (nur bei einspaltigem int-PK) |
| `nullable` | NULL erlaubt (Standard: NOT NULL) |
| `null_ratio` | Anteil generierter NULLs (0–1), setzt `nullable` voraus |
| `unique` | Einspaltiges UNIQUE. Bei nullable Spalten erzeugt der SQL-Server-Export einen gefilterten Index, weil SQL Server sonst nur ein NULL zulässt |
| `references` | Fremdschlüssel als `"Table.Column"`. Das Ziel muss PK oder unique sein |
| `default` | Portabler SQL-Ausdruck, z. B. `"0"` oder `"CURRENT_TIMESTAMP"` |
| `gen` | Generator-Regel (siehe unten) |

Ein einspaltiger int-PK ohne `gen` wird automatisch durchnummeriert, auch ohne `identity`.

Typ-Abbildung: `string` → VARCHAR / NVARCHAR, `bool` → BOOLEAN / BIT,
`datetime` → DATETIME / DATETIME2(0) / TIMESTAMP(0). Datetimes haben keine
Sekundenbruchteile und werden auf ganze Minuten generiert, damit Studierende sie lesen können.

## Generatoren (`gen`)

Ohne `gen` gibt es einen typabhängigen Standardwert (Zufallszahl, `fake.word()` …). Das
ist nur für Füllspalten gedacht. Alles, was in Aufgaben vorkommt, braucht eine Regel,
sonst entstehen Daten ohne Sinn.

| Regel | Wirkung |
|---|---|
| `{"choice": [...], "weights": [...]}` | Wert aus Liste, optional gewichtet. **Das Mittel für Fachvokabular** (Produktnamen, Status, Kategorien) |
| `{"faker": "provider", "args": {...}}` | Faker-Provider, z. B. `first_name`, `last_name`, `email`, `city`, `street_address`, `phone_number`, `company`, `iban`; `args` sind Keyword-Argumente |
| `{"range": [min, max]}` | int, decimal, float, date (`"2026-01-01"`) oder datetime (`"2026-01-01 08:00"`) |
| `{"range": [...], "hours": [14, 18]}` | datetime nur zwischen 14:00 und 18:00 (Öffnungs-, Dienst-, Mietzeiten) |
| `{"offset_from": "Spalte", "range": [a, b], "unit": "minutes"}` | Relativ zu einer früheren Spalte; `unit` = `minutes`/`hours`/`days` für Datumswerte, bei Zahlen wird addiert. Negative Grenzen sind erlaubt. Ist die Basis NULL, wird es auch der Wert |
| `{"sequence": "INV-{:05d}", "start": 1}` | Fortlaufender Code pro Zeile |
| `{"const": wert}` | Fester Wert |

Für Fremdschlüssel-Spalten (`references`) gelten eigene Regeln:

| Regel | Wirkung |
|---|---|
| `{"coverage": 0.8}` | Nur 80 % der Elternzeilen bekommen Kinder; der Rest bleibt kinderlos (LEFT-JOIN-Fall) |
| `{"skew": 0.8}` | Ungleichverteilung: wenige Eltern haben viele Kinder. Macht GROUP-BY-Ergebnisse unterscheidbar und Gleichstände selten. 0 = gleichverteilt |

Selbstreferenzen (`"references": "Employee.Id"`) müssen nullable sein und zeigen auf
früher generierte Zeilen. Der Export sortiert die INSERTs so, dass Eltern zuerst kommen.

## Fixtures

```json
"fixtures": {
  "Category": [{"Name": "Elektro"}, {"Name": "Uhren", "_childless": true}],
  "Volunteer": [{"Id": 9, "Firstname": "Maria", "Lastname": "Huber"},
                {"Id": 15, "Firstname": "Maria", "Lastname": "Huber"}],
  "RepairCase": [{"VolunteerId": 9}, {"RepairCafeId": 4, "BroughtAt": "2026-06-30 16:30:00"}]
}
```

- Fehlende Spalten werden wie bei generierten Zeilen ergänzt: nach den `gen`-Regeln, mit
  `null_ratio`, und fehlende Fremdschlüssel kommen aus dem Eltern-Pool. Du gibst nur an, was
  den Edge Case ausmacht. Hängt die Aufgabe an einem Wert, setz ihn explizit, auch NULL
  (`"FinishedAt": null`).
- Fixture-Zeilen ohne expliziten Schlüssel bekommen zufällige Positionen in der Nummerierung,
  damit Sonderfälle nicht alle bei Id 1, 2, 3 stehen und kein Muster erkennbar ist.
- Willst du aus anderen Fixtures auf eine Fixture-Zeile verweisen, gib ihr eine explizite Id
  (gestreut wählen, z. B. 9 und 15). Das gilt auch für Lookups: Ohne Id landet „Lawine“
  irgendwo zwischen 1 und 8, und ein `"CategoryId": 3` in einer anderen Fixture zeigt still
  auf die falsche Kategorie.
- `"_childless": true` schließt die Zeile von allen *generierten* Fremdschlüsseln aus.
  Fixture-Kinder dürfen trotzdem auf sie zeigen. Damit baust du **exakte Zählwerte**: ein
  `_childless`-Elternteil mit expliziter Id und genau so vielen Fixture-Kindern, wie die
  Aufgabe braucht (HAVING-Grenze, gleichnamige Personen mit bekannter Anzahl).
- Lookup-Tabellen mit festem Vokabular: `"rows": 0` und alle Werte als Fixtures.

## post_sql

SQLite-Statements, die nach dem Generieren in derselben Transaktion laufen; danach werden
alle Fremdschlüssel geprüft. Gedacht für Edge Cases, die von generierten Daten abhängen:
Gleichstände herstellen, Grenzwerte setzen, Konsistenz zwischen Spalten erzwingen.

```json
"post_sql": [
  "UPDATE RepairCase SET Successful = NULL WHERE FinishedAt IS NULL",
  "UPDATE Volunteer SET MentorId = 15 WHERE Id = (SELECT MIN(Id) FROM Volunteer WHERE MentorId IS NULL AND Id NOT IN (4, 15))"
]
```

Die Statements laufen in SQLite (Funktionen wie `strftime`, `date()` sind erlaubt). In den
Dump kommen nur die resultierenden Daten, nicht die Statements.

Typische Muster für Zusammenhänge, die Generatoren nicht ausdrücken:

```json
"post_sql": [
  "UPDATE Mission SET CategoryId = CASE WHEN CAST(strftime('%m', StartedAt) AS INTEGER) BETWEEN 5 AND 10 THEN 3 ELSE 1 END WHERE CategoryId IN (1, 3)",
  "DELETE FROM Deployment WHERE (SELECT m.StationId FROM Mission m WHERE m.Id = Deployment.MissionId) <> (SELECT r.StationId FROM Rescuer r WHERE r.Id = Deployment.RescuerId)"
]
```

- **Abhängigkeit innerhalb einer Zeile** (Kategorie passt zur Jahreszeit, Preis zur
  Produktgruppe): erst unabhängig generieren, dann per `UPDATE … CASE` angleichen.
- **Konsistenz über Tabellen** (n:m nur innerhalb derselben Ortsstelle, Firma, Klasse): mehr
  Zeilen generieren als nötig (etwa das Doppelte) und die unpassenden per `DELETE` entfernen.
  Die Statistik von `build_db.py` zeigt, wie viele übrig bleiben.

## Beispiel

```json
{
  "name": "repair_cafe",
  "seed": 7,
  "locale": "de_AT",
  "reference_date": "2026-10-01",
  "tables": [
    {"name": "Category", "description": "Art des Gegenstands, der zur Reparatur gebracht wird.", "rows": 0, "columns": [
      {"name": "Id", "type": "int", "pk": true, "identity": true},
      {"name": "Name", "type": "string", "length": 50, "unique": true}]},
    {"name": "Volunteer", "rows": 18, "columns": [
      {"name": "Id", "type": "int", "pk": true, "identity": true},
      {"name": "Firstname", "type": "string", "length": 50, "gen": {"faker": "first_name"}},
      {"name": "Lastname", "type": "string", "length": 50, "gen": {"faker": "last_name"}},
      {"name": "Email", "type": "string", "length": 100, "nullable": true, "null_ratio": 0.2, "unique": true,
       "gen": {"faker": "email"}},
      {"name": "MentorId", "type": "int", "nullable": true, "null_ratio": 0.4, "references": "Volunteer.Id"}]},
    {"name": "RepairCase", "rows": 70, "columns": [
      {"name": "Id", "type": "int", "pk": true, "identity": true},
      {"name": "CategoryId", "type": "int", "references": "Category.Id", "gen": {"skew": 0.7}},
      {"name": "VolunteerId", "type": "int", "nullable": true, "null_ratio": 0.1, "references": "Volunteer.Id",
       "gen": {"coverage": 0.8, "skew": 0.5}},
      {"name": "Item", "type": "string", "length": 100,
       "gen": {"choice": ["Toaster", "Kaffeemaschine", "Fahrrad", "Jeans", "Wasserkocher", "Laptop"]}},
      {"name": "BroughtAt", "type": "datetime", "gen": {"range": ["2026-01-10", "2026-09-26"], "hours": [14, 18]}},
      {"name": "FinishedAt", "type": "datetime", "nullable": true, "null_ratio": 0.15,
       "gen": {"offset_from": "BroughtAt", "range": [20, 180], "unit": "minutes"}},
      {"name": "Successful", "type": "bool", "nullable": true, "gen": {"choice": [1, 0], "weights": [7, 3]}},
      {"name": "Bonus", "type": "decimal", "precision": 6, "scale": 2, "nullable": true, "null_ratio": 0.5,
       "gen": {"range": [10, 200]}}],
     "checks": ["FinishedAt IS NULL OR FinishedAt > BroughtAt"]},
    {"name": "SparePart", "rows": 0, "columns": [
      {"name": "Id", "type": "int", "pk": true, "identity": true},
      {"name": "Name", "type": "string", "length": 100, "unique": true},
      {"name": "Price", "type": "decimal", "precision": 8, "scale": 2, "gen": {"range": [0.5, 40]}}]},
    {"name": "UsedPart", "rows": 45, "primary_key": ["RepairCaseId", "SparePartId"], "columns": [
      {"name": "RepairCaseId", "type": "int", "references": "RepairCase.Id", "gen": {"coverage": 0.6}},
      {"name": "SparePartId", "type": "int", "references": "SparePart.Id", "gen": {"skew": 0.5}},
      {"name": "Quantity", "type": "int", "gen": {"choice": [1, 1, 1, 2, 3]}}]}
  ],
  "fixtures": {
    "Category": [{"Id": 3, "Name": "Elektrogeräte"}, {"Id": 1, "Name": "Fahrrad"}, {"Id": 4, "Name": "Textil"},
                 {"Id": 2, "Name": "Uhren", "_childless": true}],
    "SparePart": [{"Name": "Sicherung 5A"}, {"Name": "Lötzinn"}, {"Name": "Bremsbelag"}, {"Name": "Schrumpfschlauch", "_childless": true}]
  },
  "post_sql": ["UPDATE RepairCase SET Successful = NULL WHERE FinishedAt IS NULL"]
}
```
