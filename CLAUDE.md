# Coding Conventions

## Lokale Umgebung

- OS: Windows 11 Pro Version 25H2
- Docker
- git bash
- Home Verzeichnis: C:\Users\Michael
- Browser: C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe
- Installierte Frameworks:
    - .NET 10
    - Java OpenJDK 25
    - Python 3.14
    - Node.js 25
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
    2. Erst wenn auch das scheitert, den Skill **playwright-cli** nehmen; der
       setzt Requests aus einem echten Browser ab.
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

- Antworte im Fließtext (Erklärungen, Zusammenfassungen, etc.) immer auf Deutsch.
- Verwende für die Userinteraktion im Chat immer lockere Sprache und "du".
- Code, commit messages, Bezeichner und sämtliche Code-Kommentare sind ausschließlich auf Englisch.

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

## Qualität des Prompts für die Implementierung von Features rückmelden

Für die Implementierung von Features ist ein guter Prompt essentiell.
Hilf dem User, sich zu verbessern.
Sage ihm, wenn ein Prompt schlecht (zu wenig Infos hat) oder zu detailliert (over-guidance) ist und dem Modell damit die nötigen Freiheiten nimmt.
Bei einfachen Aufträgen oder in Chatsituationen entfällt die Bewertung.
