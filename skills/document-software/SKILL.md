---
name: document-software
description: Erstellt oder aktualisiert eine Referenzdokumentation, die ausschließlich ein KI-Agent liest (Datei REFERENCE.md neben dem Code), für ein kleineres Projekt, Skript, Modul oder Paket — damit ein späterer Agent erweitern, debuggen oder refactoren kann, ohne den gesamten Quellcode zu lesen. Nutze diesen Skill, wenn der Nutzer um eine Dokumentation, Doku oder ein "Kontext-Dokument für ein LLM/einen Agent" zu bestehendem Code bittet oder eine vorhandene REFERENCE.md auf den aktuellen Stand bringen will — auch bei englischen Formulierungen wie "document this module", "write docs for X", "update the reference docs", "explain this codebase for an agent". NICHT für Dokumentation, die Menschen lesen (Onboarding, Architekturbeschreibungen, Endnutzer-Handbücher, Tutorials, READMEs), und nicht für Docstrings im Code.
---

# Agentenlesbare Softwaredokumentation

## Zielgruppe und Zweck

Der einzige Leser ist ein KI-Agent. Er lädt die Datei **statt** des Quellcodes in den Kontext, um anschließend zu erweitern, zu debuggen oder zu refactoren. Kein Mensch liest sie, Einleitungen, Überleitungen und Lesekomfort kosten also nur Kontext. Daraus folgt alles Weitere:

- **Nur was der Code nicht in zehn Sekunden verrät.** Signaturen abschreiben ist wertlos — Herkunft magischer Zahlen, Invarianten, Reihenfolgeabhängigkeiten und Fallstricke sind der eigentliche Inhalt.
- **Jede Aussage verankern** (Format unter Regeln), damit der Agent gezielt nachlesen kann, statt alles zu lesen.
- **Tabellen vor Prosa** für alles Aufzählbare (Konstanten, Modi, Fehlerfälle, Endpunkte). Fließtext nur dort, wo ein *Warum* erklärt wird.
- **Nichts erfinden.** Was weder im Code steht noch vom User bestätigt wurde, kommt nicht in die Doku — auch nicht als Vermutung oder "offen"-Markierung. Der Agent vertraut der Datei; eine plausible Fehlannahme richtet mehr Schaden an als eine Lücke, die ihn zum Nachlesen zwingt.
- **Beschreiben, nicht bewerten.** Die Doku hält den Ist-Zustand fest. Verbesserungsbedarf — fehlende Docstrings, SRP-Kandidaten, vermutete Bugs — gehört in den Abschlussbericht an den User; in der Doku würde ein Agent ihn als Auftrag missverstehen. Was fehlt (keine Tests, kein Logging), ist dagegen Ist-Zustand und gehört hinein.

## Ablauf

Existiert am Zielort schon eine `REFERENCE.md`, gilt der Abschnitt *Aktualisieren* weiter unten.

1. **Umfang klären.** Der Skill ist für kleinere Projekte gedacht und schreibt genau eine Datei, standardmäßig `REFERENCE.md` im Verzeichnis des dokumentierten Codes. Im Zweifel den Umfang wählen, den der User genannt hat, und die direkten Abhängigkeiten als Nebendarsteller behandeln. Mehrere Dateien nur, wenn der User die Aufteilung vorgibt.

2. **Vollständig lesen.** Zielobjekt *und* jede von ihm importierte Projektdatei, dazu Einstiegspunkt, Konfiguration und, falls vorhanden, `README`/`CLAUDE.md` für den Projektkontext. Zeilenanzahl je Datei erheben — sie kommt in den Modulüberblick, damit der Agent abschätzen kann, was das Nachlesen einer Datei kostet.

3. **Fakten sammeln,** je Punkt mit Verweis:
   - öffentliche API: Funktionen/Klassen, Parameter, Rückgabewerte, Seiteneffekte;
   - alle Konstanten und Konfigurationswerte, inklusive erkennbarer Herkunft;
   - Ein-/Ausgaben: Dateien, Netzwerk, stdin/stdout, Datenbank, Umgebungsvariablen;
   - Kontrollfluss: Modi, Verzweigungen, Schleifen mit Abbruchbedingung;
   - Fehlerpfade — besonders die **nicht** behandelten;
   - Invarianten: Reihenfolgen, Größenbeziehungen (`len(a) == len(b) + 1`), Alignment, Wertebereiche.

4. **Rechnen und prüfen.** Abgeleitete Zahlen (Puffergrößen, Zeitbudgets, Grenzwerte) tatsächlich nachrechnen, bevor sie in die Doku wandern. Verhalten darf durch Ausführen geprüft werden, solange das keine Seiteneffekte hat: vorhandene Tests, reine Funktionen, eigene Rechenskripte. Alles, was Dateien schreibt, Netzwerk nutzt, Kosten verursacht oder auf Eingabe wartet, nur nach Rückfrage — der Auftrag ist Dokumentieren, nicht den Zustand des Projekts zu verändern.

5. **Den User fragen.** Alle Unklarheiten (ungewöhnliche Patterns, nicht erkennbare Logik oder Ziele, Herkunft magischer Zahlen) sammeln, gebündelt stellen und nachfragen, bis nichts mehr offen ist. Ist kein User erreichbar (Subagent, nicht-interaktiver Lauf), gehen die Fragen im Ergebnis an den Aufrufer; die betroffenen Punkte bleiben aus der Doku draußen und werden nach der Klärung per *Aktualisieren* ergänzt.

6. **Schreiben** nach der Gliederung unten. Nicht zutreffende Abschnitte ersatzlos streichen statt mit Füllsätzen zu bestücken.

7. **Selbstprüfung** anhand der Checkliste am Ende.

8. **Abschlussbericht** im Chat bzw. an den Aufrufer, knapp:
   - Pfad der Doku;
   - offene Fragen (nur, wenn kein User erreichbar war);
   - Auffälligkeiten, die nicht in die Doku gehören: fehlende Docstrings, Dateien, deren Größe oder Verantwortungsmix auf eine SRP-Verletzung hindeutet, vermutete Bugs;
   - bei mehr als etwa 3.000 Zeilen Code den Hinweis, dass eine Aufteilung in mehrere Dokus sinnvoll wäre, samt Vorschlag;
   - das Angebot, in der `CLAUDE.md` des Projekts einen Verweis einzutragen ("Vor Änderungen in src/foo/ zuerst src/foo/REFERENCE.md lesen"), sofern dort keiner steht. Ohne diesen Verweis erfährt ein späterer Agent nicht, dass die Datei existiert. Nur anbieten, nicht ungefragt eintragen.

### Aktualisieren

Eine bestehende `REFERENCE.md` wird überarbeitet, nicht neu geschrieben: Ihre Gliederung und die eingeflossenen Antworten des Users haben Wert.

1. Bestehende Doku lesen, dann den Code vollständig neu lesen (Schritte 2–3). Welche Stellen sich seit der letzten Fassung geändert haben, lässt sich nicht verlässlich eingrenzen, deshalb wird alles geprüft.
2. Jede Aussage und jeden Verweis gegen den Code prüfen: Zeilennummern nachziehen, Falsches korrigieren, Verschwundenes streichen, Neues ergänzen.
3. Aussagen mit der Kennzeichnung "(laut User)" lassen sich nicht am Code prüfen. Sie bleiben, solange der Code, auf den sie sich beziehen, noch so aussieht wie beschrieben. Hat er sich geändert — anderer Wert, andere Logik —, wird die Aussage gestrichen und neu gefragt.
4. Weiter mit den Schritten 4–8. Der Bericht nennt zusätzlich, welche Abschnitte sich inhaltlich geändert haben.

## Gliederung

Als Baukasten verstehen, nicht als Pflichtschema. Vorlage mit fertigen Überschriften und Beispielzeilen: [references/vorlage.md](references/vorlage.md).

| Abschnitt | Inhalt | Wann weglassen |
| --- | --- | --- |
| Zweck | Was das Ding tut, in 3–6 Zeilen oder Stichpunkten | nie |
| Modulüberblick | Tabelle Datei / Zeilen / Verantwortung + externe Abhängigkeiten | bei einer einzelnen, abhängigkeitsfreien Datei |
| Schnittstelle | CLI-Modi, öffentliche API, HTTP-Routen, Events — je nach Art des Codes | wenn es keinen externen Einstiegspunkt gibt |
| Datenfluss | Call-Graph als Codeblock mit Verweisen, danach die Invarianten der Reihenfolge | bei rein deklarativem Code |
| Kernkonzept | Die eine Sache, die man verstanden haben muss: Algorithmus, Formel, Zustandsmaschine, Datenmodell — samt Herkunft der Parameter | wenn es keine gibt |
| Konstanten-Referenz | Tabelle Konstante / Zeile / Bedeutung, je Datei | wenn alle Werte trivial sind |
| Externe Systeme | Endpunkte, Payloads, Auth, Timeouts, Antwortpfade | ohne I/O nach außen |
| Details | Was beim Nachbauen sonst überrascht: Formate, Encodings, Rundungen, Defaults | selten |
| Fehlerbehandlung | Tabelle Situation / Verhalten, inklusive der ungefangenen Fälle | nie |
| Erweiterungspunkte | Pro typischer Änderung: welche Stelle anfassen, was mitzieht | nie |
| Fallstricke | Destruktives Verhalten, Blockieren, fehlende Tests, stille Annahmen | nie |

### Der wichtigste Abschnitt: Erweiterungspunkte

Er ist der Grund, warum die Datei existiert. Aufbau je Eintrag: **auslösende Absicht → anzufassende Stelle (mit Verweis) → Folgewirkung**.

> **Neues Ausgabeformat** — Eintrag in `FORMATS` (src/export.py:14) ergänzen und einen Writer nach dem Muster von `write_csv` (src/export.py:88) anlegen. Achtung: `parse_args` (src/cli.py:31) prüft `--format` gegen eine eigene Liste, die nicht aus `FORMATS` abgeleitet ist — beide müssen mitgezogen werden.

Nicht: "Die Konstante `FORMATS` enthält die unterstützten Formate." Das steht im Code.

### Datenfluss-Notation

Ein Codeblock mit Baumzeichen, jede Ebene mit Verweis, Verzweigungen als `[Bedingung]` markiert:

```
main(argv)                                  src/app.py:351
 ├─ Argumente parsen + validieren
 ├─ load_sources(...)                       src/app.py:276
 │    ├─ lokal:    open(...)
 │    └─ Download: api.fetch(...)  -> Result(data, meta)
 ├─ [nur Download] pause_for_input(...)     src/app.py:313
 └─ save(output_path)
```

Direkt darunter die Invarianten nummerieren, die aus der Reihenfolge folgen ("A muss vor B laufen, weil …").

## Regeln

- **Sprache:** Fließtext in der Sprache, die die `CLAUDE.md` des Projekts festlegt, sonst in der des Users; Bezeichner, Pfade und Codebeispiele bleiben in der Sprache des Codes.
- **Verweisformat:** reiner Text, `symbol` (pfad:42) bzw. pfad:42-51, Pfade relativ zum Projektverzeichnis — dem Arbeitsverzeichnis des Agents, in dem auch die `CLAUDE.md` liegt. Dort starten die Tool-Aufrufe des Agents, er kann den Pfad also direkt verwenden. Keine Markdown-Links: Der Agent liest das Rohmarkdown, ein Link stünde doppelt da. Der Symbolname macht den Verweis robust — verrutscht die Zeile, findet der Agent die Stelle per Suche.
- **Zeilennummern** stammen aus dem tatsächlich gelesenen Stand. Wird der Code im selben Arbeitsgang geändert, die Verweise danach korrigieren. Auf Definitionen verweisen, nicht auf Aufrufe — die bleiben länger gültig.
- **Magische Zahlen** bekommen eine Herkunft: gemessen, gefittet, von der Spezifikation vorgegeben, historisch gewachsen. Ist sie aus dem Code nicht erkennbar, fragen (Schritt 5); weiß es auch der User nicht, ist "Herkunft unbekannt (laut User)" eine gültige Angabe.
- **Antworten des Users kennzeichnen** mit "(laut User)". Beim Aktualisieren ist das die einzige Möglichkeit, sie von Fakten aus dem Code zu unterscheiden.
- **Kein Redundanzverbot bei Invarianten.** Was leicht kaputtgeht, darf zweimal dastehen — einmal in der Konstantentabelle, einmal als Warnung im zugehörigen Abschnitt.
- **Umfang:** so lang wie nötig. Für ein Skript von einigen hundert Zeilen sind 150–250 Zeilen Doku angemessen; wächst sie über die Codegröße hinaus, wurde Code paraphrasiert statt erklärt.
- **Nur der Ist-Zustand.** Beschrieben wird, was jetzt im Code steht, nie, was vorher dort stand — weder beim Code noch beim eigenen Arbeitsauftrag. Der Agent hat den Vorzustand nie gesehen; jede Differenzaussage kostet ihn Aufmerksamkeit und erklärt ihm nichts. Verräterisch sind "nur noch", "nicht mehr", "früher", "inzwischen", "wurde entfernt", "es gab einmal". Statt "Die Konfiguration wird nicht mehr aus Umgebungsvariablen gelesen" schlicht: "Die Konfiguration stammt ausschließlich aus config.toml." Gelöschte Dateien, ersetzte Parameter und alte Defaults kommen gar nicht vor. Zulässig bleibt die Herkunft eines Werts ("historisch gewachsen") und der Hinweis, dass eine Funktion heute unbenutzt im Code liegt. Besonders wachsam sein, wenn die Doku direkt nach einem Umbau entsteht oder aktualisiert wird: Dann steckt der Verlauf noch im eigenen Kontext und rutscht ungefragt in die Sätze.
- **Keine Meta-Kommentare** über den Entstehungsprozess der Doku. Kein "TODO: später ergänzen" — Offenes wird gefragt, nicht vertagt.

## Checkliste vor der Abgabe

1. Könnte ein Agent allein mit dieser Datei eine typische Erweiterung korrekt umsetzen?
2. Ist jede Konstante, jeder Endpunkt und jeder Fehlerfall entweder erklärt oder bewusst ausgelassen?
3. Stimmen alle Verweise (Symbol und Zeile) und alle nachgerechneten Zahlen?
4. Steht irgendwo etwas, das genauso gut direkt im Code steht? Streichen.
5. Sind die destruktiven und blockierenden Verhaltensweisen benannt (Dateien überschreiben, auf Eingabe warten, Netzwerkzugriff, Kosten)?
6. Ist klar, was **nicht** existiert (keine Tests, kein Logging, keine Rückwärtstransformation, keine Retry-Logik)?
7. Ist jede Aussage durch Code oder "(laut User)" gedeckt, und steht keine Bewertung drin, die in den Bericht gehört?
8. Beschreibt jeder Satz den Ist-Zustand (Regel *Nur der Ist-Zustand*), und kommt keine Datei vor, die es nicht gibt?
