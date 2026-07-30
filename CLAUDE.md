# Coding Conventions

## Lokale Umgebung

- **OS:** Windows 11 Pro Version 26H2
- **Docker**
- **git bash** 
- **Installierte Frameworks:**
    - .NET 10 (Aufruf mit dotnet)
    - Java OpenJDK 25
    - Python 3.14  (Aufruf mit python)
    - Node.js 26 (Aufruf mit node)
- **Installierte IDEs:**
    - VS Code
    - Visual Studio 2026

Mehrzeilige Skripte (Python, Shell) nicht über -c oder Heredoc im PowerShell-Tool übergeben, sondern mit dem Write-Tool in den Scratchpad schreiben und als Datei ausführen. Heredocs nur im Bash-Tool.

## Installierte Tools

### gh

Das github Command Line Tool ist authentifiziert und mit dem Befehl

`gh`

erreichbar.

Fehlt das Programm, biete dem User an, es mit `winget install --id GitHub.cli` zu laden und nach der Installation zum PATH hinzuzufügen.

### Markitdown

Konvertiert docx, pptx, xlsx, html, epub, msg, ipynb, csv als Markdown und gibt es in outfile utf8 codiert aus:

`python -m markitdown (infile) -o (outfile)`

Verwende das Tool, um einen schnellen Überblick über die Datei zu bekommen.
Layouts werden nur eingeschränkt konvertiert.
Für eine layoutgetreue Konvertierung (Tabellen, etc.) verwende spezialisierte Tools für das entsprechende Dateiformat.

Ohne die Option `-o` wird auf stdout ausgegeben, beachte in diesem Fall aber den Windows Zeichensatz (cp1252). Wenn du das Tool nicht hast, installiere es mit `pip install markitdown[all]`.

Für PDF nicht Markitdown verwenden, sondern PyMuPDF (siehe unten): Markitdown zerlegt Tabellen in PDFs zu Zeilensalat und erkennt keine Überschriften.

### PyMuPDF

Konvertiert PDF als Markdown mit Überschriften und Tabellen; Text aus Vektorgrafiken (z. B. UML-Diagrammen) bleibt erhalten. Für docx & Co. ist Markitdown besser, weil PyMuPDF diese erst zu PDF rendert und die Struktur rät.

In eine Datei (utf8):

`python -c "import os, sys, pymupdf; pymupdf.set_messages(path=os.devnull); open(sys.argv[2], 'w', encoding='utf-8').write(pymupdf.open(sys.argv[1]).to_markdown())" (infile).pdf (outfile).md`

Auf stdout (utf8, auch bei cp1252-Konsole):

`python -c "import os, sys, pymupdf; pymupdf.set_messages(path=os.devnull); sys.stdout.reconfigure(encoding='utf-8'); print(pymupdf.open(sys.argv[1]).to_markdown())" (infile).pdf`

`set_messages` ist nötig, weil PyMuPDF sonst Statusmeldungen auf stdout schreibt, die im Markdown landen.

Fehlt das Paket, biete dem User an, es mit `pip install --upgrade pymupdf` zu installieren.

### Ghostscript

Exportiert alle Seiten eines PDF als PNG Bilder für eine Vorbetrachtung.

`gswin64c.exe -q -sDEVICE=png16m -r70 -dFirstPage=1 -dLastPage=(page) -dNOPAUSE -dBATCH -sOutputFile=(directory)/page%d.png (pdf_file)`

Fehlt das Programm, biete dem User an, es von https://ghostscript.com/releases/gsdnld.html zu laden und nach der Installation zum PATH hinzuzufügen.

### resvg

Rendert SVG als PNG, z. B. um eine erzeugte Grafik zu prüfen. Die Größe kommt aus dem SVG, Systemschriften werden verwendet.

`resvg (infile.svg) (outfile.png) --zoom 2`

Für HTML innerhalb des SVG (`foreignObject`) stattdessen Brave headless verwenden, das rendert resvg nicht.

Fehlt das Programm, biete dem User an, es mit `winget install --id linebender.resvg` zu installieren.

### Playwright CLI samt Skill

playwright-cli sowie der Skill playwright-cli stehen zur Verfügung.

Fehlt das Programm, biete dem User an, das Programm und den Skill mit `npm install -g @playwright/cli@latest` und `playwright-cli install --skills` zu installieren.

## Skills zum Download

Folgende nützliche Skills können verwendet bzew. geladen werden:

### document-software

Erstellt die Dokumentation von Software für einen Agent.
Installation: `npx skills@latest add schletz/claude_settings --skill document-software -g -y --copy`

### asciidoc

Informationen und Skripts für die Erstellung und Konvertierung von AsciiDoc Dokumenten.
Installation: `npx skills@latest add schletz/claude_settings --skill asciidoc -g -y --copy`

### ideas

Sucht Ideen per RSS Newsfeeds. Nützlich, wenn z. B. Angaben oder Übungsbeispiele entwickelt werden sollen.
Installation: `npx skills@latest add schletz/claude_settings --skill ideas -g -y --copy`

### bundle-files

Fasst ein Projekt (z. B. Template samt PDF-Angabe) zu einer `.bundle`-Datei zusammen, die ein Agent über ein Inhaltsverzeichnis gezielt liest. Liest, ändert, durchsucht und entpackt bestehende Bündel.
Installation: `npx skills@latest add schletz/claude_settings --skill bundle-files -g -y --copy`

## Webrecherche

- **HTTP 403 von `WebFetch` heißt nicht „gesperrt", sondern „Client gefiltert".**
  `WebFetch` kann keine eigenen Header setzen und wird von Sites mit Bot-Schutz
  deshalb abgewiesen. Nicht auf eine schlechtere Quelle ausweichen und die
  Information nicht als unbelegbar melden, ohne vorher eskaliert zu haben.
- **Eskalationsreihenfolge bei 403:**
    1. `curl` über das Bash-Tool mit vollem Chrome-Header-Satz — `User-Agent`,
       `Accept`, `Accept-Language`, `Sec-CH-UA`, `Sec-CH-UA-Mobile`,
       `Sec-CH-UA-Platform`, `Sec-Fetch-Dest/Mode/Site/User`,
       `Upgrade-Insecure-Requests`, dazu `--compressed` und `-L`.
       Bleibt es bei 403, sofort weiter zu Schritt 2: Bot-Schutz wie Cloudflare
       erkennt `curl` schon am TLS-Verbindungsaufbau, weitere Header ändern
       daran nichts.
    2. Den Skill **playwright-cli** mit **sichtbarem** Edge nehmen:
       `playwright-cli open --headed --browser=msedge <URL>`. Ein Headless-Browser
       unterscheidet sich messbar von einem normalen Fenster und bleibt in der
       Cloudflare-Prüfung „Just a moment…“ hängen; ein sichtbarer Edge kommt
       durch wie der Browser des Users. Den Text mit
       `playwright-cli --raw eval "document.body.innerText" > <scratchpad>/seite.txt`
       sichern, danach `playwright-cli close`.
    3. Erscheint trotzdem ein Captcha, lasse es dem User lösen.
- **Antwort in eine Datei im Scratchpad schreiben**, nicht in die Konsole. Den
  Statuscode über `-w "%{http_code}"` mitnehmen, sonst hältst du eine
  Fehlerseite für Inhalt.
- **Rohes HTML nie mit dem Read-Tool lesen** — eine Nachrichtenseite hat leicht
  600 KB. Vorher mit einem kurzen Python-Skript (`re` + `html.unescape`) zu Text
  reduzieren, Skript-, Style- und Navigationszeilen wegwerfen, dann die
  Textdatei lesen.
- **Die Websuche ersetzt das Abrufen der Seite nicht.** Die Zusammenfassung eines
  Suchtreffers lässt regelmäßig genau die Zahl oder das Datum weg, wegen dessen
  du die Quelle aufgerufen hast.

## Sprache

- Verwende für die Userinteraktion im Chat immer lockere Sprache und "du".
- Code, Bezeichner und sämtliche Code-Kommentare sind ausschließlich auf Englisch.

## Kommentare

- Auf Funktions- und Klassenebene: Doc-Kommentare nach dem Standard der jeweiligen Sprache (JSDoc/TSDoc für JS/TS, docstrings/PEP 257 für Python, XML-Doc für C#, Javadoc für Java, etc.). Zielgruppe sind andere Entwickler.
- Nicht-triviale Logik wird durch Inline-Kommentare erklärt; Triviales bleibt unkommentiert.
- Bestehende Kommentare im Original übernehmen und – falls sich der Code ändert – inhaltlich anpassen, statt sie zu löschen.
- Keine Meta-Kommentare über die Änderung selbst (kein "// changed", "// added by Claude", "// new"). Änderungen sind im IDE-Diff sichtbar.

## Patterns

- Achte auf gängige Patterns wie SOLID oder DRY.
- Achte vor allem auf single responsibility.
- Wende alle Patterns pragmatisch an, vermeide over engineering.
- Verwende wenn immer möglich das Typkonzept des Compilers, um Fehler schon auf Compilerebene zu verhindern.

## Test und Metriken

- Ermittle nach dem Refactoring die Anzahl der Codezeilen. Sie sind ein Indiz für Verletzungen des single responsibility Prinzips.

## Datei-Struktur

- One class per file: pro Datei genau eine öffentliche Klasse/Top-Level-Komponente.
- Wenn eine Datei beim Bearbeiten unübersichtlich groß wird, sinnvoll auftrennen.

## Arbeitsweise

- Vor größeren Refactorings oder strukturellen Umbauten kurz nachfragen bzw. das Vorgehen skizzieren, statt ungefragt umzubauen.
- Getroffene Annahmen offenlegen, wenn eine Anforderung mehrdeutig ist.

## Erstellen und Bearbeiten von Skills

Vor jeder Änderung an einer SKILL.md den Skill **skill-creator** laden, auch bei kleinen Korrekturen. Für Skills gilt:

- **Allgemein halten:** Ein Skill wird für viele Prompts benutzt, nicht nur für den Fall, an dem gerade gearbeitet wird.
- **Schlank bleiben:** Was nicht zum Ergebnis beiträgt, wird gestrichen.
- **Das Warum erklären:** Regeln werden begründet (Zweck), statt starr vorgegeben.
- **Keine Historie:** Wie ein Fehler entstand, gehört nicht in den Skill. Bei beachteten Regeln tritt er nicht mehr auf.
- **Skripte bündeln:** Wiederkehrende Hilfsroutinen liegen in `scripts/`.
- **Minimale Shell-Logik:** Skills müssen auf Windows, macOS und Linux laufen. Sie enthalten deshalb nur den kleinsten gemeinsamen Nenner, den schon MS-DOS bot: einzelne Befehle mit Argumenten, `>`, `|`, `&&` und `||`. `curl` kann verwendet werden. Nichts, was von der Shell abhängt (Umgebungsvariablen, Wildcards, Anführungszeichen-Regeln, Schleifen, Heredocs) und keine Unix-Programme, die es unter Windows nicht gibt. Alles darüber hinaus (Schleifen, Parallelisierung, Pfadbehandlung, Textverarbeitung) erledigt ein Python-Skript.

**Skills nicht ungefragt ändern!** Wenn es aufgrund eines Use Cases eine begründete Änderung für einen bestehenden Skill gibt, schlage zuerst die Änderung vor und warte auf die Zustimmung des Users.
