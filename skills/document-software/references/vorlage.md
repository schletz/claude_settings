# Vorlage

Gerüst für eine agentenlesbare Dokumentation. Kursive Passagen sind Ausfüllhinweise und werden ersetzt, nicht übernommen. Abschnitte, die auf den dokumentierten Code nicht zutreffen, ersatzlos löschen. Pfade sind relativ zum Projektverzeichnis.

---

# `<einheit>` — Agent-Referenz

*Ein Satz: was dokumentiert wird und wofür die Datei gedacht ist ("… so, dass Erweiterungen ohne vorheriges vollständiges Lesen des Quellcodes möglich sind").*

## Zweck

*3–6 Zeilen oder eine Stichpunktliste: was der Code tut, mit welchen Ein- und Ausgaben.*

## Modulüberblick

| Datei | Zeilen | Verantwortung |
| --- | --- | --- |
| src/a.py | 397 | *eine Zeile, in Verben* |
| src/b.py | 120 | |

Externe Abhängigkeiten: *Pakete und wie sie installiert werden; explizit vermerken, wenn keine Manifestdatei existiert.*
Standardbibliothek: *nur nennen, wenn etwas Bemerkenswertes dabei ist (plattformabhängige Module, Fallbacks).*
Einordnung ins Projekt: *Verhältnis zum restlichen Projekt, falls nicht offensichtlich.*

## Schnittstelle

*Eine der drei Formen wählen:*

**CLI**

```
programm <arg> [<option>]
```

| Modus | Auslöser | Quelle | Ausgabe | Besonderheit |
| --- | --- | --- | --- | --- |

*Exit-Codes und deren Bedeutung.*

**Bibliothek**

| Funktion / Klasse | Zeile | Signatur | Seiteneffekte |
| --- | --- | --- | --- |

**Dienst**

| Route / Event | Zeile | Payload | Antwort | Fehler |
| --- | --- | --- | --- | --- |

## Datenfluss

```
einstieg(...)                               src/datei.py:351
 ├─ schritt_a(...)                          src/datei.py:276
 │    └─ [Bedingung] alternativer_pfad
 └─ schritt_b(...)                          src/datei.py:219
```

Wichtige Reihenfolge-Invarianten:

1. ***A vor B**, weil …*
2. ***C bekommt X, nicht Y**, sonst …*

## *Kernkonzept*

*Überschrift konkret benennen (Zustandsautomat, Datenmodell, Scheduling, Parser-Grammatik, Formel).*
*Formel oder Diagramm als Codeblock, danach die Parameter mit Werten und Herkunft, danach: unter welchen Umständen muss das neu bestimmt werden und wie.*
*Auch nennen, was bewusst nicht existiert (z. B. die Umkehrfunktion) — samt Hinweis, wie sie lauten würde.*

## Konstanten-Referenz

### src/datei.py

| Konstante | Zeile | Wert / Bedeutung |
| --- | --- | --- |
| `NAME` | 57 | *Wert — wofür, und welche Annahme daran hängt* |
| `TIMEOUT_S` | 61 | *30 — am Produktivsystem gemessen (laut User)* |

*Invarianten zwischen Konstanten fett hervorheben: **Invariante:** `len(A) == len(B) + 1`.*

## Externe Systeme

*Pro Aufruf: Methode, URL/Kommando, Parameter, Pfad zum Ergebnis in der Antwort, Auth, Timeout, Fehlerverhalten. Kurz begründen, warum es so aufgeteilt ist (z. B. zweistufig Metadaten → Nutzdaten).*

## Details

*Was beim Nachbauen überrascht: Zahlenbeispiele mit Rechenweg, Formatentscheidungen, Encodings, Rundungen, Alignment. Jede Zahl, die von einer anderen abhängt, mit der Abhängigkeit versehen ("wer X ändert, muss Y nachziehen").*

## Fehlerbehandlung

| Situation | Verhalten |
| --- | --- |
| *Ungültige Eingabe* | *Meldung nach stderr, Exit 1, kein Request* |
| *Ressource fehlt* | ***nicht** abgefangen — Traceback* |

*Sprache der Benutzermeldungen und Ausgabekanal (stdout/stderr/Logger) festhalten.*

## Erweiterungspunkte

***Absicht** — anzufassende Stelle `symbol` (src/datei.py:107). Was dabei mitzieht, was stillschweigend schiefgeht.*

*Fünf bis acht Einträge, sortiert nach Häufigkeit der Änderung.*

## Fallstricke

- *Destruktives Verhalten (überschreibt Eingabedateien, löscht Zwischenstände).*
- *Blockierendes oder interaktives Verhalten und wofür es damit ungeeignet ist.*
- *Stille Annahmen (Zeitzonen, Locale, Plattform, Reihenfolge von Dict-Einträgen).*
- *Was fehlt: Tests, Logging, Retries, Validierung.*
