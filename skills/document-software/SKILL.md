---
name: document-software
description: Erstellt agentenlesbare Referenzdokumentation für ein Skript, Modul, Paket oder Subsystem (Datei <name>.md neben dem Code). Nutze diesen Skill, wenn der Nutzer um eine Dokumentation, Doku, Architekturbeschreibung, Onboarding-Datei oder ein "Kontext-Dokument für ein LLM" zu bestehendem Code bittet — auch bei englischen Formulierungen wie "document this module", "write docs for X", "explain this codebase for an agent". NICHT für Endnutzer-Handbücher, Tutorials, Marketing-READMEs oder Docstrings im Code.
---

# Agentenlesbare Softwaredokumentation

## Zielgruppe und Zweck

Die Leserin ist ein LLM (oder ein neuer Entwickler), das die Datei **statt** des Quellcodes in den Kontext lädt, um anschließend zu erweitern, zu debuggen oder zu refactoren. Daraus folgt alles Weitere:

- **Nur was der Code nicht in zehn Sekunden verrät.** Signaturen abschreiben ist wertlos — Herkunft magischer Zahlen, Invarianten, Reihenfolgeabhängigkeiten und Fallstricke sind der eigentliche Inhalt.
- **Jede Aussage verankern.** Konstanten, Funktionen und Verzweigungen mit `Datei:Zeile` referenzieren, damit der Agent gezielt nachlesen kann, statt alles zu lesen.
- **Tabellen vor Prosa** für alles Aufzählbare (Konstanten, Modi, Fehlerfälle, Endpunkte). Fließtext nur dort, wo ein *Warum* erklärt wird.
- **Nichts erfinden.** Was nicht im Code steht, wird nicht behauptet. Unklares wird als offen markiert, nicht plausibel ergänzt.
- **Nur der Endzustand.** Beschrieben wird, was jetzt im Code steht — nie, was vorher dort stand. Die Leserin hat den Vorzustand nie gesehen; jede Differenzaussage kostet sie Aufmerksamkeit und erklärt ihr nichts. Besonders wachsam sein, wenn die Doku direkt nach einem Umbau entsteht: Dann steckt der Verlauf noch im eigenen Kontext und rutscht ungefragt in die Sätze.

## Ablauf

1. **Umfang klären.** Eine Datei, ein Modul, ein Subsystem? Im Zweifel den Umfang wählen, den der Nutzer genannt hat, und die direkten Abhängigkeiten als Nebendarsteller behandeln. Ausgabedatei standardmäßig `<basisname>.md` neben dem dokumentierten Code.

2. **Vollständig lesen.** Zielobjekt *und* jede von ihm importierte Projektdatei, dazu Einstiegspunkt, Konfiguration und, falls vorhanden, `README`/`CLAUDE.md` für den Projektkontext. Zeilenanzahl je Datei erheben — sie gehört in den Modulüberblick und ist ein Indiz für Verletzungen des Single-Responsibility-Prinzips.

3. **Fakten sammeln,** je Punkt mit Zeilennummer:
   - öffentliche API: Funktionen/Klassen, Parameter, Rückgabewerte, Seiteneffekte;
   - alle Konstanten und Konfigurationswerte, inklusive erkennbarer Herkunft;
   - Ein-/Ausgaben: Dateien, Netzwerk, stdin/stdout, Datenbank, Umgebungsvariablen;
   - Kontrollfluss: Modi, Verzweigungen, Schleifen mit Abbruchbedingung;
   - Fehlerpfade — besonders die **nicht** behandelten;
   - Invarianten: Reihenfolgen, Größenbeziehungen (`len(a) == len(b) + 1`), Alignment, Wertebereiche.

4. **Rechnen und prüfen.** Abgeleitete Zahlen (Bildgrößen, Puffergrößen, Zeitbudgets, Grenzwerte) tatsächlich nachrechnen, bevor sie in die Doku wandern. Behauptungen über Verhalten, die sich billig verifizieren lassen, verifizieren.

5. **Schreiben** nach der Gliederung unten. Nicht zutreffende Abschnitte ersatzlos streichen statt mit Füllsätzen zu bestücken.

6. **Selbstprüfung** anhand der Checkliste am Ende.

## Gliederung

Als Baukasten verstehen, nicht als Pflichtschema. Vorlage mit fertigen Überschriften und Beispielzeilen: [references/vorlage.md](references/vorlage.md).

| Abschnitt | Inhalt | Wann weglassen |
| --- | --- | --- |
| Zweck | Was das Ding tut, in 3–6 Zeilen oder Stichpunkten | nie |
| Modulüberblick | Tabelle Datei / Zeilen / Verantwortung + externe Abhängigkeiten | bei einer einzelnen, abhängigkeitsfreien Datei |
| Schnittstelle | CLI-Modi, öffentliche API, HTTP-Routen, Events — je nach Art des Codes | wenn es keinen externen Einstiegspunkt gibt |
| Datenfluss | Call-Graph als Codeblock mit Zeilenverweisen, danach die Invarianten der Reihenfolge | bei rein deklarativem Code |
| Kernkonzept | Die eine Sache, die man verstanden haben muss: Algorithmus, Formel, Zustandsmaschine, Datenmodell — samt Herkunft der Parameter | wenn es keine gibt |
| Konstanten-Referenz | Tabelle Konstante / Zeile / Bedeutung, je Datei | wenn alle Werte trivial sind |
| Externe Systeme | Endpunkte, Payloads, Auth, Timeouts, Antwortpfade | ohne I/O nach außen |
| Details | Was beim Nachbauen sonst überrascht: Formate, Fonts, Encodings, Defaults | selten |
| Fehlerbehandlung | Tabelle Situation / Verhalten, inklusive der ungefangenen Fälle | nie |
| Erweiterungspunkte | Pro typischer Änderung: welche Stelle anfassen, was mitzieht | nie |
| Fallstricke | Destruktives Verhalten, Blockieren, fehlende Tests, stille Annahmen | nie |

### Der wichtigste Abschnitt: Erweiterungspunkte

Er ist der Grund, warum die Datei existiert. Aufbau je Eintrag: **auslösende Absicht → anzufassende Stelle (mit Zeilenverweis) → Folgewirkung**.

> **Anderes Quellprodukt** — `PRODUCT`/`PROJECTION` in [api.py:20-21](api.py#L20-L21). Achtung: anderes Produkt heißt in aller Regel neue Projektionsparameter, neuer Zuschnitt und neue Legendenfarben.

Nicht: "Die Konstante `PRODUCT` definiert das Produkt." Das steht im Code.

### Datenfluss-Notation

Ein Codeblock mit Baumzeichen, jede Ebene mit Zeilenanker, Verzweigungen als `[Bedingung]` markiert:

```
main(argv)                                  app.py:351
 ├─ Argumente parsen + validieren
 ├─ load_sources(...)                       app.py:276
 │    ├─ lokal:    open(...)
 │    └─ Download: api.fetch(...)  -> Result(data, meta)
 ├─ [nur Download] pause_for_input(...)     app.py:313
 └─ save(output_path)
```

Direkt darunter die Invarianten nummerieren, die aus der Reihenfolge folgen ("A muss vor B laufen, weil …").

## Regeln

- **Sprache:** Fließtext in der Sprache des Nutzers bzw. wie in der `CLAUDE.md` des Projekts festgelegt; Bezeichner, Pfade und Codebeispiele bleiben in der Sprache des Codes.
- **Links:** Dateiverweise als relative Markdown-Links vom Repo-Wurzelverzeichnis, mit `#L42` bzw. `#L42-L51` für Zeilen. Keine Backticks um Pfade.
- **Zeilennummern** stammen aus dem tatsächlich gelesenen Stand. Wird der Code im selben Arbeitsgang geändert, die Anker danach korrigieren. Anker auf Definitionen setzen, nicht auf Aufrufe — die bleiben länger gültig.
- **Magische Zahlen** bekommen eine Herkunft: gemessen, gefittet, von der Spezifikation vorgegeben, historisch gewachsen, oder "Herkunft unbekannt".
- **Kein Redundanzverbot bei Invarianten.** Was leicht kaputtgeht, darf zweimal dastehen — einmal in der Konstantentabelle, einmal als Warnung im zugehörigen Abschnitt.
- **Umfang:** so lang wie nötig. Für ein Skript von einigen hundert Zeilen sind 150–250 Zeilen Doku angemessen; wächst sie über die Codegröße hinaus, wurde Code paraphrasiert statt erklärt.
- **Keine Änderungshistorie** — weder die des Codes noch die des eigenen Arbeitsauftrags. Verräterisch sind "nur noch", "nicht mehr", "früher", "inzwischen", "wurde entfernt", "es gab einmal": Sie beschreiben eine Differenz zu einem Zustand, den die Leserin nicht kennt. Statt "Es gab einmal eine CLI, deren Andockstellen wurden restlos entfernt" schlicht: "`app.py` ist der einzige Einstiegspunkt." Gelöschte Dateien, ersetzte Parameter und alte Defaults kommen gar nicht vor. Zulässig bleibt, was den Ist-Zustand beschreibt: die Herkunft eines Werts ("historisch gewachsen") und der Hinweis, dass eine Funktion oder ein Feld heute unbenutzt im Code liegt.
- **Keine Meta-Kommentare** über den Entstehungsprozess der Doku. Kein "TODO: später ergänzen" — offene Punkte gehören benannt und begründet.
- **Docstrings ersetzen die Datei nicht und umgekehrt.** Wenn beim Lesen auffällt, dass Docstrings fehlen, das melden statt es stillschweigend in der Doku aufzufangen.

## Checkliste vor der Abgabe

1. Könnte ein Agent allein mit dieser Datei eine typische Erweiterung korrekt umsetzen?
2. Ist jede Konstante, jeder Endpunkt und jeder Fehlerfall entweder erklärt oder bewusst ausgelassen?
3. Stimmen alle Zeilennummern und alle nachgerechneten Zahlen?
4. Steht irgendwo etwas, das genauso gut direkt im Code steht? Streichen.
5. Sind die destruktiven und blockierenden Verhaltensweisen benannt (Dateien überschreiben, auf Eingabe warten, Netzwerkzugriff, Kosten)?
6. Ist klar, was **nicht** existiert (keine Tests, kein Logging, keine Rückwärtstransformation, keine Retry-Logik)?
7. Beschreibt jeder Satz den Ist-Zustand? Nach "nur noch", "nicht mehr", "früher", "inzwischen", "entfernt", "einmal" suchen und jeden Treffer umformulieren oder streichen. Kommt eine Datei vor, die es nicht mehr gibt?
