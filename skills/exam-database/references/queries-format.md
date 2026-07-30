# Abfragedatei (`queries.json`)

Eine Datei für drei Zwecke: `check_queries.py` prüft damit die Daten,
`verify_dump.py` vergleicht die Lösungen auf der Zieldatenbank, und `render_tasks.py`
erzeugt daraus das Aufgabenblatt.

```json
{
  "max_rows": 15,
  "queries": [
    {
      "id": "q1",
      "topic": "left-join",
      "task": "Geben Sie für jede Kategorie die Anzahl der Reparaturfälle aus. Kategorien ohne Reparaturfall sollen mit 0 aufscheinen.",
      "sql": "SELECT c.Id, c.Name, COUNT(rc.Id) AS Cases FROM Category c LEFT JOIN RepairCase rc ON rc.CategoryId = c.Id GROUP BY c.Id, c.Name",
      "wrong": [
        {"label": "INNER JOIN statt LEFT JOIN", "sql": "SELECT c.Id, c.Name, COUNT(rc.Id) AS Cases FROM Category c JOIN RepairCase rc ON rc.CategoryId = c.Id GROUP BY c.Id, c.Name"},
        {"label": "COUNT(*) statt COUNT(rc.Id)", "sql": "SELECT c.Id, c.Name, COUNT(*) AS Cases FROM Category c LEFT JOIN RepairCase rc ON rc.CategoryId = c.Id GROUP BY c.Id, c.Name"}
      ]
    },
    {
      "id": "d1",
      "topic": "dml",
      "task": "Setzen Sie bei allen Fällen ohne Endzeitpunkt vor dem 1. September 2026 den Erfolg auf 'nicht erfolgreich'.",
      "sql": "UPDATE RepairCase SET Successful = 0 WHERE FinishedAt IS NULL AND BroughtAt < '2026-09-01'",
      "sql_by_dialect": {"postgres": "UPDATE RepairCase SET Successful = FALSE WHERE FinishedAt IS NULL AND BroughtAt < '2026-09-01'"},
      "wrong": [
        {"label": "= NULL statt IS NULL", "sql": "UPDATE RepairCase SET Successful = 0 WHERE FinishedAt = NULL AND BroughtAt < '2026-09-01'"}
      ]
    }
  ]
}
```

| Feld | Bedeutung |
|---|---|
| `max_rows` | Obergrenze für Ergebniszeilen (global, pro Abfrage überschreibbar) |
| `id` | Kurze Kennung für Berichte |
| `topic` | Prüfungsthema, frei wählbar |
| `task` | Aufgabentext für die Studierenden (Deutsch, eindeutig formuliert, mit festen Datumswerten) |
| `sql` | Korrekte Lösung. Gilt für jeden Dialekt ohne Override, also auch für den SQLite-Check |
| `sql_by_dialect` | Overrides pro Dialekt: `sqlite`, `mssql`, `postgres` |
| `wrong` | Falsche Varianten in **SQLite-Syntax** (sie laufen nur im Check) |
| `ordered` | `true`, wenn die Reihenfolge Teil der Lösung ist. Dann vergleicht der Check auch die Reihenfolge |

`sql` sollte wenn möglich direkt im Zieldialekt geschrieben sein. Läuft es nicht auf
SQLite (TOP, YEAR(), …), braucht es einen `sqlite`-Override, damit der Check es ausführen kann.

Die Lösungen landen wortwörtlich im Aufgabenblatt. Für mehrzeilige, gut lesbare Lösungen
schreibst du Zeilenumbrüche als `\n` in den JSON-String
(`"SELECT c.Name, COUNT(rc.Id) AS Cases\nFROM Category c\n..."`).

DML-Aufgaben (INSERT/UPDATE/DELETE) laufen im Check auf einer Kopie der Datenbank. Jede
Aufgabe startet also vom Ausgangszustand. Mehrere Statements in `sql` werden mit `;`
getrennt (z. B. erst Kinder, dann Eltern löschen). Als „betroffene Datensätze“ zählt
die Summe über alle Statements; das Aufgabenblatt weist darauf hin. Eine falsche Variante gilt als erkannt,
wenn sie einen anderen Datenbestand hinterlässt oder mit einem Fehler abbricht
(z. B. FK-Verletzung).
