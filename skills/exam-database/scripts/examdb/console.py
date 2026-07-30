"""Console setup shared by the command line scripts."""

from __future__ import annotations

import sys


def use_utf8_output() -> None:
    """Forces UTF-8 on stdout/stderr.

    On Windows, piped output otherwise uses the ANSI code page and umlauts arrive garbled
    in the calling agent.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")
