---
name: create-spengergasse-repo
description: Legt in der GitHub-Organisation Die-Spengergasse ein privates Schüler-Repo an, pusht einen main Branch mit README.md, gibt einem GitHub-Account Write-Zugriff darauf und kann das Repo optional gleich lokal klonen. Nutze diesen Skill immer, wenn der User ein neues Schüler-/Klassen-Repo für die Spengergasse anlegen will, einen Schüler-Account einem Repo zuweisen will, oder Formulierungen wie "Repo anlegen", "Schüler-Repo", "GitHub-Zugriff geben/zuweisen" im Kontext der Organisation die-spengergasse/Die-Spengergasse fallen — auch wenn nur einzelne Angaben (Klasse, Name, Repo-URL, Account) genannt werden. Unterstützt auch Batch-Anlage für eine ganze Klasse über eine CSV/JSON-Datei.
---

# Spengergasse Schüler-Repo anlegen

Legt private Schüler-Repos in der Organisation `Die-Spengergasse` an (Org-Slug ist case-insensitive, in URLs taucht sowohl `die-spengergasse` als auch `Die-Spengergasse` auf) und weist einen bestehenden GitHub-Account mit Write-Rechten zu. Die eigentliche Logik steckt in [`scripts/create_repo.py`](scripts/create_repo.py) — ruf das Skript aus, statt die Schritte einzeln nachzubauen.

## Warum die feste Prüfreihenfolge wichtig ist

Ein einfacher unauthentifizierter HTTP-404-Check kann ein privates Repo nicht von einem nicht existierenden Repo unterscheiden — beide liefern 404. Deshalb prüft das Skript über die authentifizierte `gh`-Session (`gh repo view`), die private Repos korrekt als existent erkennt. Existiert das Repo bereits, wird **nichts** angelegt oder zugewiesen — das Skript meldet das nur und beendet den jeweiligen Eintrag sauber. Das macht wiederholte Aufrufe (z. B. für dieselbe Klasse in einem späteren Semester nochmal ausgeführt) ungefährlich statt fehlerhaft.

## Voraussetzungen

- `gh` CLI ist installiert und bei einem Account eingeloggt, der Lese-/Schreibrechte auf die Organisation hat (prüfbar mit `gh auth status`).
- `git` ist installiert.
- Python 3 ist installiert (das Skript nutzt nur die Standardbibliothek).

## Eingaben

Entweder als Einzelwerte, oder gesammelt für eine ganze Klasse über eine Datei.

**Einzeln:**
- `--klasse` (z. B. `5CAIF`)
- `--name` (Vor- und Zuname, z. B. `Michael Schletz`)
- `--schuljahr` (z. B. `2026/27`)
- `--repo-url` — volle GitHub-URL (`https://github.com/Die-Spengergasse/sj26-27-5caif-wmc-schletz`), `<owner>/<repo>` (`Die-Spengergasse/sj26-27-5caif-wmc-schletz`), oder ein bloßer Reponame (`sj26-27-5caif-wmc-schletz`) — dann wird automatisch die Org `Die-Spengergasse` angenommen. Egal welche Form übergeben wird, im README landet immer die volle kanonische URL.
- `--github-user` (GitHub-Accountname, z. B. `schletz`)
- `--clone-dir` (optional) — Basisordner, in den das Repo zusätzlich lokal geklont (bzw. bei erneutem Aufruf aktualisiert) wird, als `<clone-dir>/<klasse>/<repo>`

**Batch über `--data-file`:** CSV oder JSON mit einer Zeile/einem Objekt pro Schüler und den Spalten/Keys `klasse,name,schuljahr,repo_url,github_user`. Jeder Eintrag wird unabhängig verarbeitet — ein Fehler bei einem Schüler (z. B. unbekannter Account) bricht nicht den ganzen Lauf ab, sondern nur diesen einen Eintrag.

## Ablauf pro Eintrag (macht das Skript automatisch)

1. Org und Repo-Name aus der Repo-Angabe extrahieren (volle URL, `<owner>/<repo>`, oder bloßer Reponame → Org `Die-Spengergasse` wird angenommen).
2. Prüfen, ob das Repo existiert (`gh repo view`, authentifiziert → erkennt auch private Repos korrekt). Existiert es: Meldung „already exists, nothing created" und weiter zum nächsten Eintrag — **kein** Create, **kein** Collaborator-Zuweisen.
3. Prüfen, ob der GitHub-Account existiert (`gh api users/<user>`). Existiert er nicht: Abbruch für diesen Eintrag, nichts wird angelegt.
4. Privates Repo anlegen: `gh repo create <owner>/<repo> --private`.
5. `main` Branch mit README.md pushen. Dafür wird lokal ein Wegwerf-Git-Repo initialisiert und über `gh`s eigenen Credential-Helper (scoped auf diesen einen Aufruf, ohne die globale Git-Config zu verändern) gepusht.
6. GitHub-User mit Write-Zugriff hinzufügen: `gh api repos/<owner>/<repo>/collaborators/<user> --method PUT -f permission=push`. Ist der Account nicht bereits Org-Mitglied, erzeugt GitHub daraus eine offene Einladung, die der Schüler noch annehmen muss — das ist normales GitHub-Verhalten, nicht steuerbar.
7. Nur wenn `--clone-dir` angegeben ist: Repo lokal nach `<clone-dir>/<klasse>/<repo>` klonen (`gh repo clone`, nutzt automatisch die gh-Session, auch für private Repos). Das passiert unabhängig davon, ob das Repo gerade neu angelegt wurde oder schon existierte — läuft also auch beim erneuten Aufruf für bereits vorhandene Repos. Existiert der Zielordner schon, wird stattdessen nur ein `git pull --ff-only` gemacht statt neu zu klonen.

## README.md-Inhalt

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

## Verwendung

Einzelner Schüler:

```bash
python "scripts/create_repo.py" \
  --klasse 5CAIF \
  --name "Michael Schletz" \
  --schuljahr "2026/27" \
  --repo-url "https://github.com/Die-Spengergasse/sj26-27-5caif-wmc-schletz" \
  --github-user schletz
```

Ganze Klasse aus einer Datei, inklusive lokalem Klonen:

```bash
python "scripts/create_repo.py" --data-file klasse-5caif.csv --clone-dir "."
```

Rufe das Skript mit dem absoluten Pfad zu diesem Skill-Verzeichnis auf, nicht mit einem relativen Pfad, falls das aktuelle Arbeitsverzeichnis nicht der Skill-Ordner ist.

**Frag proaktiv nach, ob geklont werden soll**, wenn der User nicht von sich aus "klonen" erwähnt — es ist eine sinnvolle Zusatzoption nach dem Anlegen, aber kein impliziter Standard. Der Zielordner liegt am besten im aktuellen Arbeitsverzeichnis des Users, nicht irgendwo fix Vorgegebenem.

## Bekannte Nebeneffekte, die vorher klar sein sollten

- Legt ein **privates** GitHub-Repo in einer echten Organisation an und vergibt Schreibrechte — das sind Aktionen mit echten, für andere sichtbaren Folgen. Bei Unsicherheit über einen Eintrag (z. B. ungewöhnlicher Klassenname, Repo-URL zeigt auf eine andere Org) lieber vorher beim User nachfragen statt zu raten.
- Der GitHub-Existenz-Check unterscheidet bewusst zwischen „existiert nicht" (GraphQL „Could not resolve to a Repository") und jedem anderen Fehler (z. B. Auth-Problem, Netzwerkfehler) — Letzteres bricht den Eintrag mit Fehlermeldung ab, statt fälschlich ein Repo anzulegen, das eigentlich schon da ist.
