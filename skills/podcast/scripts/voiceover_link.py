"""Make the voiceover skill's scripts importable from here.

This skill deliberately owns only what a podcast does differently. Detection of
hallucinated filler and the rules a synthesiser's input has to obey are the same
problem in both skills, and a copy of either would drift from the original the
first time someone fixes a phrase list. The two skills therefore sit side by side
under ``.claude/skills`` and this module bridges them.

Usage:
    from voiceover_link import scripts
    scripts()                       # raises with a readable message if absent
    from transcribe import is_suspicious
"""

from __future__ import annotations

import os
import sys

RELATIVE = os.path.join("voiceover", "scripts")


def scripts() -> str:
    """Return the voiceover scripts directory, putting it on sys.path."""
    skills = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(skills, RELATIVE)
    if not os.path.isdir(path):
        raise SystemExit(
            f"Der Skill voiceover fehlt: {path} gibt es nicht.\n"
            "Der Skill podcast baut auf dessen Skripten und Stimmarchiv auf und "
            "laeuft ohne ihn nicht.")
    if path not in sys.path:
        sys.path.insert(0, path)
    return path
