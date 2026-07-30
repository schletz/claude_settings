"""Operations that change a bundle or restore its files. Each returns messages for the user."""

from __future__ import annotations

from pathlib import Path

from bundle_format import Bundle, root_of
from file_reader import read_file


def apply_meta(bundle: Bundle, meta: dict) -> list[str]:
    """Set abstracts and summaries from read_meta.py JSON; report gaps."""
    summaries: dict[str, str] = meta.get("summaries", {})
    abstracts: dict[str, str] = meta.get("abstracts", {})
    bundle.abstract_level = int(meta.get("abstract_level", bundle.abstract_level))
    bundle.abstracts.update(abstracts)
    for f in bundle.files:
        f.summary = summaries.get(f.path, f.summary)
    known = {f.path for f in bundle.files}
    directories = bundle.directory_levels()
    return [_listed("paths not in the bundle", [p for p in summaries if p not in known]),
            _listed("directories not in the bundle", [d for d in abstracts if d not in directories])] + _gaps(bundle)


def merge_base(bundle: Bundle, base: Bundle) -> list[str]:
    """Carry metadata of a previous bundle over to a freshly scanned one.

    Files are matched by path. Comparing the stored content tells which
    summaries may be outdated, so no hash is needed. Converted and binary
    entries cannot be extracted, so they are kept when SRC lacks them.
    """
    old = {f.path: f for f in base.files}
    scanned = {f.path for f in bundle.files}
    bundle.abstract_level = bundle.abstract_level or base.abstract_level
    bundle.abstracts = {**base.abstracts, **bundle.abstracts}
    changed, new = [], []
    for f in bundle.files:
        previous = old.get(f.path)
        if previous is None:
            new.append(f.path)
            continue
        f.summary = f.summary or previous.summary
        if (f.content, f.size) != (previous.content, previous.size):
            changed.append(f.path)
    kept = [f for f in base.files if f.path not in scanned and (f.converted or f.content is None)]
    bundle.files += kept
    removed = [p for p in old if p not in scanned and p not in {f.path for f in kept}]
    return [
        f"{len(bundle.files) - len(changed) - len(new) - len(kept)} unchanged",
        _listed("changed, check the summary", changed),
        _listed("new, write a summary", new),
        _listed("removed", removed),
        _listed("kept from the base bundle (converted or binary, not in SRC)", [f.path for f in kept]),
    ] + _gaps(bundle)


def add_file(bundle: Bundle, file: Path, path: str, summary: str | None) -> list[str]:
    """Add or replace a file. A replacement inherits what the new file cannot provide.

    An edited conversion is plain Markdown on disk, so it keeps the origin
    format (``converted="pdf"``) of the entry it replaces.
    """
    path = path.replace("\\", "/")
    if path.startswith("/") or ":" in path or ".." in path.split("/"):
        raise ValueError(f"{path} must be a relative path inside the bundle, e.g. Root/dir/File.cs")
    old = next((f for f in bundle.files if f.path == path), None)
    added = read_file(file, path)
    added.summary = summary if summary is not None else (old.summary if old else "")
    if old and old.converted and added.content is not None and not added.converted:
        added.converted = old.converted
    bundle.files = [f for f in bundle.files if f.path != path] + [added]
    return [_listed("directories without abstract, set them with update", bundle.missing_abstracts()),
            "" if added.summary else f"{path} has no summary, pass --summary"]


def remove_files(bundle: Bundle, paths: list[str]) -> list[str]:
    """Remove files by full path; raises KeyError naming unknown paths so nothing is removed silently."""
    unknown = [p for p in paths if p not in {f.path for f in bundle.files}]
    if unknown:
        raise KeyError(", ".join(unknown))
    bundle.files = [f for f in bundle.files if f.path not in paths]
    return []


def extract(bundle: Bundle, dest: Path, force: bool) -> list[str]:
    """Write all plain text files below ``dest``, keeping their bundle paths.

    Converted documents and binary files cannot be restored; they stay in the
    bundle and are kept by ``create --base`` when the bundle is rebuilt.
    """
    dest = dest.resolve()
    targets = {}
    for f in bundle.files:
        if f.content is None or f.converted:
            continue
        target = (dest / f.path).resolve()
        # A bundle from elsewhere could contain "../" paths; never write outside dest.
        if not target.is_relative_to(dest):
            raise ValueError(f"{f.path} points outside {dest}")
        targets[target] = f.content
    existing = [t for t in targets if t.exists()]
    if existing and not force:
        raise FileExistsError(f"{len(existing)} files already exist, e.g. {existing[0]}; use --force to overwrite")
    for target, content in targets.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content + "\n", encoding="utf-8", newline="\n")
    root = root_of(bundle.files)
    rebuild = f"{dest / root} BUNDLE --base BUNDLE" if root else f"{dest} BUNDLE --base BUNDLE --no-root"
    skipped = [f.path for f in bundle.files if f.content is None or f.converted]
    return [f"{len(targets)} files written to {dest}",
            _listed("not extracted (converted or binary)", skipped),
            f"rebuild: bundle.py create {rebuild}"]


def _gaps(bundle: Bundle) -> list[str]:
    missing = [f.path for f in bundle.files if not f.summary]
    return [_listed("files without summary", missing),
            _listed(f"directories down to level {bundle.abstract_level} without abstract", bundle.missing_abstracts())]


def _listed(label: str, paths: list[str]) -> str:
    return f"{len(paths)} {label}: " + ", ".join(paths) if paths else ""
