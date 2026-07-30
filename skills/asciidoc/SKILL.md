---
name: asciidoc
description: Erstellt AsciiDoc-Dokumente (mit PlantUML-Diagrammen, LaTeX-Formeln, Zitaten, Literaturverzeichnis) und konvertiert sie per Docker-Container in ein PDF. Nutze diesen Skill immer, wenn der Nutzer ein AsciiDoc-Dokument (.adoc) schreiben, erweitern oder als PDF ausgeben will — auch bei englischen Formulierungen wie "write an asciidoc document", "convert .adoc to pdf", "asciidoctor-pdf". Auch relevant, wenn nach einer technischen Dokumentation, einem Bericht oder einer Diplomarbeit mit Diagrammen/Formeln gefragt wird und AsciiDoc als Format genannt wird oder aus dem Kontext (vorhandene .adoc-Dateien im Projekt) sinnvoll ist. NICHT für reine Markdown-, Word- oder LaTeX-Dokumente ohne AsciiDoc-Bezug.
---

# AsciiDoc-Dokumente erstellen und in PDF konvertieren

## Regeln für den AsciiDoc-Text

- Genau ein Satz pro Zeile. AsciiDoc behandelt Zeilenumbrüche innerhalb eines Absatzes wie Leerzeichen, das Ergebnis-PDF wird dadurch nicht beeinflusst — aber Diffs im Dokument bleiben dadurch auf Satzebene lesbar.
- Vor jeder Liste eine Leerzeile einfügen, sonst wird sie von manchen Renderern nicht als Liste erkannt.
- Keine Markdown-Syntax wie `[cite]` oder Ähnliches verwenden, nur in AsciiDoc gültige Syntax.
- Querverweise der Form `<<anker>>` dürfen nicht mit einer Ziffer beginnen — sonst kann `asciidoctor-pdf` sie nicht auflösen. Also `<<kapitel-2>>`, nicht `<<2-kapitel>>`.
- PlantUML-Diagramme direkt im Dokument einbetten, mit `[plantuml,format=svg]` und einem `----`-Block (siehe Vorlage).
- `:hyphens:` (automatische Silbentrennung) nur bei `:lang: DE` setzen. Für englische Dokumente (`:lang: EN`) diese Zeile weglassen, da die Trennung dort nicht unterstützt wird.

## Vorlage

Die vollständige Vorlage mit allen Modulen (Codeblock mit Callouts, Zitate, PlantUML, LaTeX-Formeln, Bilder, Literaturverzeichnis) liegt in [references/vorlage.adoc](references/vorlage.adoc). Beim Anlegen eines neuen Dokuments von dieser Vorlage ausgehen und nur die tatsächlich benötigten Module übernehmen — nicht alle Beispielabschnitte blind in jedes Dokument kopieren.

## PDF-Konvertierung

Die Konvertierung läuft über das Docker-Image `asciidoctor/docker-asciidoctor` und wird von [scripts/convert_to_pdf.py](scripts/convert_to_pdf.py) übernommen. Das Skript spricht über das `docker`-Python-Paket direkt mit der Docker-Engine (kein `docker run` über die Shell), läuft daher unverändert unter Windows, macOS und Linux und kommt auch mit Leerzeichen in Datei- und Verzeichnisnamen zurecht.

Aufruf:

```bash
python scripts/convert_to_pdf.py "<Arbeitsverzeichnis>" "<Dateiname.adoc>" ["<Layoutdatei.yml>"]
```

- **Arbeitsverzeichnis**: enthält die `.adoc`-Datei und alle referenzierten Bilder. Wird 1:1 als Volume in den Container gemountet, das PDF landet dort neben der Quelldatei.
- **Dateiname**: Name der `.adoc`-Datei relativ zum Arbeitsverzeichnis.
- **Layoutdatei** (optional): ein `pdf-theme`-YAML-File für `asciidoctor-pdf`. Muss nicht im Arbeitsverzeichnis liegen — das Skript kopiert es temporär dorthin (unter einem eindeutigen, versteckten Namen) und löscht die Kopie nach der Konvertierung wieder, unabhängig davon, ob sie erfolgreich war.

Das Skript pullt das Image automatisch, falls es lokal noch nicht vorhanden ist (kann beim ersten Lauf etwas dauern), aktiviert `asciidoctor-diagram` (PlantUML) und `asciidoctor-mathematical` (LaTeX-Formeln als SVG) und räumt danach selbst auf:

- den internen `.asciidoctor`-Cache-Ordner im Container,
- die von `asciidoctor-diagram`/`asciidoctor-mathematical` neben der Quelldatei erzeugten `diag-*.svg`- und `stem-*.svg`-Dateien.

Bei einem Fehler gibt das Skript die `stderr`-Ausgabe von `asciidoctor-pdf` aus und beendet sich mit Exit-Code 1 — diese Meldung enthält meist schon die genaue Zeile im `.adoc`-Dokument, die das Problem verursacht.

## Voraussetzungen

- Docker muss laufen (lokal per Docker Desktop).
- Das Python-Paket `docker` muss installiert sein (`pip install docker`).
