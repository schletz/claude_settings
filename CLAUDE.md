# Coding Conventions

## Lokale Umgebung

- OS: Windows 11 Pro Version 25H2
- Docker
- git bash
- Installierte Frameworks:
    - .NET 10 (Aufruf mit dotnet)
    - Java OpenJDK 25
    - Python 3.14  (Aufruf mit python)
    - Node.js 26 (Aufruf mit node)
- Installierte IDEs:
    - VS Code
    - Visual Studio 2026

## Globale Skills

- **playwright-cli** für end to end Tests von Browserapplikationen.
- **document-software** für die Dokumentation von Software für einen Agent.

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

- Antworte im Fließtext (Erklärungen, Zusammenfassungen, Commit-Message-Vorschläge) immer auf Deutsch.
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
