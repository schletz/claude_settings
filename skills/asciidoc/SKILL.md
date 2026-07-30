---
name: asciidoc
description: Erstellt AsciiDoc-Dokumente (mit PlantUML-Diagrammen, LaTeX-Formeln, Zitaten, Literaturverzeichnis) und konvertiert sie per Docker-Container in ein PDF. Nutze diesen Skill immer, wenn der Nutzer ein AsciiDoc-Dokument (.adoc) schreiben, erweitern oder als PDF ausgeben will — auch bei englischen Formulierungen wie "write an asciidoc document", "convert .adoc to pdf", "asciidoctor-pdf". Deckt auch Dokumente in Schriften von rechts nach links ab (Arabisch, Hebräisch, Persisch), etwa wenn eine Angabe oder Unterlage ins Arabische übersetzt und als PDF ausgegeben werden soll. Auch relevant, wenn nach einer technischen Dokumentation, einem Bericht oder einer Diplomarbeit mit Diagrammen/Formeln gefragt wird und AsciiDoc als Format genannt wird oder aus dem Kontext (vorhandene .adoc-Dateien im Projekt) sinnvoll ist. NICHT für reine Markdown-, Word- oder LaTeX-Dokumente ohne AsciiDoc-Bezug.
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

## Arabisch, Hebräisch, Persisch (Schrift von rechts nach links)

`asciidoctor-pdf` kann diese Sprachen nicht setzen: Arabische Buchstaben erscheinen unverbunden, die Zeilen laufen von links nach rechts. Solche Dokumente konvertiert daher [scripts/convert_rtl_to_pdf.py](scripts/convert_rtl_to_pdf.py). Es erzeugt im selben Docker-Image HTML, fügt [assets/rtl.css](assets/rtl.css) ein (Schreibrichtung, Systemschriften mit arabischen/hebräischen Glyphen) und druckt die Seite mit dem Chromium von Playwright als A4-PDF mit Seitenzahlen.

```bash
python scripts/convert_rtl_to_pdf.py "<Arbeitsverzeichnis>" "<Dateiname.adoc>"
```

Ein Layout-YAML gibt es hier nicht, das Aussehen bestimmt `assets/rtl.css`. Zwischendateien (HTML, Diagramm-SVGs) räumt das Skript selbst weg.

Im Dokument auf Folgendes achten. In RTL-Text bestimmt der Unicode-Bidi-Algorithmus die Reihenfolge. Englische Bezeichner mit Klammern, Doppelpunkten oder Formeln landen ohne Hilfe an der falschen Stelle, etwa `()CalculatePrice` statt `CalculatePrice()`:

- Im Header `:lang: ar` (bzw. `he`, `fa`) setzen, kein `:hyphens:`. Admonition-Titel übersetzen (`:note-caption: ملاحظة`, `:tip-caption: نصيحة`, …), weil das Skript Text-Labels statt Icons ausgibt.
- `_kursiv_`, `*fett*` und `` `code` `` sind für links-nach-rechts-Inhalt gedacht. Das CSS isoliert sie als LTR und verhindert Umbrüche darin. Deshalb Bezeichner, Dateinamen und kurze englische Begriffe so auszeichnen und kurz halten.
- Arabischen Text hervorheben mit der Rolle `.rtl`: `[.rtl]*مثال*:`. Satzzeichen nach der Hervorhebung außerhalb lassen, sonst rutschen sie auf die falsche Seite.
- Formeln und Zahlenausdrücke ohne Auszeichnung in `[.ltr]#6 × 10 + 100 × 5 = 560#` setzen. Ebenso englische Wörter mit Bindestrich in Fließtext, z. B. `([.ltr]#read-only#)`, damit sie nicht am Bindestrich umbrechen.
- Zahlenbereiche wie „48 - 42“ werden in RTL gespiegelt gelesen. Besser in Worten formulieren („من 42 إلى 48“) oder in `[.ltr]#…#` setzen.
- Nach arabischen Präfixen ohne Leerzeichen (z. B. „و“ = „und“) greift die einfache Auszeichnung nicht, weil davor ein Buchstabe steht. Dort `**Customer**` bzw. `__Datei.cs__` schreiben.
- Tabellen mit englischem Inhalt (z. B. Programmausgaben) bekommen die Rolle `[.ltr%header,cols="…"]`. Sie laufen dann wie im Original von links nach rechts.
- Codeblöcke und PlantUML-Diagramme bleiben automatisch links-nach-rechts.

Das PDF anschließend seitenweise als Bild rendern und ansehen. Bidi-Fehler fallen nur visuell auf, nicht in einer Fehlermeldung.

## Voraussetzungen

- Docker muss laufen (lokal per Docker Desktop).
- Das Python-Paket `docker` muss installiert sein (`pip install docker`).
- Nur für RTL-Dokumente: Playwright für Python mit Chromium (`pip install playwright` und `python -m playwright install chromium`).
