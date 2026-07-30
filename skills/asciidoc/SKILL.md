---
name: asciidoc
description: Erstellt AsciiDoc-Dokumente (mit PlantUML-Diagrammen, LaTeX-Formeln, Zitaten, Literaturverzeichnis) und konvertiert sie per Docker-Container in ein PDF. Nutze diesen Skill immer, wenn der Nutzer ein AsciiDoc-Dokument (.adoc) schreiben, erweitern oder als PDF ausgeben will — auch bei englischen Formulierungen wie "write an asciidoc document", "convert .adoc to pdf", "asciidoctor-pdf". Deckt auch Dokumente in Schriften von rechts nach links ab (Arabisch, Hebräisch, Persisch), etwa wenn eine Angabe oder Unterlage ins Arabische übersetzt und als PDF ausgegeben werden soll. Auch relevant, wenn nach einer technischen Dokumentation, einem Bericht oder einer Diplomarbeit mit Diagrammen/Formeln gefragt wird und AsciiDoc als Format genannt wird oder aus dem Kontext (vorhandene .adoc-Dateien im Projekt) sinnvoll ist. NICHT für reine Markdown-, Word- oder LaTeX-Dokumente ohne AsciiDoc-Bezug.
---

# AsciiDoc-Dokumente erstellen und in PDF konvertieren

Relative Pfade wie `scripts/…`, `references/…` und `assets/…` beziehen sich auf das Verzeichnis dieses Skills, nicht auf das Arbeitsverzeichnis des Users.

## Regeln für den AsciiDoc-Text

- Genau ein Satz pro Zeile. AsciiDoc behandelt Zeilenumbrüche innerhalb eines Absatzes wie Leerzeichen, das Ergebnis-PDF wird dadurch nicht beeinflusst — aber Diffs im Dokument bleiben dadurch auf Satzebene lesbar.
- Vor jeder Liste eine Leerzeile einfügen, sonst wird sie von manchen Renderern nicht als Liste erkannt.
- Quellen wie in der Vorlage zitieren: `^<<schluessel>>^` verweist auf einen Eintrag `[[[schluessel,1]]]` im Abschnitt `[bibliography]`. Keine Zitier-Platzhalter aus anderen Formaten wie `[cite]`, `[@key]` oder `\cite{}` verwenden, AsciiDoc kennt sie nicht und gibt sie als Text aus.
- Anker-IDs (auch die Schlüssel im Literaturverzeichnis) mit einem Buchstaben oder `_` beginnen. Eine ID mit einer Ziffer am Anfang erkennt Asciidoctor nicht als Anker, der Verweis darauf läuft ins Leere. Also `[[kapitel-2]]` und `<<kapitel-2>>`, nicht `<<2-kapitel>>`.
- PlantUML-Diagramme direkt im Dokument einbetten, mit `[plantuml,format=svg]` und einem `----`-Block (siehe Vorlage).
- `:hyphens:` (automatische Silbentrennung) zusammen mit `:lang:` setzen, z. B. `:lang: de` oder `:lang: en`. Ohne Wert nimmt `asciidoctor-pdf` die Trennsprache aus `:lang:`. Englisch in Kleinbuchstaben schreiben (`en` oder `en-US`): Nur kleines `en` wird auf die Trennmuster `en_us` abgebildet, `:lang: EN` bricht die Konvertierung mit `cannot load such file -- text/hyphen/language/en` ab. Ausnahme sind Dokumente von rechts nach links (siehe unten), die nicht über `asciidoctor-pdf` laufen.

## Vorlage

Die vollständige Vorlage mit allen Modulen (Codeblock mit Callouts, Zitate, PlantUML, LaTeX-Formeln, Bilder, Literaturverzeichnis) liegt in [references/vorlage.adoc](references/vorlage.adoc). Beim Anlegen eines neuen Dokuments von dieser Vorlage ausgehen und nur die tatsächlich benötigten Module übernehmen — nicht alle Beispielabschnitte blind in jedes Dokument kopieren.

### PlantUML Layout


## PlantUML Diagramme

Bette die PlantUML Diagramme in die AsciiDoc Datei ein.
Verwende dabei folgendes Layout, um eine gute Lesbarkeit zu erzielen:

```
skinparam shadowing false
skinparam classAttributeIconSize 0
skinparam defaultFontSize 15
skinparam ArrowThickness 1.5
skinparam class {
  BackgroundColor #ffffff
  HeaderBackgroundColor #ededed
  BorderColor #1d1d1b
  BorderThickness 1.5
  FontStyle bold
}
skinparam stereotypeCBackgroundColor #d1ebf7
skinparam stereotypeABackgroundColor #fdebd1
skinparam stereotypeIBackgroundColor #e5f4f1
skinparam stereotypeEBackgroundColor #e5f1d9
```

### Layoutdatei (YAML-Theme)

Wenn der User kein Theme angibt, verwende `references/vorlage.yml`.
Es erweitert das default Theme. Dessen Keys und Defaultwerte stehen in `data/themes/default-theme.yml` im Bündel `references/asciidoctor-pdf.bundle` (lesen wie im Abschnitt „Edge Cases“ beschrieben). Den neuesten Stand gibt es unter `https://raw.githubusercontent.com/asciidoctor/asciidoctor-pdf/refs/heads/main/data/themes/default-theme.yml`.

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

## Edge Cases: in der Implementierung nachsehen

Wenn die Doku offen lässt, wie `asciidoctor-pdf` ein Attribut, eine Rolle, einen Theme-Key oder eine Blockvariante behandelt, entscheidet die Implementierung.
Sie liegt samt Specs, Doku und eingebauten Themes in [references/asciidoctor-pdf.bundle](references/asciidoctor-pdf.bundle) und wird mit den Skripten des Skills **bundle-files** gelesen.
Die Datei ist 3 MB groß, deshalb nicht ganz laden, sondern so vorgehen (`<bundle-files>` ist das Skill-Verzeichnis von bundle-files, meist `~/.claude/skills/bundle-files`):

```bash
# overview: folders with abstracts
python <bundle-files>/scripts/read_toc.py references/asciidoctor-pdf.bundle --dir-level 1
# search file contents; hits come as path:line
python <bundle-files>/scripts/read_document.py references/asciidoctor-pdf.bundle --search "pdfwidth" "*/spec/*_spec.rb"
# read the lines around a hit, e.g. image_spec.rb:312
python <bundle-files>/scripts/read_document.py references/asciidoctor-pdf.bundle image_spec.rb --lines 300-340 -n
```

Fehlt der Skill bundle-files, geht es auch ohne ihn, weil das Bündel reiner Text mit einem Inhaltsverzeichnis (TOC) am Anfang ist:

- Grep nach `<dir ` in der Bündeldatei listet alle Ordner mit Zeilennummer. Ein Read von einer Ordnerzeile bis zur nächsten liefert das Abstract und die Dateieinträge dieses Ordners.
- Jeder Eintrag nennt Startzeile und Länge, z. B. `<entry name="image_spec.rb" start="43569" lines="3125">`. Ein Read mit `offset=start` und `limit=lines` liest genau diese Datei; Zeile n der Datei liegt im Bündel bei `start + n - 1`.
- Grep im Bündel liefert absolute Zeilennummern. Wähle daher zuerst die Datei über den TOC und beachte nur Treffer zwischen `start` und `start + lines`. Gehört ein Treffer zu keiner bekannten Datei, ist es der Eintrag mit dem größten `start` unter der Trefferzeile; Grep nach z. B. `start="2\d{4}"` (gleiche Stellenzahl, gleiche erste Ziffer, dann kleinere) grenzt die Kandidaten ein.

Musst du in einer Session mehr als ein- oder zweimal nachschlagen, biete dem User die Installation von bundle-files an, statt sie selbst auszuführen: `npx skills@latest add schletz/claude_settings --skill bundle-files -g -y --copy`. Die Skripte sind danach sofort unter `~/.claude/skills/bundle-files/scripts/` aufrufbar, der Skill selbst erscheint erst in einer neuen Session.

Die Specs (`spec/*_spec.rb`) sind die genaueste Quelle, weil jeder Test eine AsciiDoc-Eingabe und das erwartete PDF-Ergebnis oder die Log-Meldung zeigt.
Theme-Keys samt Defaults stehen in `data/themes/default-theme.yml` und auf den Seiten unter `docs/modules/theme`, die Verarbeitung selbst in `lib/asciidoctor/pdf/converter.rb` (eine `convert_<node>`-Methode pro Element).
Das Bündel gibt den Stand von `main` wieder (Version und Commit im Abstract der obersten Ebene), das Docker-Image dagegen ein veröffentlichtes Release.
Verhält sich die Konvertierung anders als das Bündel erwarten lässt, nennt der Abschnitt „Unreleased“ in `CHANGELOG.adoc` die Änderungen seit dem letzten Release.

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
- Optional: der Skill bundle-files zum Nachschlagen im Bündel. Ohne ihn geht es auch, siehe „Edge Cases“.
