# Coding Conventions

## Lokale Umgebung

| Kategorie  | Details                                                                          |
|------------|----------------------------------------------------------------------------------|
| OS         | Windows 11 Pro Version 26H2                                                      |
| Tools      | Docker, git bash                                                                 |
| Frameworks | .NET 10 (`dotnet`), Java OpenJDK 25, Python 3.14 (`python`), Node.js 26 (`node`) |
| IDEs       | VS Code, Visual Studio 2026                                                      |

Mehrzeilige Skripte (Python, Shell) nicht über `-c` oder Heredoc im PowerShell-Tool übergeben, sondern mit dem Write-Tool in den Scratchpad schreiben und als Datei ausführen. Heredocs nur im Bash-Tool.

## Installierte Tools

### gh
GitHub CLI, authentifiziert, Aufruf: `gh`
Fehlt es: User anbieten, `winget install --id GitHub.cli` auszuführen und PATH zu ergänzen.

### Markitdown
Konvertiert docx, pptx, xlsx, html, epub, msg, ipynb, csv zu Markdown:
`python -m markitdown (infile) -o (outfile)` (UTF-8-Ausgabe)

- Nutzen für schnellen Überblick; Layouts nur eingeschränkt konvertiert.
- Für layoutgetreue Konvertierung (Tabellen etc.) spezialisierte Tools je Format verwenden.
- Ohne `-o`: Ausgabe auf stdout, Achtung Windows-Zeichensatz (cp1252).
- Für PDF **nicht** Markitdown verwenden (zerlegt Tabellen zu Zeilensalat, erkennt keine Überschriften) — stattdessen PyMuPDF.
- Fehlt das Tool: `pip install markitdown[all]`

### PyMuPDF
Konvertiert PDF zu Markdown inkl. Überschriften/Tabellen; Text aus Vektorgrafiken (z. B. UML) bleibt erhalten. Für docx & Co. ist Markitdown besser (PyMuPDF rendert diese erst zu PDF und rät die Struktur).

In Datei (UTF-8):
```
python -c "import os, sys, pymupdf; pymupdf.set_messages(path=os.devnull); open(sys.argv[2], 'w', encoding='utf-8').write(pymupdf.open(sys.argv[1]).to_markdown())" (infile).pdf (outfile).md
```

Auf stdout (UTF-8, auch bei cp1252-Konsole):
```
python -c "import os, sys, pymupdf; pymupdf.set_messages(path=os.devnull); sys.stdout.reconfigure(encoding='utf-8'); print(pymupdf.open(sys.argv[1]).to_markdown())" (infile).pdf
```

`set_messages` nötig, da PyMuPDF sonst Statusmeldungen auf stdout schreibt, die im Markdown landen.
Fehlt das Paket: `pip install --upgrade pymupdf`

### Ghostscript
Exportiert PDF-Seiten als PNG zur Vorbetrachtung:
```
gswin64c.exe -q -sDEVICE=png16m -r70 -dFirstPage=1 -dLastPage=(page) -dNOPAUSE -dBATCH -sOutputFile=(directory)/page%d.png (pdf_file)
```
Fehlt es: User anbieten, von https://ghostscript.com/releases/gsdnld.html zu laden und PATH zu ergänzen.

### resvg
Rendert SVG als PNG (z. B. zur Prüfung erzeugter Grafiken). Größe kommt aus dem SVG, Systemschriften werden verwendet.
`resvg (infile.svg) (outfile.png) --zoom 2`
Für HTML innerhalb des SVG (`foreignObject`) stattdessen Brave headless verwenden (resvg rendert das nicht).
Fehlt es: User anbieten, `winget install --id linebender.resvg` auszuführen.

### Playwright CLI samt Skill
`playwright-cli` und der Skill `playwright-cli` stehen zur Verfügung.
Fehlt es: User anbieten, mit `npm install -g @playwright/cli@latest` und `playwright-cli install --skills` zu installieren.

## Skills zum Download

| Skill | Zweck | Installation |
|---|---|---|
| document-software | Erstellt Software-Dokumentation für einen Agent | `npx skills@latest add schletz/claude_settings --skill document-software -g -y --copy` |
| asciidoc | Infos/Skripte für Erstellung und Konvertierung von AsciiDoc-Dokumenten | `npx skills@latest add schletz/claude_settings --skill asciidoc -g -y --copy` |
| ideas | Sucht Ideen per RSS-Newsfeeds, nützlich für Angaben/Übungsbeispiele | `npx skills@latest add schletz/claude_settings --skill ideas -g -y --copy` |
| bundle-files | Fasst ein Projekt zu einer `.bundle`-Datei zusammen (Agent liest per Inhaltsverzeichnis gezielt); liest/ändert/durchsucht/entpackt bestehende Bündel | `npx skills@latest add schletz/claude_settings --skill bundle-files -g -y --copy` |

## Webrecherche

- **HTTP 403 von `WebFetch` heißt "Client gefiltert", nicht "gesperrt".** `WebFetch` kann keine eigenen Header setzen und wird von Sites mit Bot-Schutz deshalb abgewiesen. Nicht auf eine schlechtere Quelle ausweichen oder Info als unbelegbar melden, ohne vorher eskaliert zu haben.
- **Eskalationsreihenfolge bei 403:**
  1. `curl` über das Bash-Tool mit vollem Chrome-Header-Satz — `User-Agent`, `Accept`, `Accept-Language`, `Sec-CH-UA`, `Sec-CH-UA-Mobile`, `Sec-CH-UA-Platform`, `Sec-Fetch-Dest/Mode/Site/User`, `Upgrade-Insecure-Requests`, dazu `--compressed` und `-L`. Bleibt 403 bestehen, sofort zu Schritt 2 (Cloudflare & Co. erkennen `curl` schon am TLS-Handshake, weitere Header ändern nichts).
  2. Skill **playwright-cli** mit **sichtbarem** Edge: `playwright-cli open --headed --browser=msedge <URL>`. Headless unterscheidet sich messbar von einem normalen Fenster und bleibt bei Cloudflares "Just a moment…" hängen; sichtbarer Edge kommt durch. Text sichern mit `playwright-cli --raw eval "document.body.innerText" > <scratchpad>/seite.txt`, danach `playwright-cli close`.
  3. Erscheint trotzdem ein Captcha: User lösen lassen.
- **Antwort in eine Datei im Scratchpad schreiben**, nicht in die Konsole. Statuscode mit `-w "%{http_code}"` mitnehmen, sonst wird eine Fehlerseite für Inhalt gehalten.
- **Rohes HTML nie mit dem Read-Tool lesen** (Nachrichtenseiten oft 600 KB). Vorher per kurzem Python-Skript (`re` + `html.unescape`) zu Text reduzieren, Skript-/Style-/Navigationszeilen entfernen, dann die Textdatei lesen.
- **Websuche ersetzt nicht das Abrufen der Seite.** Zusammenfassungen von Suchtreffern lassen regelmäßig genau die Zahl/das Datum weg, wegen dessen die Quelle aufgerufen wurde.

## Sprache

- Userinteraktion im Chat: locker, "du".
- Code, Bezeichner, Code-Kommentare: ausschließlich Englisch.

## Kommentare

- Funktions-/Klassenebene: Doc-Kommentare nach Sprachstandard (JSDoc/TSDoc, docstrings/PEP 257, XML-Doc, Javadoc etc.), Zielgruppe andere Entwickler.
- Nicht-triviale Logik durch Inline-Kommentare erklären; Triviales bleibt unkommentiert.
- Bestehende Kommentare übernehmen und bei Codeänderung inhaltlich anpassen statt löschen.
- Keine Meta-Kommentare über die Änderung selbst (kein "// changed", "// added by Claude", "// new") — Änderungen sind im IDE-Diff sichtbar.

## Patterns

- Gängige Patterns (SOLID, DRY) beachten, vor allem Single Responsibility.
- Patterns pragmatisch anwenden, Over-Engineering vermeiden.
- Wo möglich das Typkonzept des Compilers nutzen, um Fehler schon zur Compilezeit zu verhindern.

## Test und Metriken

- Nach Refactoring die Anzahl der Codezeilen ermitteln — Indiz für Single-Responsibility-Verletzungen.

## Datei-Struktur

- One class per file: pro Datei genau eine öffentliche Klasse/Top-Level-Komponente.
- Unübersichtlich große Dateien beim Bearbeiten sinnvoll auftrennen.

## Arbeitsweise

- Vor größeren Refactorings/strukturellen Umbauten kurz nachfragen bzw. Vorgehen skizzieren statt ungefragt umzubauen.
- Getroffene Annahmen bei mehrdeutigen Anforderungen offenlegen.

## Erstellen und Bearbeiten von Skills

Vor jeder Änderung an einer SKILL.md den Skill **skill-creator** laden, auch bei kleinen Korrekturen.

Regeln für Skills:

- **Allgemein halten:** Ein Skill wird für viele Prompts benutzt, nicht nur für den aktuellen Fall.
- **Schlank bleiben:** Was nicht zum Ergebnis beiträgt, wird gestrichen.
- **Größe im Auge behalten:** Tokens der SKILL.md zählen; bei zu großen Dateien Aufteilung vorschlagen.
- **Das Warum erklären:** Regeln werden begründet (Zweck), statt starr vorgegeben.
- **Keine Historie:** Wie ein Fehler entstand, gehört nicht in den Skill — bei beachteten Regeln tritt er nicht mehr auf.
- **Skripte bündeln:** Wiederkehrende Hilfsroutinen liegen in `scripts/`.
- **Minimale Shell-Logik:** Skills müssen auf Windows, macOS, Linux laufen. Nur kleinster gemeinsamer Nenner (wie MS-DOS): einzelne Befehle mit Argumenten, `>`, `|`, `&&`, `||`. `curl` erlaubt. Nichts Shell-Abhängiges (Umgebungsvariablen, Wildcards, Anführungszeichen-Regeln, Schleifen, Heredocs) und keine fehlenden Unix-Programme unter Windows. Alles Weitere (Schleifen, Parallelisierung, Pfadbehandlung, Textverarbeitung) übernimmt ein Python-Skript.

**Skills nicht ungefragt ändern!** Bei begründetem Änderungsbedarf für einen bestehenden Skill: zuerst Änderung vorschlagen und Zustimmung des Users abwarten.