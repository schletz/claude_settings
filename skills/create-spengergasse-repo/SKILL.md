---
name: create-spengergasse-repo
description: 'Legt in der GitHub-Organisation Die-Spengergasse ein privates Repo an und pusht einen main Branch mit README.md. Zwei Modi — Schüler-Modus: ein Repo pro Schüler/in mit Write-Zugriff für einen Account; Projekt-Modus (--projekt): ein gemeinsames Repo für mehrere Studierende (Projekte, Diplomarbeiten) mit Admin-Zugriff für alle, plus ein damit verlinktes GitHub Project (v2) Board, auf dem dieselben Mitglieder ebenfalls Admin sind. Kann das Repo optional gleich lokal klonen. Nutze diesen Skill immer, wenn der User ein neues Schüler-/Klassen-/Projekt-Repo für die Spengergasse anlegen will, einen Account einem Repo zuweisen will, ein GitHub Project/Board für ein Projekt-/Diplomarbeit-Repo will, oder Formulierungen wie "Repo anlegen", "Schüler-Repo", "Projekt-Repo", "Diplomarbeit-Repo", "GitHub-Zugriff geben/zuweisen", "Projekt/Board anlegen" im Kontext der Organisation die-spengergasse/Die-Spengergasse fallen — auch wenn nur einzelne Angaben (Klasse, Name, Repo-URL, Account) genannt werden. Unterstützt auch Batch-Anlage über eine CSV/JSON-Datei, für eine ganze Klasse oder für mehrere Projektteams.'
---

# Spengergasse Schüler-/Projekt-Repo anlegen

Legt private Repos in der Organisation `Die-Spengergasse` an (Org-Slug ist case-insensitive, in URLs taucht sowohl `die-spengergasse` als auch `Die-Spengergasse` auf: https://github.com/Die-Spengergasse). Zwei Modi, siehe [Schüler-Modus vs. Projekt-Modus](#schüler-modus-vs-projekt-modus). Die eigentliche Logik steckt in [`scripts/create_repo.py`](scripts/create_repo.py) — ruf das Skript aus, statt die Schritte einzeln nachzubauen.

## Sicherheitshinweis: niemals Org-weite Rechte vergeben

**Dieser Skill vergibt ausschließlich Zugriff auf einzelne Repos und einzelne GitHub-Project-Boards — niemals auf die Organisation `Die-Spengergasse` als Ganzes.** Das ist bewusst eng gehalten: Der Account, der den Skill ausführt (der `gh`-Token des Users), hat selbst Admin-Rechte auf die Organisation — ein Fehler hier hätte also nicht nur Folgen für ein einzelnes Repo, sondern potenziell für die ganze Organisation.

Unabhängig davon, wie die Anfrage formuliert ist:

- **Niemals** einen Account als Org-Mitglied hinzufügen oder zu einem Org-Team hinzufügen (z. B. über `gh api orgs/<org>/memberships/<user>` oder `gh api orgs/<org>/teams/...`).
- **Niemals** Org-weite Rollen vergeben oder ändern (Owner, Org-Admin, Billing-Manager) oder Org-Settings anfassen (Default-Repository-Permissions, Member-Privileges, SSO/SAML, etc.).
- Erlaubt sind **ausschließlich** Repo-Collaborator-Rechte (`push`/`admin` auf genau einem Repo, siehe [Schüler-Modus vs. Projekt-Modus](#schüler-modus-vs-projekt-modus)) und Project-Board-Collaborator-Rechte (`ADMIN` auf genau einem Board) — beides bleibt strikt auf das eine Repo bzw. das eine Board beschränkt und darf nie auf mehrere Repos, das ganze Board-Portfolio oder die Organisation ausgeweitet werden.
- Nimmt ein per Collaborator-Einladung hinzugefügter Account die Einladung an und wird dadurch offizielles Org-Mitglied, ist das normales, von GitHub gesteuertes Verhalten — keine bewusste Org-Mitgliedschaft, die dieser Skill selbst vergibt, und kein Grund, zusätzlich noch Org-Rechte nachzuschieben.
- Klingt eine Anfrage nach Org-weiten Rechten (z. B. „gib X Zugriff auf die ganze Organisation", „mach Y zum Owner", „X soll überall Admin sein"), lehne das im Rahmen dieses Skills ab und erkläre, dass er absichtlich nur repo-/board-scoped Zugriff vergeben kann.

## Naming Convention für Repo-Namen

Reponamen sind **immer kleingeschrieben** und setzen sich aus festen Bausteinen zusammen. Kennst du nur einzelne Bausteine (z. B. Klasse + Fach + Schulaccount, oder Klasse + Projektname statt der vollen `--repo-url`), bau den Reponamen selbst nach diesem Schema zusammen, statt beim User extra nachzufragen — frag nur nach, wenn ein Baustein wirklich fehlt oder erkennbar nicht ins jeweilige Muster passt.

### Bausteine

| Baustein | Muster | Beispiele |
|---|---|---|
| Schuljahr | `^sj\d{2}-?\d{2}$` | `sj26-27` (Standarddarstellung, mit Bindestrich) bzw. `sj2627`; die zweite Zahl ist immer die erste + 1 |
| Klasse | `^[1-8][a-z][abckhf][a-z]{2,3}$` | `5ahif`, `8acmna`, `3afitm` |
| Fach | `^[a-zäöüß0-9]{1,6}$` | `e`, `pos`, `dsai` |
| Schulaccount | `^[a-z]{3}\d+$` | `sch123456`, `kur210534` — der **Schul**account, nicht der GitHub-Accountname (der ist ein eigener Wert, siehe `--github-user`) |
| Projektname | ein Wort | `gutachtenmanager` |

### Schemata

- **Unterrichtsrepos** (Schüler-Modus): `(schuljahr)-(klasse)-(fach)-(schulaccount)`, z. B. `sj26-27-5caif-pos-kur210534`. Der letzte Baustein ist der **Schulaccount** der/des Schülers/Schülerin, nicht ihr/sein GitHub-Accountname — die beiden können unterschiedliche Strings sein und werden im Skript auch getrennt behandelt (Schulaccount steckt nur im Reponamen, der GitHub-Accountname geht separat über `--github-user`).
- **Projektrepos** (Projekt-Modus, auch Diplomarbeiten): `(schuljahr)-(klasse)-da-(projektname)`, z. B. `sj26-27-5caif-da-gutachtenmanager`. Das feste Segment `da` markiert Projekt-/Diplomarbeitenrepos.

## Schüler-Modus vs. Projekt-Modus

| | **Schüler-Modus** (Standard) | **Projekt-Modus** (`--projekt`) |
|---|---|---|
| Wann | Ein Repo pro Schüler/in (z. B. WMC-Übungen) | **Ein gemeinsames Repo für mehrere Studierende** — Projekte, Diplomarbeiten |
| Zugriff | **Write** für genau einen Account | **Admin** für alle angegebenen Mitglieder (damit das Team selbst Branch-Protection-Rules etc. definieren kann) |
| GitHub Project (Board) | Wird nicht angelegt | Wird zusätzlich angelegt (oder wiederverwendet, falls unter demselben Titel bereits mit dem Repo verlinkt) und mit dem Repo verlinkt; alle Mitglieder werden dort ebenfalls **Admin** — vorausgesetzt der `project`-Scope ist vorhanden, siehe [Voraussetzungen](#voraussetzungen) |
| Existiert das Repo schon? | Ganzer Eintrag wird übersprungen (auch kein Collaborator-Zuweisen) | Nur README wird übersprungen (Team arbeitet evtl. schon damit); Collaborator-Zuweisen (Repo **und** Project Board) läuft **trotzdem** für alle Mitglieder — macht erneute Aufrufe sicher, z. B. um später ein Mitglied hinzuzufügen oder einen falsch getippten Usernamen zu korrigieren |
| Ungültiger Account | Bricht den ganzen Eintrag ab | Bricht nur dieses eine Mitglied ab, Rest läuft weiter |
| README | Ein Name | Liste aller Mitglieder, optional Tabelle mit individuellen Themenstellungen pro Mitglied, optionaler eigener Titel |

Nutze **Projekt-Modus** immer, wenn mehrere Studierende gemeinsam an einem Repo arbeiten sollen (typisch: Diplomarbeiten-Gruppen, Klassen-/Teamprojekte) — nicht den Schüler-Modus mehrfach mit derselben Repo-URL aufrufen, das würde ab dem zweiten Aufruf "already exists" melden und **keinen weiteren Collaborator hinzufügen**.

## Warum die feste Prüfreihenfolge wichtig ist

Ein einfacher unauthentifizierter HTTP-404-Check kann ein privates Repo nicht von einem nicht existierenden Repo unterscheiden — beide liefern 404. Deshalb prüft das Skript über die authentifizierte `gh`-Session (`gh repo view`), die private Repos korrekt als existent erkennt. Existiert das Repo bereits, wird **nichts** angelegt oder zugewiesen — das Skript meldet das nur und beendet den jeweiligen Eintrag sauber. Das macht wiederholte Aufrufe (z. B. für dieselbe Klasse in einem späteren Semester nochmal ausgeführt) ungefährlich statt fehlerhaft.

## Voraussetzungen

- `gh` CLI ist installiert und bei einem Account eingeloggt, der Lese-/Schreibrechte auf die Organisation hat (prüfbar mit `gh auth status`).
- `git` ist installiert.
- Python 3 ist installiert (das Skript nutzt nur die Standardbibliothek).
- **Nur für Projekt-Modus mit GitHub-Project-Board:** Der `gh`-Token braucht zusätzlich den OAuth-Scope `project` (`gh project create`/`link` und die GraphQL-Collaborator-Mutation brauchen ihn; die Standard-Scopes von `gh auth login` reichen dafür nicht). Prüfe das **vor** dem Aufruf des Skripts selbst mit `gh auth status` und schau in der Zeile `Token scopes:` nach `'project'`.

  **Fehlt der Scope, führe den Refresh nicht selbst über das Bash-Tool aus** (der Device-Code-Flow braucht eine Bestätigung im Browser des Users und blockiert dabei unnötig lange). Gib dem User stattdessen dieses Kommando zum selbst Ausführen in seiner eigenen Konsole:

  ```bash
  gh auth refresh -h github.com -s project
  ```

  Warte danach auf seine Bestätigung (z. B. über `AskUserQuestion`), bevor du das Skript im Projekt-Modus aufrufst. Fehlt der Scope trotzdem noch, bricht das Skript deswegen nicht ab — es legt Repo und Collaborator-Zugriff wie gewohnt an, überspringt aber das Project-Board mit einer klaren Meldung samt demselben Kommando.

## Eingaben — Schüler-Modus

Entweder als Einzelwerte, oder gesammelt für eine ganze Klasse über eine Datei.

**Einzeln:**
- `--klasse` (z. B. `5caif`, siehe [Naming Convention](#naming-convention-für-repo-namen))
- `--name` (Vor- und Zuname, z. B. `Michael Schletz`)
- `--schuljahr` (z. B. `2026/27`)
- `--repo-url` — volle GitHub-URL (`https://github.com/Die-Spengergasse/sj26-27-5caif-pos-kur210534`), `<owner>/<repo>` (`Die-Spengergasse/sj26-27-5caif-pos-kur210534`), oder ein bloßer Reponame (`sj26-27-5caif-pos-kur210534`) — dann wird automatisch die Org `Die-Spengergasse` angenommen. Egal welche Form übergeben wird, im README landet immer die volle kanonische URL. Der letzte Baustein ist der **Schulaccount**, nicht zwangsläufig derselbe String wie `--github-user`.
- `--github-user` (GitHub-Accountname — eigener Wert, unabhängig vom Schulaccount im Reponamen, z. B. `kurta-schueler`)
- `--clone-dir` (optional) — Basisordner, in den das Repo zusätzlich lokal geklont (bzw. bei erneutem Aufruf aktualisiert) wird, als `<clone-dir>/<klasse>/<repo>`

**Batch über `--data-file`:** CSV oder JSON mit einer Zeile/einem Objekt pro Schüler und den Spalten/Keys `klasse,name,schuljahr,repo_url,github_user`. Jeder Eintrag wird unabhängig verarbeitet — ein Fehler bei einem Schüler (z. B. unbekannter Account) bricht nicht den ganzen Lauf ab, sondern nur diesen einen Eintrag.

## Eingaben — Projekt-Modus (`--projekt`)

- `--klasse`, `--schuljahr`, `--repo-url` — wie im Schüler-Modus.
- `--titel` (optional) — Projekt-/Diplomarbeitstitel für die README-Überschrift; fehlt er, wird wie im Schüler-Modus der Repo-Name verwendet.
- `--mitglied "Name:github_user"` oder `--mitglied "Name:github_user:Thema"` — **wiederholbar**, ein Aufruf pro Teammitglied. Der optionale dritte Teil ist die individuelle Themenstellung dieser Person; sobald mindestens ein Mitglied ein Thema hat, baut das Skript automatisch die Tabelle „Individuelle Themenstellungen" ins README.
- `--clone-dir` (optional) — wie im Schüler-Modus.

**Batch über `--data-file`:** gleiche Spalten wie im Schüler-Modus (`klasse,name,schuljahr,repo_url,github_user`), plus optional `thema` und/oder `titel`. Mehrere Zeilen mit **derselben** `repo_url` werden automatisch zu einem gemeinsamen Projekt-Eintrag gruppiert — eine Zeile pro Teammitglied, wie beim manuellen Anlegen einer Klassenliste, nur dass hier alle mit derselben `repo_url` ein Team bilden.

## Ablauf pro Eintrag im Schüler-Modus (macht das Skript automatisch)

1. Org und Repo-Name aus der Repo-Angabe extrahieren (volle URL, `<owner>/<repo>`, oder bloßer Reponame → Org `Die-Spengergasse` wird angenommen).
2. Prüfen, ob das Repo existiert (`gh repo view`, authentifiziert → erkennt auch private Repos korrekt). Existiert es: Meldung „already exists, nothing created" und weiter zum nächsten Eintrag — **kein** Create, **kein** Collaborator-Zuweisen.
3. Prüfen, ob der GitHub-Account existiert (`gh api users/<user>`). Existiert er nicht: Abbruch für diesen Eintrag, nichts wird angelegt.
4. Privates Repo anlegen: `gh repo create <owner>/<repo> --private`.
5. `main` Branch mit README.md pushen. Dafür wird lokal ein Wegwerf-Git-Repo initialisiert und über `gh`s eigenen Credential-Helper (scoped auf diesen einen Aufruf, ohne die globale Git-Config zu verändern) gepusht.
6. GitHub-User mit Write-Zugriff hinzufügen: `gh api repos/<owner>/<repo>/collaborators/<user> --method PUT -f permission=push`. Ist der Account nicht bereits Org-Mitglied, erzeugt GitHub daraus eine offene Einladung, die der Schüler noch annehmen muss — das ist normales GitHub-Verhalten, nicht steuerbar.
7. Nur wenn `--clone-dir` angegeben ist: Repo lokal nach `<clone-dir>/<klasse>/<repo>` klonen (`gh repo clone`, nutzt automatisch die gh-Session, auch für private Repos). Das passiert unabhängig davon, ob das Repo gerade neu angelegt wurde oder schon existierte — läuft also auch beim erneuten Aufruf für bereits vorhandene Repos. Existiert der Zielordner schon, wird stattdessen nur ein `git pull --ff-only` gemacht statt neu zu klonen.

## Ablauf pro Eintrag im Projekt-Modus (macht das Skript automatisch)

1. Org und Repo-Name aus der Repo-Angabe extrahieren, wie im Schüler-Modus.
2. Prüfen, ob das Repo existiert. Existiert es **nicht**: privates Repo anlegen und README mit allen Mitgliedern (und ggf. Themen-Tabelle) pushen. Existiert es **bereits**: README wird nicht angerührt (das Team arbeitet damit ggf. schon) — es geht direkt weiter zu Schritt 3.
3. Für **jedes** Mitglied unabhängig: Account-Existenz prüfen und Admin-Zugriff auf dem Repo vergeben (`permission=admin` statt `push`). Ein ungültiger Account bricht nur dieses eine Mitglied ab, nicht den Rest des Teams oder das Repo. Das läuft immer, auch wenn Schritt 2 wegen bereits existierendem Repo übersprungen wurde — dadurch kann derselbe Aufruf später erneut ausgeführt werden, um ein weiteres Mitglied hinzuzufügen oder eine falsch getippte GitHub-Kennung zu korrigieren.
4. **Nur wenn der `gh`-Token den `project`-Scope hat** (siehe [Voraussetzungen](#voraussetzungen), einmal vorab für den ganzen Lauf geprüft): GitHub-Project-Board anlegen oder wiederverwenden.
   - Titel = `--titel` (bzw. `titel`-Spalte), sonst wie im README der Repo-Name.
   - Erst wird per GraphQL geschaut, ob unter dem Repo bereits ein Project V2 mit genau diesem Titel verlinkt ist (`repository.projectsV2`) — Projects sind anders als Repos nicht eindeutig über den Namen, deshalb dieser Titel-Abgleich als Ersatz für die sonstige „existiert schon"-Prüfung. Gibt es einen Treffer, wird der wiederverwendet statt ein Duplikat anzulegen.
   - Sonst: `gh project create --owner <org> --title <titel>`, danach `gh project link <nummer> --owner <org> --repo <owner>/<repo>`.
   - Jedes im vorigen Schritt erfolgreich geprüfte Mitglied (per REST-`node_id`, aus demselben Account-Check wiederverwendet) wird per GraphQL-Mutation `updateProjectV2Collaborators` mit Rolle `ADMIN` auf dem Board eingetragen — `gh project` selbst hat dafür keinen eigenen Unterbefehl. Das läuft wie Schritt 3 bei jedem Aufruf erneut, ist also genauso sicher wiederholbar.
   - Fehlt der Scope, wird dieser Schritt übersprungen (Meldung inkl. Nachrüst-Kommando), Repo und Collaborator-Zugriff aus den Schritten 2–3 sind davon nicht betroffen.
5. Nur wenn `--clone-dir` angegeben ist: wie im Schüler-Modus.

## README.md-Inhalt — Schüler-Modus

Exakt dieses Template (Achtung: nach `**Name:**`- und `**Klasse:**`-Zeile stehen zwei Leerzeichen für einen harten Markdown-Zeilenumbruch — das ist im Skript bereits korrekt umgesetzt, beim manuellen Nachbauen nicht vergessen):

```
# <Repo-Slug aus der URL>

**Name:** <Vor- und Zuname>
**Klasse:** <Klasse>
**Schuljahr:** <Schuljahr>

Klonen des Repos

\`\`\`
git clone <URL des Repos>
\`\`\`
```

## README.md-Inhalt — Projekt-Modus

```
# <Titel oder Repo-Slug>

**Klasse:** <Klasse>
**Schuljahr:** <Schuljahr>

**Teammitglieder:**
- <Name 1> (GitHub: <user1>)
- <Name 2> (GitHub: <user2>)
...

Klonen des Repos

\`\`\`
git clone <URL des Repos>
\`\`\`
```

Nur wenn mindestens ein Mitglied ein Thema hat, kommt zusätzlich diese Tabelle dazu (Reihenfolge wie die Mitglieder, Personen ohne Thema werden ausgelassen):

```
## Individuelle Themenstellungen

| **Schüler/in** | **Individuelle Themenstellung** |
|----|----|
| <Name> | <Thema> |
...
```

## Verwendung

Einzelner Schüler:

```bash
python "scripts/create_repo.py" \
  --klasse 5caif \
  --name "Michael Schletz" \
  --schuljahr "2026/27" \
  --repo-url "https://github.com/Die-Spengergasse/sj26-27-5caif-pos-kur210534" \
  --github-user schletz
```

Ganze Klasse aus einer Datei, inklusive lokalem Klonen:

```bash
python "scripts/create_repo.py" --data-file klasse-5caif.csv --clone-dir "."
```

Projekt-/Diplomarbeit-Repo mit mehreren Mitgliedern und individuellen Themen, alle mit Admin-Zugriff:

```bash
python "scripts/create_repo.py" --projekt \
  --klasse 5caif \
  --schuljahr "2026/27" \
  --repo-url "https://github.com/Die-Spengergasse/sj26-27-5caif-da-gutachtenmanager" \
  --mitglied "Benjamin Wilk:King-ElWebo:Grundsystem und Fachmodul für Schadenakten." \
  --mitglied "Sebastian Kurta:bast-bit:Fachmodul zur Gutachtenerstellung." \
  --mitglied "Robert Krajinovic:Sajberluk:Fachmodul für Preisstände und Kalkulation." \
  --mitglied "Ivaylo Turitsov:TUR210548:Fachmodul für Raumerfassung."
```

Mehrere Projektteams aus einer Datei (Zeilen mit gleicher `repo_url` bilden ein Team):

```bash
python "scripts/create_repo.py" --projekt --data-file projekte-5caif.csv --clone-dir "."
```

Rufe das Skript mit dem absoluten Pfad zu diesem Skill-Verzeichnis auf, nicht mit einem relativen Pfad, falls das aktuelle Arbeitsverzeichnis nicht der Skill-Ordner ist.

**Frag proaktiv nach, ob geklont werden soll**, wenn der User nicht von sich aus "klonen" erwähnt — es ist eine sinnvolle Zusatzoption nach dem Anlegen, aber kein impliziter Standard. Der Zielordner liegt am besten im aktuellen Arbeitsverzeichnis des Users, nicht irgendwo fix Vorgegebenem.

## Bekannte Nebeneffekte, die vorher klar sein sollten

- Legt ein **privates** GitHub-Repo in einer echten Organisation an und vergibt Schreib- bzw. Admin-Rechte — das sind Aktionen mit echten, für andere sichtbaren Folgen. Bei Unsicherheit über einen Eintrag (z. B. ungewöhnlicher Klassenname, Repo-URL zeigt auf eine andere Org) lieber vorher beim User nachfragen statt zu raten.
- Der GitHub-Existenz-Check unterscheidet bewusst zwischen „existiert nicht" (GraphQL „Could not resolve to a Repository") und jedem anderen Fehler (z. B. Auth-Problem, Netzwerkfehler) — Letzteres bricht den Eintrag mit Fehlermeldung ab, statt fälschlich ein Repo anzulegen, das eigentlich schon da ist.
- Im Projekt-Modus bekommen **alle** angegebenen Mitglieder **Admin**-Rechte, nicht nur Write — sowohl auf dem Repo als auch auf dem GitHub-Project-Board. Das erlaubt ihnen auch, Branch-Protection-Rules, Webhooks, Collaborator-Verwaltung etc. selbst zu ändern. Das ist beabsichtigt (Teams sollen ihr Projekt-Repo und -Board selbst verwalten können), aber bei Unsicherheit vorher beim User bestätigen lassen. Diese Admin-Rechte sind immer auf das eine Repo bzw. das eine Board beschränkt — siehe [Sicherheitshinweis](#sicherheitshinweis-niemals-org-weite-rechte-vergeben): niemals Org-Mitgliedschaft oder Org-weite Rechte daraus ableiten.
- Die Idempotenz-Prüfung für das GitHub-Project-Board läuft **nur** über einen exakten Titel-Abgleich unter den mit dem Repo verlinkten Projects — anders als beim Repo-Namen gibt es dafür keine eindeutige Kennung. Wird derselbe Aufruf später mit einem **anderen** `--titel` (oder ganz ohne, sodass der Repo-Name als Titel einspringt) wiederholt, legt das Skript ein **zweites** Board an, statt das bestehende zu erkennen. Bei einem erneuten Aufruf für dasselbe Projekt immer denselben Titel verwenden wie beim ersten Mal.
