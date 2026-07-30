#!/usr/bin/env python3
"""Create private repositories in the Die-Spengergasse GitHub organization.

Supports two modes:

Student mode (default) — one repo per student:
  1. Checks (authenticated, so private repos are detected correctly) whether the
     target repo already exists. If it does, nothing is created or assigned.
  2. Checks whether the given GitHub user exists. If not, the entry is aborted
     before anything is created.
  3. Creates a private repo, pushes a `main` branch with a README.md, and grants
     the user write access.
  4. Optionally (--clone-dir) clones the repo locally to <clone-dir>/<klasse>/<repo>,
     or fast-forward-pulls it if it was already cloned there.

Project mode (--projekt) — one shared repo for several students (team projects,
Diplomarbeiten):
  1. Creates the repo and pushes a README listing all team members (and, if given,
     each member's individual Themenstellung) — but only the first time; an
     existing repo's README is never touched again, since the team may already be
     working in it.
  2. Grants every listed member admin access (not just write), so the team can
     manage branch protection rules etc. themselves. Unlike student mode, this
     step always runs, even if the repo already existed — so re-running the
     command later to add a member (or fix a typo'd username) works as expected.
  3. Each member is handled independently: an invalid GitHub username aborts only
     that member, not the whole project.
  4. If the gh token has the `project` OAuth scope, also creates (or reuses, if
     one with the same title is already linked to this repo) a GitHub Project
     (v2) board and grants every valid member ADMIN access on it. If the scope
     is missing, this step is skipped with a warning instead of failing the
     whole run — the caller is expected to have already asked the user to run
     `gh auth refresh -h github.com -s project` themselves beforehand.

The repo reference (`repo_url` field / `--repo-url`) accepts a full GitHub URL,
an "<owner>/<repo>" shorthand, or a bare repo name — a bare name assumes
DEFAULT_ORG as the owner.

Uses the `gh` CLI, which must already be authenticated with read/write access to
the organization (`gh auth status`).
"""
import argparse
import csv
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

# Assumed organization when a repo reference doesn't specify one (bare repo name).
DEFAULT_ORG = "Die-Spengergasse"

# Built from explicit "  \n" pieces (not a triple-quoted block) so the two
# trailing spaces that force a Markdown hard line break after Name/Klasse
# cannot be silently stripped by an editor or formatter.
README_TEMPLATE = (
    "# {repo_name}\n"
    "\n"
    "**Name:** {name}  \n"
    "**Klasse:** {klasse}  \n"
    "**Schuljahr:** {schuljahr}\n"
    "\n"
    "Klonen des Repos\n"
    "\n"
    "```\n"
    "git clone {repo_url}\n"
    "```\n"
)


@dataclass
class StudentEntry:
    klasse: str
    name: str
    schuljahr: str
    repo_url: str
    github_user: str


@dataclass
class ProjectMember:
    name: str
    github_user: str
    thema: str = ""  # individuelle Themenstellung; leer = kein Eintrag in der Tabelle


@dataclass
class ProjectEntry:
    klasse: str
    schuljahr: str
    repo_url: str
    members: list = field(default_factory=list)  # list[ProjectMember]
    titel: str = ""  # optionaler Projekt-/Diplomarbeitstitel für die README-Überschrift


def run_gh(args):
    """Run a gh CLI command and return the CompletedProcess without raising."""
    return subprocess.run(["gh", *args], capture_output=True, text=True)


def resolve_owner_repo(repo_ref):
    """
    Resolve a repo reference to (owner, repo).

    Accepts three forms, so the caller can be as terse as convenient:
      - a full GitHub URL, e.g. "https://github.com/Die-Spengergasse/sj26-27-5caif-wmc-hei240978"
      - an "<owner>/<repo>" shorthand, e.g. "Die-Spengergasse/sj26-27-5caif-wmc-hei240978"
      - a bare repo name, e.g. "sj26-27-5caif-wmc-hei240978", in which case
        DEFAULT_ORG is assumed as the owner.
    """
    ref = repo_ref.strip()
    path = urlparse(ref).path if "://" in ref else ref
    path = path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = [p for p in path.split("/") if p]
    if len(parts) == 2:
        return parts[0], parts[1]
    if len(parts) == 1:
        return DEFAULT_ORG, parts[0]
    raise ValueError(f"cannot parse owner/repo from: {repo_ref}")


def canonical_repo_url(owner, repo):
    """Build the https clone URL, used for the README regardless of how the repo was referenced."""
    return f"https://github.com/{owner}/{repo}"


def repo_exists(owner, repo):
    """
    Check whether the repo exists, using an authenticated `gh repo view` call.

    A plain unauthenticated HTTP check would return 404 both for "repo does not
    exist" and for "repo exists but is private", so it cannot tell them apart.
    `gh repo view` uses the authenticated gh session and correctly reports
    private repos the account can see as existing.
    """
    result = run_gh(["repo", "view", f"{owner}/{repo}", "--json", "name"])
    if result.returncode == 0:
        return True
    if "Could not resolve to a Repository" in result.stderr:
        return False
    raise RuntimeError(f"gh repo view failed unexpectedly: {result.stderr.strip()}")


def get_user(username):
    """
    Look up a GitHub user via the REST API.

    Returns the parsed JSON (which includes 'node_id', the GraphQL node ID
    reused for the Projects v2 collaborator mutation) if the account exists,
    or None if it doesn't.
    """
    result = run_gh(["api", f"users/{username}"])
    if result.returncode == 0:
        return json.loads(result.stdout)
    if "HTTP 404" in result.stderr or "'status': '404'" in result.stderr:
        return None
    raise RuntimeError(f"gh api users/{username} failed unexpectedly: {result.stderr.strip()}")


def user_exists(username):
    return get_user(username) is not None


def has_gh_scope(scope):
    """
    Check whether the currently authenticated gh session's token includes the
    given OAuth scope (e.g. "project", required for GitHub Projects v2 —
    `gh project create`/`link` and the GraphQL collaborators mutation).

    Assumes gh is already logged in (a precondition of this whole script); a
    completely failed `gh auth status` call is treated as an unexpected error,
    not as "scope missing".
    """
    result = run_gh(["auth", "status"])
    if result.returncode != 0:
        raise RuntimeError(f"gh auth status failed: {result.stderr.strip()}")
    output = result.stdout + result.stderr  # gh auth status writes its report to stderr
    return f"'{scope}'" in output


def create_repo(owner, repo):
    result = run_gh(["repo", "create", f"{owner}/{repo}", "--private"])
    if result.returncode != 0:
        raise RuntimeError(f"gh repo create failed: {result.stderr.strip()}")


def push_readme(owner, repo, readme_content):
    """Init a throwaway local git repo, commit README.md, and push it as `main`.

    Uses gh's own credential helper scoped to this git invocation only
    (`credential.helper=!gh auth git-credential`), so it authenticates over
    HTTPS without touching the user's global git configuration.
    """
    gh_login_result = run_gh(["api", "user", "-q", ".login"])
    gh_login = gh_login_result.stdout.strip() or "unknown"
    commit_author_email = f"{gh_login}@users.noreply.github.com"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        # newline="\n" keeps the template's trailing two-space hard line breaks intact
        (tmp_path / "README.md").write_text(readme_content, encoding="utf-8", newline="\n")

        def git(*args):
            cmd = [
                "git", "-C", str(tmp_path),
                "-c", f"user.name={gh_login}",
                "-c", f"user.email={commit_author_email}",
                "-c", "credential.helper=",
                "-c", "credential.helper=!gh auth git-credential",
                *args,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
            return result

        git("init", "-b", "main")
        git("add", "README.md")
        git("commit", "-m", "Initial commit: add README")
        git("remote", "add", "origin", f"https://github.com/{owner}/{repo}.git")
        git("push", "-u", "origin", "main")


def add_collaborator(owner, repo, username, permission="push"):
    """Grant access at the given level ("push" = write, "admin" = admin).

    If the user is not already an organization member, GitHub creates a
    pending invitation instead of adding them immediately; they then need to
    accept it before access becomes active.
    """
    result = run_gh([
        "api", f"repos/{owner}/{repo}/collaborators/{username}",
        "--method", "PUT", "-f", f"permission={permission}",
    ])
    if result.returncode != 0:
        raise RuntimeError(f"gh api collaborators failed: {result.stderr.strip()}")


def find_linked_project(owner, repo, title):
    """
    Return (project_id, project_number) of a GitHub Project (v2) already
    linked to this repo with the given title, or None if none matches.

    Projects aren't unique by title the way repos are unique by name, so this
    lookup is what makes re-running the project-board step idempotent instead
    of creating a duplicate board on every re-run (e.g. to add a member later).
    """
    query = (
        "query($owner: String!, $repo: String!) {"
        " repository(owner: $owner, name: $repo) {"
        "   projectsV2(first: 50) { nodes { id number title } }"
        " } }"
    )
    result = run_gh([
        "api", "graphql",
        "-f", f"query={query}", "-f", f"owner={owner}", "-f", f"repo={repo}",
    ])
    if result.returncode != 0:
        raise RuntimeError(f"gh api graphql (projectsV2 lookup) failed: {result.stderr.strip()}")
    nodes = json.loads(result.stdout)["data"]["repository"]["projectsV2"]["nodes"]
    for node in nodes:
        if node["title"] == title:
            return node["id"], node["number"]
    return None


def create_and_link_project(owner, repo, title):
    """Create an org-owned GitHub Project (v2), link it to the repo, and return its node id."""
    result = run_gh(["project", "create", "--owner", owner, "--title", title, "--format", "json"])
    if result.returncode != 0:
        raise RuntimeError(f"gh project create failed: {result.stderr.strip()}")
    project = json.loads(result.stdout)

    result = run_gh([
        "project", "link", str(project["number"]),
        "--owner", owner, "--repo", f"{owner}/{repo}",
    ])
    if result.returncode != 0:
        raise RuntimeError(f"gh project link failed: {result.stderr.strip()}")

    return project["id"]


def set_project_collaborators_admin(project_id, member_node_ids):
    """
    Grant ADMIN role on the project board to every given user (by GraphQL node
    ID, e.g. a user's REST 'node_id') — `gh project` has no dedicated
    collaborator subcommand for this, so it goes through the GraphQL API
    directly via the updateProjectV2Collaborators mutation.
    """
    if not member_node_ids:
        return
    mutation = (
        "mutation($projectId: ID!, $collaborators: [ProjectV2Collaborator!]!) {"
        " updateProjectV2Collaborators(input: {projectId: $projectId, collaborators: $collaborators}) {"
        "   clientMutationId"
        " } }"
    )
    payload = {
        "query": mutation,
        "variables": {
            "projectId": project_id,
            "collaborators": [{"userId": nid, "role": "ADMIN"} for nid in member_node_ids],
        },
    }
    # gh api graphql can't take a nested array of objects through -f/-F, so the
    # request body is passed as a JSON file via --input instead.
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(payload, f)
        payload_path = f.name
    try:
        result = run_gh(["api", "graphql", "--input", payload_path])
    finally:
        Path(payload_path).unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(f"gh api graphql (updateProjectV2Collaborators) failed: {result.stderr.strip()}")


def clone_repo(owner, repo, dest: Path):
    """
    Clone the repo to `dest`, or update it with a fast-forward pull if it was
    already cloned there before (so re-running with --clone-dir stays safe).

    Uses `gh repo clone`, which reuses gh's own authentication, so private
    repos work without any extra git credential setup.
    """
    if dest.exists():
        result = subprocess.run(["git", "-C", str(dest), "pull", "--ff-only"], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"git pull in {dest} failed: {result.stderr.strip()}")
        print(f"Updated existing local clone: {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = run_gh(["repo", "clone", f"{owner}/{repo}", str(dest)])
    if result.returncode != 0:
        raise RuntimeError(f"gh repo clone failed: {result.stderr.strip()}")
    print(f"Cloned to {dest}")


def process_entry(entry: StudentEntry, clone_dir: Path = None):
    owner, repo = resolve_owner_repo(entry.repo_url)
    repo_url = canonical_repo_url(owner, repo)
    print(f"\n=== {entry.name} ({entry.github_user}) -> {owner}/{repo} ===")

    if repo_exists(owner, repo):
        print(f"SKIP: repository {owner}/{repo} already exists. Nothing created or assigned.")
        if clone_dir:
            clone_repo(owner, repo, clone_dir / entry.klasse / repo)
        return

    if not entry.github_user or not entry.github_user.strip():
        # An empty username would otherwise slip through to `gh api users/`,
        # which is a different (list-users) endpoint that returns 200 OK.
        print("ABORT: no GitHub user given. Nothing created.")
        return

    if not user_exists(entry.github_user):
        print(f"ABORT: GitHub user '{entry.github_user}' does not exist. Nothing created.")
        return

    print(f"Creating private repository {owner}/{repo}...")
    create_repo(owner, repo)

    readme = README_TEMPLATE.format(
        repo_name=repo,
        name=entry.name,
        klasse=entry.klasse,
        schuljahr=entry.schuljahr,
        repo_url=repo_url,
    )
    print("Pushing main branch with README.md...")
    push_readme(owner, repo, readme)

    print(f"Granting write access to '{entry.github_user}'...")
    add_collaborator(owner, repo, entry.github_user, permission="push")

    print(f"DONE: {owner}/{repo} created and '{entry.github_user}' added with write access.")

    if clone_dir:
        clone_repo(owner, repo, clone_dir / entry.klasse / repo)


def build_project_readme(repo_name, repo_url, entry: ProjectEntry):
    heading = entry.titel.strip() or repo_name
    lines = [
        f"# {heading}",
        "",
        f"**Klasse:** {entry.klasse}  ",
        f"**Schuljahr:** {entry.schuljahr}",
        "",
        "**Teammitglieder:**",
    ]
    for m in entry.members:
        lines.append(f"- {m.name} (GitHub: {m.github_user})")
    lines += [
        "",
        "Klonen des Repos",
        "",
        "```",
        f"git clone {repo_url}",
        "```",
    ]

    themed = [m for m in entry.members if m.thema.strip()]
    if themed:
        lines += [
            "",
            "## Individuelle Themenstellungen",
            "",
            "| **Schüler/in** | **Individuelle Themenstellung** |",
            "|----|----|",
        ]
        for m in themed:
            lines.append(f"| {m.name} | {m.thema.strip()} |")

    return "\n".join(lines) + "\n"


def project_board_title(repo_name, entry: ProjectEntry):
    return entry.titel.strip() or repo_name


def process_project_entry(entry: ProjectEntry, clone_dir: Path = None, project_scope_ok: bool = True):
    """
    Same repo, shared by several students, everyone gets admin access — on the
    repository and, if the gh token has the `project` scope, on a linked
    GitHub Project (v2) board as well.

    Unlike process_entry (student mode), an already-existing repo does NOT
    short-circuit the whole entry: the README is left untouched (the team may
    already be working in it), but collaborators are still (re-)granted admin
    access below, on both the repo and the project board. That makes it safe
    to re-run this for a project repo later, e.g. to add a member or fix a
    mistyped username, without needing a separate code path.
    """
    owner, repo = resolve_owner_repo(entry.repo_url)
    repo_url = canonical_repo_url(owner, repo)
    member_list = ", ".join(f"{m.name} ({m.github_user})" for m in entry.members)
    print(f"\n=== Projekt {owner}/{repo}: {member_list} ===")

    if repo_exists(owner, repo):
        print(f"INFO: repository {owner}/{repo} already exists. README left untouched.")
    else:
        print(f"Creating private repository {owner}/{repo}...")
        create_repo(owner, repo)

        readme = build_project_readme(repo, repo_url, entry)
        print("Pushing main branch with README.md...")
        push_readme(owner, repo, readme)

    had_member_error = False
    member_node_ids = []
    for m in entry.members:
        if not m.github_user or not m.github_user.strip():
            print(f"ABORT for member '{m.name}': no GitHub user given.")
            had_member_error = True
            continue
        user = get_user(m.github_user)
        if user is None:
            print(f"ABORT for member '{m.name}': GitHub user '{m.github_user}' does not exist.")
            had_member_error = True
            continue
        print(f"Granting admin access to '{m.github_user}' ({m.name})...")
        add_collaborator(owner, repo, m.github_user, permission="admin")
        member_node_ids.append(user["node_id"])

    if project_scope_ok:
        title = project_board_title(repo, entry)
        existing = find_linked_project(owner, repo, title)
        if existing:
            project_id, project_number = existing
            print(f"INFO: GitHub Project '{title}' (#{project_number}) already linked to {owner}/{repo}, reusing it.")
        else:
            print(f"Creating GitHub Project '{title}' and linking it to {owner}/{repo}...")
            project_id = create_and_link_project(owner, repo, title)
        print(f"Granting admin access on the project board to {len(member_node_ids)} member(s)...")
        set_project_collaborators_admin(project_id, member_node_ids)
    else:
        print(
            "SKIP: no GitHub Project (v2) board created or updated — the gh token is missing "
            "the 'project' scope. Run 'gh auth refresh -h github.com -s project' and re-run "
            "this command to add the board."
        )

    if had_member_error:
        raise RuntimeError(f"{owner}/{repo}: one or more members could not be granted access (see log above).")

    print(f"DONE: {owner}/{repo} — all members granted admin access.")

    if clone_dir:
        clone_repo(owner, repo, clone_dir / entry.klasse / repo)


def load_entries_from_file(path: Path):
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data if isinstance(data, list) else [data]
    else:
        with path.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
    return [
        StudentEntry(
            klasse=row["klasse"],
            name=row["name"],
            schuljahr=row["schuljahr"],
            repo_url=row["repo_url"],
            github_user=row["github_user"],
        )
        for row in rows
    ]


def load_project_entries_from_file(path: Path):
    """
    Same file shape as student mode (one row per person: klasse, schuljahr,
    repo_url, name, github_user) plus an optional 'thema' and/or 'titel'
    column, but rows sharing the same repo_url are grouped into a single
    ProjectEntry with multiple members — that's the whole difference between
    "one repo per student" and "one shared repo per team".
    """
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data if isinstance(data, list) else [data]
    else:
        with path.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))

    projects = {}  # (owner, repo) -> ProjectEntry, insertion-ordered
    for row in rows:
        owner, repo = resolve_owner_repo(row["repo_url"])
        key = (owner, repo)
        if key not in projects:
            projects[key] = ProjectEntry(
                klasse=row["klasse"],
                schuljahr=row["schuljahr"],
                repo_url=row["repo_url"],
                titel=(row.get("titel") or "").strip(),
            )
        entry = projects[key]
        if not entry.titel and (row.get("titel") or "").strip():
            entry.titel = row["titel"].strip()
        entry.members.append(ProjectMember(
            name=row["name"],
            github_user=row["github_user"],
            thema=(row.get("thema") or "").strip(),
        ))
    return list(projects.values())


def parse_member_arg(raw):
    """Parse a --mitglied value: "Name:github_user" or "Name:github_user:Thema"."""
    parts = raw.split(":", 2)
    if len(parts) == 2:
        name, user = parts
        return ProjectMember(name=name.strip(), github_user=user.strip())
    if len(parts) == 3:
        name, user, thema = parts
        return ProjectMember(name=name.strip(), github_user=user.strip(), thema=thema.strip())
    raise ValueError(f"cannot parse --mitglied value (expected 'Name:github_user[:Thema]'): {raw}")


def main():
    parser = argparse.ArgumentParser(
        description="Create Spengergasse student/project repos and grant access."
    )
    parser.add_argument(
        "--data-file", type=Path,
        help="CSV or JSON file, one row per person: klasse,name,schuljahr,repo_url,github_user "
             "(student mode), plus optional thema/titel columns (project mode; rows sharing "
             "repo_url become one project)",
    )
    parser.add_argument("--klasse")
    parser.add_argument("--name", help="student mode: Vor- und Zuname")
    parser.add_argument("--schuljahr")
    parser.add_argument(
        "--repo-url",
        help=f"full GitHub URL, '<owner>/<repo>', or a bare repo name (assumes org '{DEFAULT_ORG}')",
    )
    parser.add_argument("--github-user", help="student mode: GitHub account name")
    parser.add_argument(
        "--clone-dir", type=Path,
        help="if given, also clone (or fast-forward update) each repo locally under <clone-dir>/<klasse>/<repo>",
    )
    parser.add_argument(
        "--projekt", action="store_true",
        help="project mode: one shared repo for several students, all with admin access "
             "(team projects, Diplomarbeiten), instead of one repo per student with write access",
    )
    parser.add_argument(
        "--titel",
        help="project mode only: optional Projekt-/Diplomarbeitstitel for the README heading "
             "(defaults to the repo name, like student mode)",
    )
    parser.add_argument(
        "--mitglied", action="append", dest="mitglieder", default=[],
        metavar="Name:github_user[:Thema]",
        help="project mode only: one team member, repeatable, e.g. "
             "--mitglied \"Robert Krajinovic:Sajberluk\" or "
             "--mitglied \"Robert Krajinovic:Sajberluk:Fachmodul XY\"",
    )
    args = parser.parse_args()

    if args.projekt:
        if args.data_file:
            entries = load_project_entries_from_file(args.data_file)
        else:
            required = [args.klasse, args.schuljahr, args.repo_url]
            if not all(required) or not args.mitglieder:
                parser.error(
                    "--projekt requires either --data-file, or --klasse --schuljahr --repo-url "
                    "plus at least one --mitglied"
                )
            entries = [ProjectEntry(
                klasse=args.klasse,
                schuljahr=args.schuljahr,
                repo_url=args.repo_url,
                members=[parse_member_arg(m) for m in args.mitglieder],
                titel=args.titel or "",
            )]

        project_scope_ok = has_gh_scope("project")
        if not project_scope_ok:
            print(
                "WARNING: gh token has no 'project' scope — GitHub Project (v2) boards will "
                "be skipped for every entry below (repos and collaborator access are not "
                "affected). Run 'gh auth refresh -h github.com -s project' and re-run this "
                "command to add the boards.",
                file=sys.stderr,
            )

        had_error = False
        for entry in entries:
            try:
                process_project_entry(entry, args.clone_dir, project_scope_ok)
            except Exception as exc:
                had_error = True
                print(f"ERROR processing {entry.repo_url}: {exc}", file=sys.stderr)
        sys.exit(1 if had_error else 0)

    if args.data_file:
        entries = load_entries_from_file(args.data_file)
    else:
        required = [args.klasse, args.name, args.schuljahr, args.repo_url, args.github_user]
        if not all(required):
            parser.error(
                "either --data-file or all of --klasse --name --schuljahr --repo-url --github-user are required"
            )
        entries = [StudentEntry(args.klasse, args.name, args.schuljahr, args.repo_url, args.github_user)]

    had_error = False
    for entry in entries:
        try:
            process_entry(entry, args.clone_dir)
        except Exception as exc:
            had_error = True
            print(f"ERROR processing {entry.name}: {exc}", file=sys.stderr)

    sys.exit(1 if had_error else 0)


if __name__ == "__main__":
    main()
