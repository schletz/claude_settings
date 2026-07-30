"""Print the table of contents of a bundle, whole or limited to a subtree and directory level.

Usage:
    read_toc.py BUNDLE --count-entries           # dirs and entries per level, and the size in chars
    read_toc.py BUNDLE                           # whole TOC with all entries (small bundles)
    read_toc.py BUNDLE --dir-level 1             # dirs down to level 1 with their abstracts, no entries
    read_toc.py BUNDLE "01 Types" --dir-level 3  # dirs of the subtree 01 Types down to level 3, no entries
    read_toc.py BUNDLE "01 Types"                # the whole subtree of 01 Types with all entries

BUNDLE is a local file or an http(s) URL. BASE_DIR is a directory path as the
TOC shows it, or its unique ending (``Uebungen/CarRentalService``). Levels are
absolute: level 0 is the bundle's top, whose abstract describes the project.
``--dir-level`` gives an overview of the tree, so it leaves out the file
entries; read the entries of the subtree you need with BASE_DIR.
``--count-entries`` counts the same selection, so check the size first.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

# python -I leaves the script's directory off sys.path; the sibling modules live there.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import bundle_io  # noqa: E402
from bundle_format import TocDirectory, read_toc, split_toc  # noqa: E402


def main() -> None:
    bundle_io.setup_console()
    args = _parse_args()
    head, dirs = split_toc(read_toc(bundle_io.load(args.bundle)))
    if not dirs:
        sys.exit("error: no TOC found, is this a bundle created by bundle.py?")
    if args.base_dir is not None:
        base = _resolve(dirs, args.base_dir)
        dirs = [d for d in dirs if d.path == base or d.path.startswith(base + "/")]
    if args.dir_level is not None:
        dirs = [d for d in dirs if d.level <= args.dir_level]

    text = "\n".join([*head, *(line for d in dirs for line in _lines(d, args.dir_level is None)), "</toc>"])
    if args.count_entries:
        print(_counts(dirs, text))
        return
    bundle_io.emit(text, args.out, args.max_chars,
                   "narrow it with --dir-level or a BASE_DIR (check sizes with --count-entries)")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("bundle", help="bundle file or http(s) URL")
    parser.add_argument("base_dir", nargs="?", help="print only this directory and its subtree")
    parser.add_argument("--dir-level", type=int,
                        help="print only directories down to this level (inclusive), without entries")
    parser.add_argument("--count-entries", action="store_true",
                        help="print dirs and entries per level of the selection instead of the TOC")
    parser.add_argument("--out", type=Path, help="always write to this file")
    parser.add_argument("--max-chars", type=int, default=25000)
    return parser.parse_args()


def _lines(d: TocDirectory, with_entries: bool) -> list[str]:
    return d.lines if with_entries else [line for line in d.lines if not line.startswith("<entry ")]


def _resolve(dirs: list[TocDirectory], base: str) -> str:
    """Full path of the directory named by ``base``: exact, or the only path ending with it."""
    base = base.replace("\\", "/").strip("/")
    if any(d.path == base for d in dirs):
        return base
    matches = [d.path for d in dirs if d.path.endswith("/" + base)]
    if len(matches) == 1:
        return matches[0]
    if matches:
        sys.exit(f"error: '{base}' is ambiguous: " + ", ".join(matches))
    sys.exit(f"error: no directory '{base}', see read_toc.py BUNDLE --dir-level 1 for valid paths")


def _counts(dirs: list[TocDirectory], text: str) -> str:
    """Dirs and entries per level, so a reader can tell what each --dir-level or subtree costs."""
    dir_count = Counter(d.level for d in dirs)
    entry_count = Counter()
    for d in dirs:
        entry_count[d.level] += d.entry_count
    rows = [f"{'Level':>5} {'Dirs':>6} {'Entries':>8}"]
    rows += [f"{level:>5} {dir_count[level]:>6} {entry_count[level]:>8}" for level in sorted(dir_count)]
    rows.append(f"{'Total':>5} {len(dirs):>6} {sum(entry_count.values()):>8}")
    return "\n".join(rows + [f"{len(text)} chars in this selection"])


if __name__ == "__main__":
    main()
