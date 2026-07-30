"""Write the editable metadata of a bundle or directory as JSON.

Usage:
    read_meta.py BUNDLE [META.json] [--abstract-level N]  # current abstracts and summaries
    read_meta.py SRC [META.json] [--abstract-level N] [--ext cs,md] [--exclude-dir Migrations]   # skeleton

The JSON holds only what a script cannot derive from the files:

    {"abstract_level": 1,
     "abstracts": {"Root": "The whole project.", "Root/src": "What the whole subtree contains."},
     "summaries": {"Root/src/File.cs": "One sentence."}}

``abstracts`` lists every directory down to ``abstract_level``, starting with
the top directory (level 0) whose abstract describes the whole project, plus
deeper ones that already have an abstract. ``--abstract-level`` overrides the
level stored in a bundle.

Edit it and apply it with ``bundle.py create SRC OUT --meta META.json`` or
``bundle.py update BUNDLE META.json``. Without META.json it prints to stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# python -I leaves the script's directory off sys.path; the sibling modules live there.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from bundle_format import directory_levels, parse  # noqa: E402
from file_list import add_filter_arguments, list_files  # noqa: E402


def main() -> None:
    # Umlauts must survive on consoles that default to cp1252 or cp850.
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="bundle file or source directory")
    parser.add_argument("meta", type=Path, nargs="?", help="output file (default: stdout)")
    parser.add_argument("--abstract-level", type=int,
                        help="list directories down to this level for abstracts (default: the bundle's level, 0)")
    add_filter_arguments(parser)
    args = parser.parse_args()

    if args.source.is_dir():
        root = args.source.resolve().name
        paths = [f"{root}/{p}" for p in list_files(args.source, args.ext, args.exclude_dir, skip=args.meta)]
        level, written, summaries = 0, {}, {p: "" for p in paths}
    else:
        bundle = parse(args.source.read_text(encoding="utf-8"))
        paths = [f.path for f in bundle.sorted_files()]
        level, written = bundle.abstract_level, bundle.abstracts
        summaries = {f.path: f.summary for f in bundle.sorted_files()}
    if args.abstract_level is not None:
        level = args.abstract_level

    abstracts = {d: written.get(d, "") for d, depth in directory_levels(paths).items()
                 if depth <= level or written.get(d)}
    meta = {"abstract_level": level, "abstracts": abstracts, "summaries": summaries}
    text = json.dumps(meta, indent=2, ensure_ascii=False) + "\n"
    if args.meta:
        args.meta.write_text(text, encoding="utf-8", newline="\n")
        print(f"{len(summaries)} files and {len(abstracts)} directories listed in {args.meta}")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
