#!/usr/bin/env python3
"""Create private student repositories in the Die-Spengergasse GitHub organization.

For each student entry, this script:
  1. Checks (authenticated, so private repos are detected correctly) whether the
     target repo already exists. If it does, nothing is created or assigned.
  2. Checks whether the given GitHub user exists. If not, the entry is aborted
     before anything is created.
  3. Creates a private repo, pushes a `main` branch with a README.md, and grants
     the user write access.
  4. Optionally (--clone-dir) clones the repo locally to <clone-dir>/<klasse>/<repo>,
     or fast-forward-pulls it if it was already cloned there.

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
from dataclasses import dataclass
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


def user_exists(username):
    result = run_gh(["api", f"users/{username}"])
    if result.returncode == 0:
        return True
    if "HTTP 404" in result.stderr or "'status': '404'" in result.stderr:
        return False
    raise RuntimeError(f"gh api users/{username} failed unexpectedly: {result.stderr.strip()}")


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


def add_collaborator(owner, repo, username):
    """Grant write access. `permission=push` is the API's write-access level.

    If the user is not already an organization member, GitHub creates a
    pending invitation instead of adding them immediately; they then need to
    accept it before write access becomes active.
    """
    result = run_gh([
        "api", f"repos/{owner}/{repo}/collaborators/{username}",
        "--method", "PUT", "-f", "permission=push",
    ])
    if result.returncode != 0:
        raise RuntimeError(f"gh api collaborators failed: {result.stderr.strip()}")


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
    add_collaborator(owner, repo, entry.github_user)

    print(f"DONE: {owner}/{repo} created and '{entry.github_user}' added with write access.")

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


def main():
    parser = argparse.ArgumentParser(
        description="Create Spengergasse student repos and grant write access."
    )
    parser.add_argument(
        "--data-file", type=Path,
        help="CSV or JSON file with klasse,name,schuljahr,repo_url,github_user columns/keys, one row per student",
    )
    parser.add_argument("--klasse")
    parser.add_argument("--name")
    parser.add_argument("--schuljahr")
    parser.add_argument(
        "--repo-url",
        help=f"full GitHub URL, '<owner>/<repo>', or a bare repo name (assumes org '{DEFAULT_ORG}')",
    )
    parser.add_argument("--github-user")
    parser.add_argument(
        "--clone-dir", type=Path,
        help="if given, also clone (or fast-forward update) each repo locally under <clone-dir>/<klasse>/<repo>",
    )
    args = parser.parse_args()

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
