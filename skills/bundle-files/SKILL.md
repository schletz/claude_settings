---
name: bundle-files
description: Fasst einen Verzeichnisbaum zu einer einzigen Bündeldatei (.bundle) zusammen, die ein Agent selektiv liest — erst ein Inhaltsverzeichnis mit einem Satz pro Datei, dann gezielt nur die Dateien, die er braucht. Liest, ändert, ergänzt und extrahiert bestehende Bündel. Nutze diesen Skill, wenn der Nutzer ein Verzeichnis "bündeln", "als eine Datei archivieren", "als Ressource für einen Skill ablegen" oder "für einen Agent zusammenfassen" will, wenn eine .bundle-Datei gelesen, analysiert oder geändert werden soll ("ändere xy im Bundle", "füge xy ins Bundle ein", "entpacke das Bundle"), oder wenn eine Datei oder das ganze Verzeichnis aus einem Bundle wiederhergestellt werden soll — auch bei englischen Formulierungen wie "bundle this directory", "pack the repo into one file for an agent". NICHT für zip/tar-Archive, git bundle oder JavaScript-Bundler (webpack, vite).
---

# bundle-files

Ein Bündel archiviert einen Verzeichnisbaum in einer UTF-8-Textdatei.
Oben steht ein Inhaltsverzeichnis (TOC) mit allen Ordnern samt `level` (Abstand zur
obersten Ebene, die Level 0 hat), einem Satz pro Datei und der Zeilenposition jeder Datei.
Ordner bis zum `abstract-level` des Bündels tragen ein `<abstract>`, das ihren ganzen
Teilbaum zusammenfasst; das Abstract von Level 0 ist die Projektbeschreibung.
Ein Agent liest zuerst nur den Teil des TOC, den er braucht, und lädt dann gezielt einzelne Dateien — so bleibt im Kontext nur, was für die Aufgabe relevant ist.

Die Datei sieht aus wie XML, ist aber keins: Dateiinhalte stehen unmaskiert drin, damit
Code wie `List<T>` oder `&&` lesbar bleibt. Deshalb nie einen XML-Parser darauf ansetzen,
sondern immer die Skripte verwenden; sie halten auch die Zeilenpositionen konsistent.

Alle Skripte liegen in `scripts/` dieses Skills und werden mit `python <skill>/scripts/<name>.py`
aufgerufen. Sie geben UTF-8 aus, auch auf einer cp1252-Konsole, und laufen auch mit
`python -I`. `--help` zeigt alle Optionen.

## Bündel lesen

```
python scripts/read_toc.py B.bundle --count-entries          # Ordner und Einträge je Level, Zeichen
python scripts/read_toc.py B.bundle                          # ganzer TOC mit allen Einträgen
python scripts/read_toc.py B.bundle --dir-level 1            # Ordner bis Level 1 samt Abstracts, ohne Einträge
python scripts/read_toc.py B.bundle "src" --dir-level 3      # Ordner des Teilbaums bis Level 3, ohne Einträge
python scripts/read_toc.py B.bundle "src/Model"              # Teilbaum mit allen Einträgen
python scripts/read_document.py B.bundle Candidate.cs "*/Model/*.cs"
python scripts/read_document.py B.bundle angabe.pdf --lines 40-120 -n
python scripts/read_document.py B.bundle --search "HasIndex|IsUnique" [angabe.pdf "*/Model/*.cs"]
```

Beginne mit `--count-entries`, denn ein TOC kann bei großen Repos über 100 000 Zeichen haben.
Die Tabelle zeigt je Level, wie viele Ordner und Einträge dich dort erwarten. Einen kleinen TOC
liest du ganz. Bei einem großen verschaffst du dir mit `--dir-level` einen Überblick über den
Baum (nur Ordner und Abstracts) und liest dann die Einträge nur der Teilbäume, die zur Aufgabe
passen. Den Basisordner gibst du als vollen Pfad oder als eindeutiges Pfadende an, also auch
nur als Ordnernamen (`read_toc.py B.bundle OrderService`); bei einem mehrdeutigen Ende nennt
die Fehlermeldung die passenden Pfade. Nennt die Aufgabe schon einen Ordner oder ein Projekt,
liest du so direkt dessen Teilbaum. Für Namen in Dateiinhalten
(Typen, Methoden, Begriffe) ist `--search` der kürzere Weg. `--count-entries`
zählt dieselbe Auswahl wie ohne die Option (Teilbaum, Level), so prüfst du vorher, ob sie klein
genug ist. Die Level sind absolut, auch mit Teilbaum.

Statt einer Datei nehmen beide Skripte auch eine http(s)-URL, z. B. einen Raw-Link auf
GitHub. So liest du ein veröffentlichtes Bündel, ohne es erst herunterzuladen. Die URL wird
bei jedem Aufruf neu geladen; für mehrere Aufrufe oder zum Ändern lade es einmal mit `curl` in
den Scratchpad.

Wenn der TOC nicht verrät, wo etwas steht, suche mit `--search` (Regex, ohne Groß-/Kleinschreibung)
statt mit grep über die Rohdatei: Die Treffer kommen als `Pfad:Zeile` mit der Zeilennummer
innerhalb der Datei und passen damit direkt zu `--lines`. Ohne Pfade durchsucht es alle Dateien.

Pfade dürfen voll, als Dateiname, Pfadende oder Glob angegeben werden. Ein Name wie
`Person.cs` kann mehrere Treffer liefern; dann den Pfad aus dem TOC nehmen. Alternativ liest
das Read-Tool eine Datei direkt mit `offset=start` und `limit=lines` aus dem TOC-Eintrag.

Eine Ausgabe über 25 000 Zeichen bricht mit Exit-Code 1 und einer Meldung auf stderr ab, weil
Agent-Shells lange Ausgaben abschneiden. Grenze die Auswahl dann ein, oder schreibe sie mit
`--out <scratchpad>/datei` in eine Datei und lies dort gezielt.

## Bündel erstellen

```
python scripts/bundle.py create SRC OUT.bundle [--abstract-level N] [--no-root] [--ext cs,csproj,pdf,docx,md] [--exclude-dir Migrations,src/Legacy]
python scripts/read_meta.py OUT.bundle meta.json
… meta.json ausfüllen …
python scripts/bundle.py update OUT.bundle meta.json
```

Die Pfade beginnen mit dem Ordnernamen von SRC (`Projekt/src/Program.cs`), damit ein
entpacktes Bündel wieder in einem eigenen Ordner landet. `--no-root` lässt ihn weg
(`src/Program.cs`), wenn der Nutzer Pfade relativ zu SRC will.

`--ext` nimmt nur die genannten Endungen, wenn der Nutzer Dateitypen vorgibt.
Build-Ordner (`bin`, `obj`, `node_modules`, `target`, `.vs`, …) fehlen immer; in einem
Git-Repo gilt zusätzlich die `.gitignore`. PDFs werden mit PyMuPDF, Office-Dateien mit
markitdown zu Markdown konvertiert und im TOC als `converted="pdf"` markiert; andere
Binärdateien stehen nur mit ihrer Größe im TOC. Meldet das Skript, dass ein Konverter
fehlt, biete dem User `pip install --upgrade pymupdf` bzw. `pip install markitdown[all]` an.

Die `meta.json` enthält, was kein Skript erzeugen kann: `summaries` (Pfad → Satz) und
`abstracts` (Ordner → Text). Lies dafür jede Datei (aus SRC oder mit `read_document.py`) und
schreibe:

- **summaries:** ein Satz pro Datei, der beim Auswählen hilft: wofür die Datei da ist,
  nicht, was im Code steht (den sieht der Agent nach dem Laden ohnehin). Typnamen stehen
  schon im TOC und müssen nicht wiederholt werden.
- **abstracts, Level 0** (der oberste Ordner, bei `--no-root` der Pfad `""`): die
  Projektbeschreibung, gern mehrere Absätze. Art des Projekts, Technik, wie man baut und
  testet, Aufbau der Ordner, Konventionen, die sich durchziehen. Bei einem Template auch, was
  vorgegeben ist und was ergänzt werden soll. Dieser Text erspart späteren Agents, sich die
  Architektur aus Einzeldateien zusammenzusuchen.
- **abstracts, Level 1 bis `--abstract-level`:** ein bis drei Sätze über den ganzen Teilbaum:
  welche Art Material dort liegt, welche Themen, bei Übungs- und Demo-Ordnern die Namen der
  Projekte. Ein Agent entscheidet damit, ob er absteigt. Schreibe sie nach den summaries, aus
  den Sätzen des Teilbaums (`read_toc.py OUT.bundle "Ordner" --out …`), dann musst du keine
  Datei erneut lesen.

Den Level wählst du nach der Tabelle von `read_toc.py OUT.bundle --count-entries`. Bleibt der
TOC unter etwa 25 000 Zeichen, liest ein Agent ihn ganz, und Level 0 genügt. Sonst gehst du so
tief, wie Ordner noch thematische Sammlungen sind (Kapitel, Module, Übungsordner), aber nicht
bis zu einzelnen Projekten, deren Dateien schon Sätze haben. Den Level änderst du später mit
`read_meta.py B meta.json --abstract-level N`, danach ausfüllen und `update`.

Schreibe alles auf Englisch, außer der Nutzer will es anders. `update` warnt vor leeren
Sätzen und Abstracts sowie vor Pfaden, die es im Bündel nicht gibt; behebe die Warnungen,
bevor du fertig meldest.

## Bündel ändern

Jeder Befehl schreibt das ganze Bündel neu, die Quelldateien werden nicht gebraucht.

| Aufgabe | Vorgehen |
|---|---|
| Datei ändern | `read_document.py B PFAD --raw --out <scratchpad>/datei` → mit Edit ändern → `bundle.py add B <scratchpad>/datei --path PFAD`. Der Satz bleibt erhalten; passe ihn mit `--summary` an, wenn er nicht mehr stimmt. |
| Datei einfügen | `bundle.py add B DATEI --path Root/ordner/Datei.cs --summary "…"`. Den Ordner wählst du anhand des TOC so, wie er im Projekt liegen würde; ohne `Root/`, wenn die TOC-Pfade keinen gemeinsamen Ordner haben. |
| Datei entfernen | `bundle.py remove B PFAD [PFAD …]` (volle Pfade aus dem TOC) |
| Beschreibungen ändern | `read_meta.py B meta.json` → bearbeiten → `bundle.py update B meta.json` |

Eine konvertierte Datei (z. B. `angabe.pdf`) kommt mit `--raw` als Markdown heraus und
behält nach `add` ihre Markierung `converted="pdf"`.

## Projekt wiederherstellen und neu bündeln

Zum Arbeiten in einer IDE (ändern, kompilieren, testen):

```
python scripts/bundle.py extract B.bundle ZIEL
… Arbeit im Verzeichnis ZIEL/<Root> …
python scripts/bundle.py create ZIEL/<Root> B.bundle --base B.bundle
```

Bei einem Bündel ohne Root liegt das Projekt direkt in `ZIEL`; neu gebündelt wird es mit
`create ZIEL B.bundle --base B.bundle --no-root`. `extract` gibt den passenden Befehl aus.

`extract` schreibt alle Textdateien und überschreibt nichts ohne `--force`. Konvertierte
Dokumente und Binärdateien lassen sich nicht zurückverwandeln; `--base` übernimmt sie
deshalb aus dem alten Bündel, ebenso Abstracts und Sätze. Der Bericht von
`create --base` nennt geänderte Dateien (Satz prüfen), neue Dateien und neue Ordner ohne
Abstract (schreiben, dann `read_meta.py` und `update`) und entfernte Dateien. Ändert sich ein
Teilbaum stark, prüfe auch die Abstracts seiner Ordner.
