"""Archive a directory tree as a single bundle file that agents can read selectively.

Usage:
    bundle.py create SRC OUT [--meta META.json | --base OLD.bundle] [--abstract-level N] [--no-root] [--ext cs,md] [--exclude-dir Migrations]
    bundle.py update BUNDLE META.json
    bundle.py add BUNDLE FILE --path Root/dir/File.cs [--summary "One sentence."]
    bundle.py remove BUNDLE Root/dir/File.cs [...]
    bundle.py extract BUNDLE DEST [--force]

``create`` scans SRC; get a META.json to fill in with ``read_meta.py OUT``.
``--abstract-level N`` asks for an abstract on every directory down to level N;
level 0, the project description, always gets one. read_meta.py lists them.
With ``--base`` it takes abstracts and summaries from a previous
bundle (OUT may be the same file) and reports changed and new files.
``update`` applies an edited ``read_meta.py BUNDLE`` output to the bundle.
``add`` adds or replaces one file; to edit a file that exists only in the
bundle, extract it with ``read_document.py BUNDLE PATH --raw --out FILE``,
edit FILE and add it back under the same path.
``extract`` restores all plain text files, e.g. to edit and compile them in
an IDE, followed by ``create DEST/Root BUNDLE --base BUNDLE`` (``create DEST BUNDLE
--base BUNDLE --no-root`` for a bundle without root folder; extract prints the command).
Every command rewrites the whole bundle, so all line offsets in the TOC stay correct.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# python -I leaves the script's directory off sys.path; the sibling modules live there.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import bundle_ops  # noqa: E402
from bundle_format import Bundle, parse, render  # noqa: E402
from file_list import add_filter_arguments, list_files  # noqa: E402
from file_reader import read_file  # noqa: E402


def main() -> None:
    # File names with umlauts must print on consoles that default to cp1252 or cp850.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    args = _parse_args()
    if args.command == "create":
        # Read the base first: OUT may overwrite it.
        base = parse(args.base.read_text(encoding="utf-8")) if args.base else None
        prefix = "" if args.no_root else args.src.resolve().name + "/"
        bundle = Bundle(files=[read_file(args.src / p, f"{prefix}{p}")
                               for p in list_files(args.src, args.ext, args.exclude_dir, skip=args.out)])
        messages = bundle_ops.merge_base(bundle, base) if base else []
        if args.abstract_level is not None:
            bundle.abstract_level = args.abstract_level
        if args.meta:
            messages = bundle_ops.apply_meta(bundle, json.loads(args.meta.read_text(encoding="utf-8")))
        _write(args.out, bundle, messages)
        return

    bundle = parse(args.bundle.read_text(encoding="utf-8"))
    try:
        if args.command == "extract":
            _report(bundle_ops.extract(bundle, args.dest, args.force))
            return
        if args.command == "update":
            messages = bundle_ops.apply_meta(bundle, json.loads(args.meta.read_text(encoding="utf-8")))
        elif args.command == "add":
            messages = bundle_ops.add_file(bundle, args.file, args.path, args.summary)
        else:
            messages = bundle_ops.remove_files(bundle, args.paths)
    except KeyError as e:
        sys.exit(f"error: not in the bundle: {e.args[0]}")
    except (ValueError, FileExistsError) as e:
        sys.exit(f"error: {e}")
    _write(args.bundle, bundle, messages)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="bundle a directory")
    create.add_argument("src", type=Path)
    create.add_argument("out", type=Path)
    meta = create.add_mutually_exclusive_group()
    meta.add_argument("--meta", type=Path, help="JSON from read_meta.py with abstracts and summaries")
    meta.add_argument("--base", type=Path, help="previous bundle to take abstracts and summaries from")
    create.add_argument("--abstract-level", type=int,
                        help="directories down to this level get an abstract (default: 0, or the base's)")
    create.add_argument("--no-root", action="store_true",
                        help="store paths relative to SRC instead of prefixing them with SRC's folder name")
    add_filter_arguments(create)

    update = commands.add_parser("update", help="apply edited abstracts and summaries")
    update.add_argument("bundle", type=Path)
    update.add_argument("meta", type=Path)

    add = commands.add_parser("add", help="add or replace one file in an existing bundle")
    add.add_argument("bundle", type=Path)
    add.add_argument("file", type=Path)
    add.add_argument("--path", required=True, help="path inside the bundle as the TOC shows it, e.g. Root/src/File.cs")
    add.add_argument("--summary", help="one sentence; when replacing, the old summary is kept if omitted")

    remove = commands.add_parser("remove", help="remove files from an existing bundle")
    remove.add_argument("bundle", type=Path)
    remove.add_argument("paths", nargs="+", help="full paths inside the bundle")

    extract = commands.add_parser("extract", help="restore the plain text files into a directory")
    extract.add_argument("bundle", type=Path)
    extract.add_argument("dest", type=Path)
    extract.add_argument("--force", action="store_true", help="overwrite existing files")
    return parser.parse_args()


def _write(out: Path, bundle: Bundle, messages: list[str]) -> None:
    text = render(bundle)
    out.write_text(text, encoding="utf-8", newline="\n")
    texts = [f for f in bundle.files if f.content is not None]
    converted = sum(1 for f in texts if f.converted)
    binary = len(bundle.files) - len(texts)
    _report([f"{out}: {len(bundle.files)} files ({len(texts) - converted} text, {converted} converted, "
             f"{binary} binary), {text.count(chr(10))} lines, {len(text.encode('utf-8')) // 1024} KB", *messages])


def _report(messages: list[str]) -> None:
    print("\n".join(m for m in messages if m))


if __name__ == "__main__":
    main()
