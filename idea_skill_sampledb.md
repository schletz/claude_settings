# Skill "exam-database" entwickeln

Für den Unterricht in Datenbanken brauche ich für Prüfungen oft Datenbanken mit Musterdaten.
Ein Skill soll helfen, das Schema der Datenbank zu erstellen und die Daten einzufügen.

## Aufbau der Testdaten

Die Datenbanken sind für SQL Prüfungen gedacht.
Füge daher auch Edge Cases ein, um falsche Abfragen zu erkennen (z. B. nicht alle Elemente haben Child Daten, ...).
Es werden meist Abfragen aus diesem Themenkreis geprüft:

- Join von Tabellen (INNER JOIN, LEFT JOIN)
- Aggregation (GROUP BY, HAVING)
- Unterabfragen (EXISTS, NOT EXISTS)
- DML Statements (INSERT/UPDATE/DELETE)

Ein falsch verwendetes INNER JOIN (statt LEFT JOIN) soll also nicht die korrekten Daten liefern.

Verwende zum Befüllen der Testdaten einen klassischen Python Fakedaten Generator.

## Ideen für das Schema

Wenn der Skill verwendet wird, verwende ich ihn meist in Kombination mit dem Skill /ideas.
Dieser holt aus Newsfeeds Ideen für ein Schema.
Das ist aber nicht vorgeschrieben, es können auch bestimmte Informationen im Prompt vorkommen, aus denen du ein Schema erzeugen sollst.

## Erstellen von Abfragebeispielen

Es sollen auf Wunsch eine gewisse Anzahl an Abfragebeispielen für das erzeugte Schema erstellt werden.
Die Studenten haben entweder die korrekte Lösung in der Angabe, oder die Anzahl der Datensätze.
Achte daher darauf, dass eine SQL Abfrage nicht zu viele Ergebniszeilen liefert, damit die Studenten auch die Richtigkeit optisch prüfen können.

## Skripts

Architekturmäßig ist das Erstellen der Skripts nicht einfach.
Vor allem das Erstellen der Musterdaten ist schwer, da kein Schema vorgegeben wird.
Eine Hybdridansatz (Generieren von Musterdaten mit einem python Generator) und LLM Nachkorrektur scheint mir am Besten geeignet.

Meine Gedanken dazu (wenn sie nicht OK sind liefere bessere Ideen)

1. Ich würde ein Skript machen, das eine zuerst eine sqlite Datei mit dem vom LLM erzeugten Schema erstellt.
2. Danach befüllt das Skript die Daten mit dem Musterdatengenerator in Python.
3. Das LLM prüft die Edge Cases (also falsche Lösungen, die aber die gleichen Daten wie die richtige Lösung liefern) und die Anzahl der Datensätze, die für die Abfragebeispiele zurück kommen.
4. Das LLM löscht ggf. Daten aus der SQLite Datenbank und ergänzt sie.

## Ausgabe als SQL Dump oder SQLile Datei

Es wird immer der vollständige SQL Dump (Schema + Daten) ausgegeben, der für die Zieldatenbank verarbeitbar ist.
Möchte der User eine SQLite Datenbank, gib zusätzlich die Datenbank aus.

## Unterstützte Datenbanken

Es sollen SQLite, SQL Server und Postgres unterstützt werden.

SQL Server wird über Docker geladen, `docker pull mcr.microsoft.com/mssql/server:2025-latest`
Postgres wird über Docker geladen, `docker pull postgres`

Zum Testen soll kurzzeitig ein Container erstellt und getestet werden, ob der erzeugte SQL Dump auch wirklich lauffähig ist.

