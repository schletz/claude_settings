# Claude Code Settings

![](meme.png)

Meine persönliche Konfiguration für [Claude Code](https://claude.com/claude-code): globale Einstellungen,
Coding Conventions und drei Skills (Softwaredokumentation, AsciiDoc-Dokumente, Browserautomatisierung).
Alles landet in `%USERPROFILE%\.claude` und gilt für *alle* Projekte.

Die Installation besteht aus drei unabhängigen Schritten, weil die Teile aus drei verschiedenen Quellen
kommen.

## Installation

### Schritt 1: Konfiguration (`settings.json` und `CLAUDE.md`)

Eingabeaufforderung öffnen (keine Adminrechte nötig) und ausführen:

```bat
curl.exe -sL -o "%TEMP%\install_claude.ps1" https://raw.githubusercontent.com/schletz/claude_settings/main/install.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\install_claude.ps1"
```

Lädt [settings.json](settings.json) und [CLAUDE.md](CLAUDE.md) nach `%USERPROFILE%\.claude`. Findet das
Skript eine Codex-Installation, schreibt es die `CLAUDE.md` zusätzlich als `AGENTS.md` nach
`%USERPROFILE%\.codex` (siehe [Codex-User](#äquivalent-für-codex-user)). **Vorhandene Dateien werden ohne
Sicherung überschrieben** – eigene Anpassungen vorher sichern. Skills installiert dieser Schritt nicht.

### Schritt 2: Skills *document-software* und *asciidoc*

Installation über die [skills-CLI](https://www.npmjs.com/package/skills) (Node.js nötig, das Paket lädt
`npx` selbst):

```powershell
npx skills@latest add schletz/claude_settings --skill document-software --skill asciidoc -g -y --copy
```

Weitere Befehle: `--list` (Skills anzeigen), `npx skills@latest list -g` (installierte anzeigen),
`update -g` (aktualisieren), `remove -g <skill>` (entfernen).

> Das Repo enthält weitere, sehr spezielle Skills (Untertitel, Voiceover, Podcast, Videozusammenfassung,
> Repo-Anlage Spengergasse), die teils GPU oder GitHub-Rechte brauchen und daher nicht mitinstalliert werden.

### Schritt 3: Skill *playwright-cli*

Gehört zum Werkzeug `@playwright/cli` und wird von dessen eigenem Installer angelegt:

```powershell
npm install -g @playwright/cli@latest
playwright-cli install --skills
```

## Inhalt

| Datei im Repo | Ziel am eigenen Rechner | Schritt |
| --- | --- | --- |
| [settings.json](settings.json) | `%USERPROFILE%\.claude\settings.json` | 1 |
| [CLAUDE.md](CLAUDE.md) | `%USERPROFILE%\.claude\CLAUDE.md` | 1 |
| [skills/document-software/](skills/document-software/) | `%USERPROFILE%\.claude\skills\document-software\` | 2 |
| [skills/asciidoc/](skills/asciidoc/) | `%USERPROFILE%\.claude\skills\asciidoc\` | 2 |
| *(nicht im Repo)* | `%USERPROFILE%\.claude\skills\playwright-cli\` | 3 |

**settings.json** legt Modell (`opus[1m]`), Denktiefe (`effortLevel: high`) und Freigaben fest. Wichtig:
`permissions.defaultMode: bypassPermissions` – siehe Warnung unten.

**CLAUDE.md** ist die globale Hausordnung, die Claude in jeder Sitzung mitliest: lokale Umgebung
(Frameworks, IDEs, Pfade), Hinweise auf die globalen Skills, eine Eskalationsstrategie für die Websuche bei
HTTP 403, Sprachregeln (Antworten auf Deutsch/du, Code auf Englisch), Kommentar- und Pattern-Regeln (SOLID,
Single Responsibility), Datei-Struktur (one class per file) sowie die Regel, vor größeren Umbauten
nachzufragen und Prompt-Qualität rückzumelden.

> **Nach der Installation anpassen:** Der Abschnitt *Lokale Umgebung* beschreibt den Rechner des Autors –
> auf dem eigenen Rechner in `%USERPROFILE%\.claude\CLAUDE.md` korrigieren (siehe
> [Prüf-Prompt](#claudemd-nach-der-installation-prüfen-lassen) unten).

Zusätzlich kann dieselbe Datei projektbezogen angelegt werden (`CLAUDE.md` im Projektstamm, in Git
eingecheckt) für Regeln, die nur dort gelten.

**Skill *document-software*** erstellt eine Referenzdatei `<name>.md` neben bestehendem Code – kein
Benutzerhandbuch, sondern eine Doku für LLMs/neue Entwickler mit Invarianten, Fehlerpfaden und
Erweiterungspunkten, jede Aussage mit `Datei:Zeile` belegt. Aufruf implizit ("dokumentiere `parser.py`")
oder über `/document-software`.

**Skill *playwright-cli*** steuert einen Browser fern (Seiten öffnen, klicken, Formulare ausfüllen,
Screenshots, E2E-Tests) über Snapshots mit benannten Elementreferenzen statt Pixelkoordinaten. Liegt nicht
in diesem Repo, sondern gehört zu `@playwright/cli` (Installation siehe Schritt 3).

**Skill *asciidoc*** erstellt AsciiDoc-Dokumente (`.adoc`) mit PlantUML-Diagrammen, LaTeX-Formeln, Zitaten
und Literaturverzeichnis und konvertiert sie per Docker (`asciidoctor/docker-asciidoctor`) zu PDF.
Voraussetzung: Docker läuft, Python-Paket `docker` installiert (`pip install docker`). Aufruf implizit
oder über `/asciidoc`.

## ⚠️ Warnung: `"defaultMode": "bypassPermissions"`

Die mitgelieferte `settings.json` setzt `bypassPermissions` – **Claude Code fragt vor keiner Aktion mehr
nach.** Es liest, ändert und löscht Dateien, führt Shell-Befehle aus, installiert Pakete und ruft
Webseiten ab, alles ohne Bestätigung. Zusammen mit `skipDangerousModePermissionPrompt: true` entfällt
auch der Warnhinweis beim Start.

- Ein falsch verstandener Auftrag kann ungebremst Dateien überschreiben oder löschen – nur in Verzeichnissen
  unter Versionskontrolle arbeiten und regelmäßig committen.
- Fremde Webinhalte können Prompt-Injection enthalten, die Claude dann ausführt.
- Zugangsdaten und private Dateien im Arbeitsverzeichnis sind für Claude lesbar.

Wer das nicht will, entfernt `"defaultMode": "bypassPermissions"` (und am besten
`"skipDangerousModePermissionPrompt": true`) aus `%USERPROFILE%\.claude\settings.json`. Dann fragt Claude
vor jeder schreibenden/ausführenden Aktion nach; die Liste unter `permissions.allow` bleibt bestehen und
lässt sich per `/permissions` erweitern.

## CLAUDE.md nach der Installation prüfen lassen

Der Abschnitt *Lokale Umgebung* beschreibt den Rechner des Autors. Statt von Hand zu vergleichen, neuen
Chat öffnen und Claude selbst prüfen lassen:

```text
Prüfe den Abschnitt "Lokale Umgebung" in meiner globalen CLAUDE.md oder AGENTS.md
(%USERPROFILE%\.claude\CLAUDE.md bzw. %USERPROFILE%\.codex\AGENTS.md) gegen die tatsächlich auf diesem Rechner installierte Software.
Kontrolliere dabei:
- Windows-Version (winver bzw. Registry)
- installierte Framework-Versionen: .NET, Java, Python, Node.js (jeweils --version bzw. java -version)
- ob Docker installiert und der Docker-Daemon erreichbar ist
- ob git bash installiert ist
- die installierten IDEs (VS Code, Visual Studio mit den genannten Komponenten)
- den Pfad zum Browser (existiert die angegebene .exe?)
- ob das Home-Verzeichnis in der Datei mit %USERPROFILE% übereinstimmt

Liste Abweichungen auf und schlage konkrete Korrekturen für die Datei vor. Ändere die Datei erst,
wenn ich zugestimmt habe.
```

## Äquivalent für Codex-User

Wer statt Claude Code das [Codex CLI](https://developers.openai.com/codex/cli) einsetzt, findet dieselben
Konzepte unter anderem Namen:

| Datei in diesem Repo | Codex-Entsprechung | Ziel am eigenen Rechner |
| --- | --- | --- |
| `settings.json` | `config.toml` | `%USERPROFILE%\.codex\config.toml` |
| `CLAUDE.md` | `AGENTS.md` | `%USERPROFILE%\.codex\AGENTS.md` |

`AGENTS.md` installiert [install.ps1](install.ps1) automatisch mit, wenn ein `.codex`-Ordner existiert oder
`codex` im Suchpfad liegt. `config.toml` muss von Hand angelegt werden (eigene TOML-Syntax, Werte lassen
sich nicht direkt übernehmen).
