"""Console setup, bundle loading and size-limited output shared by the reading scripts."""

from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


def setup_console() -> None:
    """Print UTF-8, because file names with umlauts must survive cp1252 or cp850 consoles."""
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def load(source: str) -> str:
    """Bundle text from a local file or an http(s) URL."""
    if not re.match(r"https?://", source, re.IGNORECASE):
        return Path(source).read_text(encoding="utf-8")
    try:
        with urllib.request.urlopen(source, timeout=60) as response:
            data = response.read()
    except (urllib.error.URLError, TimeoutError) as e:
        sys.exit(f"error: cannot download {source}: {e}")
    # Same newline handling as read_text, so a bundle served with CRLF parses identically.
    return data.decode("utf-8").replace("\r\n", "\n")


def emit(text: str, out: Path | None, max_chars: int, narrow_hint: str) -> None:
    """Print ``text``, or write it to ``out``.

    Output above ``max_chars`` without ``out`` is refused with exit code 1
    instead of being printed: agent shells truncate long output, and a caller
    piping it into another command must not silently get something else.
    """
    if out is None:
        if len(text) > max_chars:
            sys.exit(f"error: output has {len(text)} chars, more than --max-chars {max_chars}; "
                     f"{narrow_hint}, or pass --out FILE to write it to a file")
        print(text)
        return
    out.write_text(text + "\n", encoding="utf-8", newline="\n")
    print(f"{len(text)} chars, {text.count(chr(10)) + 1} lines written to {out}")
