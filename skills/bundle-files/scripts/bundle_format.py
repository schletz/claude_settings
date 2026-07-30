"""Model, renderer and parser for the bundle file format.

A bundle is a single UTF-8 text file with LF line endings that archives a
directory tree for agents. It uses XML-like tags but is NOT valid XML: file
content is embedded verbatim, so C# generics or ``&&`` need no escaping.

    <documents>
    <toc abstract-level="1">
    <dir path="Root" level="0">
    <abstract>
    Free text about the whole project (verbatim, may span several lines).
    </abstract>
    <entry name="README.md" start="30" lines="12">One sentence.</entry>
    </dir>
    <dir path="Root/src" level="1">
    <abstract>What the whole subtree below Root/src contains.</abstract>
    </dir>
    <dir path="Root/src/Model" level="2">
    <entry name="Candidate.cs" start="42" lines="20" types="class Candidate : Person">One sentence.</entry>
    <entry name="logo.png" binary="true" bytes="1234">One sentence.</entry>
    </dir>
    </toc>
    <document path="Root/src/Model/Candidate.cs" lines="20">
    ...file content...
    </document>
    </documents>

The TOC lists every directory depth-first, including directories without
files, so the flat list still shows the tree. ``level`` is the distance from
the bundle's top (the root folder, or ``""`` in a bundle without root).
Directories down to ``abstract-level`` carry an ``<abstract>`` that summarizes
their whole subtree; the one of level 0 describes the whole project. An
abstract without line breaks takes one line, otherwise it is a block.

``start`` is the 1-based line number of the first content line inside the
bundle, so an agent can read a file with any line-based reader. The parser
does not rely on ``start``: it locates ``<document path=...>`` and takes the
next ``lines`` lines, which keeps it immune to ``</document>`` inside content.
"""

from __future__ import annotations

import posixpath
import re
from collections.abc import Iterable
from dataclasses import dataclass, field

_ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
# Attribute lists are matched as quoted pairs, so '<' and '>' may occur in values (generic types).
_ATTRS = r'((?:[\w-]+="[^"]*"\s*)*)'
_DOCUMENT_RE = re.compile(rf'^<document {_ATTRS}>$')
_ENTRY_RE = re.compile(rf'^<entry {_ATTRS}>(.*)</entry>$')
_DIR_RE = re.compile(rf'^<dir {_ATTRS}>$')
_TOC_RE = re.compile(rf'^<toc\s*{_ATTRS}>$')
_ABSTRACT_RE = re.compile(r'^<abstract>(.*)</abstract>$')


@dataclass
class BundleFile:
    """One archived file. ``content`` is None for binary files."""

    path: str
    content: str | None
    summary: str = ""
    types: str = ""
    converted: str = ""
    size: int = 0

    @property
    def directory(self) -> str:
        return posixpath.dirname(self.path)

    @property
    def name(self) -> str:
        return posixpath.basename(self.path)

    @property
    def lines(self) -> list[str]:
        return self.content.split("\n") if self.content else []


@dataclass
class Bundle:
    """Directory abstracts and all archived files in arbitrary order.

    The abstract of the top directory (level 0) is the project description.
    """

    files: list[BundleFile] = field(default_factory=list)
    abstract_level: int = 0
    abstracts: dict[str, str] = field(default_factory=dict)

    def sorted_files(self) -> list[BundleFile]:
        """Files grouped by directory in depth-first order, the order used in TOC and body."""
        return sorted(self.files, key=lambda f: (_directory_key(f.directory), f.name.lower()))

    def directory_levels(self) -> dict[str, int]:
        return directory_levels(f.path for f in self.files)

    def missing_abstracts(self) -> list[str]:
        """Directories down to ``abstract_level`` (level 0 always) that still lack an abstract."""
        return [d for d, level in self.directory_levels().items()
                if level <= self.abstract_level and not self.abstracts.get(d, "").strip()]


@dataclass
class TocDirectory:
    """One ``<dir>`` block of a TOC, kept verbatim so its start offsets stay valid."""

    path: str
    level: int
    lines: list[str]

    @property
    def entry_count(self) -> int:
        return sum(1 for line in self.lines if line.startswith("<entry "))


def normalize_text(text: str) -> str:
    """Use LF line endings and drop the final newline so line counts are exact."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text[:-1] if text.endswith("\n") else text


def attrs(**values: str | int) -> str:
    """Render attributes, escaping only what would end a value or be ambiguous."""
    def escape(v: str | int) -> str:
        return str(v).replace("&", "&amp;").replace('"', "&quot;")
    return " ".join(f'{k}="{escape(v)}"' for k, v in values.items() if v not in ("", None))


def _parse_attrs(text: str) -> dict[str, str]:
    return {k: v.replace("&quot;", '"').replace("&amp;", "&") for k, v in _ATTR_RE.findall(text)}


def _directory_key(directory: str) -> tuple[str, ...]:
    """Sort key that puts every directory right before its subdirectories (depth-first)."""
    return tuple(directory.lower().split("/")) if directory else ()


def _common_root(paths: list[str]) -> str | None:
    tops = {p.split("/")[0] for p in paths}
    if len(tops) == 1 and all("/" in p for p in paths):
        return tops.pop()
    return None


def root_of(files: list[BundleFile]) -> str | None:
    """Return the common top folder of all paths, or None for a bundle made with ``--no-root``.

    A root-less bundle whose files all lie in one folder yields that folder,
    which is equivalent: bundling it as root restores the same paths.
    """
    return _common_root([f.path for f in files])


def directory_levels(paths: Iterable[str]) -> dict[str, int]:
    """All directories of the given file paths plus their empty ancestors, depth-first.

    The level is the distance from the bundle's top: the root folder (or ``""``
    in a bundle without root) has level 0, its subdirectories level 1, and so on.
    """
    paths = list(paths)
    first = 1 if _common_root(paths) else 0
    levels: dict[str, int] = {}
    for path in paths:
        parts = path.split("/")[:-1]
        for depth in range(first, len(parts) + 1):
            levels["/".join(parts[:depth])] = depth - first
    return dict(sorted(levels.items(), key=lambda item: _directory_key(item[0])))


def _header(files: list[BundleFile]) -> list[str]:
    """Explain the format to a reader that has no skill or script for it.

    No line may start with '<': the parser identifies tags by line prefix.
    No date, so rebuilding an unchanged tree yields an identical file.
    """
    root = root_of(files)
    source = f"the directory tree '{root}'" if root else "a directory tree (paths relative to its top level)"
    return [
        "<!--",
        f"Bundle of {len(files)} files from {source}, created by bundle.py",
        "(skill bundle-files). It archives a project in one text file for AI agents.",
        "",
        "This is NOT well-formed XML. File contents are embedded verbatim without escaping,",
        "so an XML parser will fail. Read it as plain text.",
        "",
        "How to read it without loading everything:",
        "1. Read the table of contents from the top of the file up to the line '</toc>'.",
        "   It lists all directories depth-first; level is the depth below the top, and an",
        "   abstract summarizes the directory's whole subtree (level 0: the whole project).",
        "   In a large TOC read the dir and abstract lines of low levels first, then only",
        "   the entries of the subtrees you need.",
        "2. Each entry gives start=S lines=N: the file's content is on lines S to S+N-1",
        "   of this file. Read only that range (e.g. a line-based read with offset S, limit N).",
        "Entries with converted='pdf' (or docx, ...) hold Markdown extracted from the original",
        "document; entries with binary='true' have no content.",
        "-->",
    ]


def render(bundle: Bundle) -> str:
    """Render the bundle, computing ``start`` offsets for every text file."""
    files = bundle.sorted_files()
    entries: dict[str, list[BundleFile]] = {}
    for f in files:
        entries.setdefault(f.directory, []).append(f)
    levels = directory_levels(f.path for f in files)
    # Abstracts of directories that no longer hold files are dropped here.
    abstracts = {d: _abstract_lines(bundle.abstracts.get(d, "")) for d in levels}

    header = _header(files)
    # Every TOC entry takes exactly one line and abstracts have a known
    # length, so the TOC length is known before the offsets are filled in.
    toc_length = len(header) + 2 + 1  # header, <documents>, <toc> ... </toc>
    toc_length += sum(2 + len(entries.get(d, [])) + len(abstracts[d]) for d in levels)

    starts: dict[str, int] = {}
    tag_line = toc_length + 1
    for f in files:
        if f.content is None:
            continue
        starts[f.path] = tag_line + 1
        tag_line += len(f.lines) + 2

    toc_tag = f"<toc {attrs(**{'abstract-level': bundle.abstract_level})}>" if bundle.abstract_level else "<toc>"
    out = [*header, "<documents>", toc_tag]
    for directory, level in levels.items():
        # attrs() drops empty values, but the top level of a --no-root bundle needs path="".
        out.append(f"<dir {attrs(path=directory, level=level)}>" if directory else f'<dir path="" {attrs(level=level)}>')
        out += abstracts[directory]
        for f in entries.get(directory, []):
            summary = " ".join(f.summary.split())
            if f.content is None:
                entry = attrs(name=f.name, binary="true", bytes=f.size)
            else:
                entry = attrs(name=f.name, start=starts[f.path], lines=len(f.lines),
                              types=f.types, converted=f.converted)
            out.append(f"<entry {entry}>{summary}</entry>")
        out.append("</dir>")
    out.append("</toc>")
    for f in files:
        if f.content is None:
            continue
        out.append(f"<document {attrs(path=f.path, lines=len(f.lines))}>")
        out += f.lines
        out.append("</document>")
    out.append("</documents>")
    return "\n".join(out) + "\n"


def _abstract_lines(text: str) -> list[str]:
    """One line for a single-line abstract, a block keeping the line breaks otherwise."""
    lines = [line.rstrip() for line in normalize_text(text).strip().split("\n")]
    if not lines[0]:
        return []
    if len(lines) == 1:
        return [f"<abstract>{lines[0]}</abstract>"]
    return ["<abstract>", *lines, "</abstract>"]


def parse(text: str) -> Bundle:
    """Parse a bundle produced by :func:`render` (or edited by hand)."""
    lines = text.replace("\r\n", "\n").split("\n")
    bundle = Bundle()
    entries: dict[str, BundleFile] = {}
    contents: dict[str, str] = {}
    directory = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        if line == "<abstract>":
            end = lines.index("</abstract>", i)
            bundle.abstracts[directory] = "\n".join(lines[i + 1:end])
            i = end
        elif m := _TOC_RE.match(line):
            bundle.abstract_level = int(_parse_attrs(m.group(1)).get("abstract-level", 0))
        elif m := _DIR_RE.match(line):
            directory = _parse_attrs(m.group(1)).get("path", "")
        elif m := _ABSTRACT_RE.match(line):
            bundle.abstracts[directory] = m.group(1)
        elif m := _ENTRY_RE.match(line):
            a = _parse_attrs(m.group(1))
            path = posixpath.join(directory, a["name"]) if directory else a["name"]
            binary = a.get("binary") == "true"
            entries[path] = BundleFile(path, None if binary else "", m.group(2), a.get("types", ""),
                                       a.get("converted", ""), int(a.get("bytes", 0)))
        elif m := _DOCUMENT_RE.match(line):
            a = _parse_attrs(m.group(1))
            count = int(a["lines"])
            contents[a["path"]] = "\n".join(lines[i + 1:i + 1 + count])
            i += count + 1  # skip content and land on </document>
        i += 1

    for path, content in contents.items():
        entries.setdefault(path, BundleFile(path, "")).content = content
    bundle.files = list(entries.values())
    return bundle


def read_toc(text: str) -> str:
    """Return the TOC block of a bundle without parsing the documents."""
    end = text.find("\n</toc>\n")
    return text[:end + len("\n</toc>")] if end >= 0 else ""


def split_toc(toc: str) -> tuple[list[str], list[TocDirectory]]:
    """Split a TOC into its head (the ``<toc>`` tag) and its ``<dir>`` blocks.

    The explanatory comment, ``<documents>`` and ``</toc>`` are left out.
    """
    head: list[str] = []
    dirs: list[TocDirectory] = []
    in_comment = False
    for line in toc.split("\n"):
        if line == "<!--" or in_comment:
            in_comment = line != "-->"
            continue
        if line in ("<documents>", "</toc>"):
            continue
        if m := _DIR_RE.match(line):
            a = _parse_attrs(m.group(1))
            dirs.append(TocDirectory(a.get("path", ""), int(a["level"]), [line]))
        elif dirs:
            dirs[-1].lines.append(line)
        else:
            head.append(line)
    return head, dirs
