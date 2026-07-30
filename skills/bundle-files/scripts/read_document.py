"""Print selected files of a bundle created by bundle.py, or search them.

Usage:
    read_document.py BUNDLE PATH [PATH ...]       # files, wrapped in <document> tags
    read_document.py BUNDLE PATH --lines 20-60    # a line range of each file
    read_document.py BUNDLE PATH -n               # with line numbers
    read_document.py BUNDLE PATH --raw --out FILE # one file verbatim, to edit and re-add
    read_document.py BUNDLE --search REGEX [PATH ...]  # matching lines as path:line, in all or the given files

The table of contents is printed by read_toc.py.

BUNDLE is a local file or an http(s) URL, e.g. a raw GitHub link; a URL is
downloaded on every call.

PATH is a full bundle path, a glob (``*/Model/*.cs``) or a file name or path
suffix (``Candidate.cs``, ``Model/Candidate.cs``). Search results give line
numbers within the file, ready for ``PATH --lines``. Output longer than
--max-chars ends with exit code 1 and a message on stderr unless --out is
given, because agent shells truncate long console output.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from pathlib import Path

# python -I leaves the script's directory off sys.path; the sibling modules live there.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import bundle_io  # noqa: E402
from bundle_format import BundleFile, attrs, parse  # noqa: E402


def main() -> None:
    bundle_io.setup_console()
    args = _parse_args()
    if not args.paths and not args.search:
        sys.exit("error: name files or pass --search; read_toc.py prints the table of contents")

    files = parse(bundle_io.load(args.bundle)).sorted_files()
    selected: list[BundleFile] = [] if args.paths else files
    for pattern in args.paths:
        matches = _match(files, pattern)
        if not matches:
            sys.exit(f"error: no file matches '{pattern}', see read_toc.py for valid paths")
        selected += [f for f in matches if f not in selected]
    if args.search:
        bundle_io.emit(_search(selected, args.search), args.out, args.max_chars,
                       "search fewer files (PATH arguments) or use a more specific REGEX")
        return
    if args.raw:
        _extract(selected, args.out)
        return
    bundle_io.emit("\n".join(_format(f, args.lines, args.n) for f in selected), args.out, args.max_chars,
                   "select fewer files or a range with --lines")


def _parse_args() -> argparse.Namespace:
    def line_range(value: str) -> tuple[int, int]:
        first, _, last = value.partition("-")
        return int(first), int(last) if last else sys.maxsize

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("bundle", help="bundle file or http(s) URL")
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--lines", type=line_range, help="1-based range like 20-60 or 20-")
    parser.add_argument("-n", action="store_true", help="prefix lines with their number in the file")
    parser.add_argument("--search", metavar="REGEX",
                        help="list matching lines (case-insensitive) as path:line: text")
    parser.add_argument("--raw", action="store_true",
                        help="content of exactly one file, without tags, for editing; needs --out")
    parser.add_argument("--out", type=Path, help="always write to this file")
    parser.add_argument("--max-chars", type=int, default=25000)
    return parser.parse_args()


def _match(files: list[BundleFile], pattern: str) -> list[BundleFile]:
    pattern = pattern.replace("\\", "/")
    exact = [f for f in files if f.path == pattern]
    if exact:
        return exact
    if any(c in pattern for c in "*?["):
        return [f for f in files if fnmatch.fnmatchcase(f.path, pattern) or fnmatch.fnmatchcase(f.path, "*/" + pattern)]
    return [f for f in files if f.path.endswith("/" + pattern)]


def _search(selected: list[BundleFile], pattern: str) -> str:
    """Matching lines with their line number inside the file, so a hit maps directly to --lines."""
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        sys.exit(f"error: invalid regex '{pattern}': {e}")
    hits, found_in = [], set()
    for f in selected:
        for number, line in enumerate(f.lines, 1):
            if m := regex.search(line):
                hits.append(f"{f.path}:{number}: {_snippet(line, m)}")
                found_in.add(f.path)
    return "\n".join(hits + [f"{len(hits)} matching lines in {len(found_in)} of {len(selected)} files"])


def _snippet(line: str, match: re.Match) -> str:
    # Converted documents have paragraph-long lines; show the part around the match.
    line = line.strip()
    if len(line) <= 200:
        return line
    start = max(0, match.start() - 80)
    return ("…" if start else "") + line[start:start + 200] + ("…" if start + 200 < len(line) else "")


def _extract(selected: list[BundleFile], out: Path | None) -> None:
    """Write one file verbatim so it can be edited and added back with bundle.py add."""
    if len(selected) != 1:
        sys.exit("error: --raw needs exactly one file, matched: " + ", ".join(f.path for f in selected))
    if out is None:
        sys.exit("error: --raw needs --out")
    f = selected[0]
    if f.content is None:
        sys.exit(f"error: {f.path} is binary, its content is not in the bundle")
    out.write_text(f.content + "\n", encoding="utf-8", newline="\n")
    print(f"{f.path} ({len(f.lines)} lines) written to {out}")


def _format(f: BundleFile, lines: tuple[int, int] | None, numbered: bool) -> str:
    if f.content is None:
        return f"<document {attrs(path=f.path, binary='true', bytes=f.size)} />"
    first, last = lines or (1, sys.maxsize)
    body = f.lines[first - 1:last]
    if numbered:
        body = [f"{first + i:>5}  {line}" for i, line in enumerate(body)]
    shown = f"{first}-{first + len(body) - 1}" if lines else ""
    return "\n".join([f"<document {attrs(path=f.path, lines=len(f.lines), shown=shown)}>", *body, "</document>"])


if __name__ == "__main__":
    main()
