"""Validate a SubRip file before muxing.

Checks numbering, timecode syntax, monotonic non-overlapping cues, display durations,
line count and line length, and optionally that no cue runs past the media duration.

Usage:
    python check_srt.py <file.srt> [--media-duration 1730.26] [--max-chars 45]
"""

import argparse
import re
import sys

TIME = re.compile(
    r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})"
)

# Timecodes are rounded to milliseconds; allow that much slack on duration limits.
TOLERANCE = 0.002


def to_seconds(hours: str, minutes: str, seconds: str, millis: str) -> float:
    """Convert the four capture groups of an SRT timecode into seconds."""
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("srt")
    parser.add_argument("--media-duration", type=float, default=None)
    parser.add_argument("--max-chars", type=int, default=45)
    parser.add_argument("--min", dest="min_dur", type=float, default=1.2)
    parser.add_argument("--max", dest="max_dur", type=float, default=8.0)
    args = parser.parse_args()

    with open(args.srt, encoding="utf-8") as fh:
        raw = fh.read()
    if raw.startswith("﻿"):
        print("HINWEIS: Datei beginnt mit BOM - fuer maximale Kompatibilitaet entfernen.")
    blocks = [b for b in raw.replace("\r\n", "\n").split("\n\n") if b.strip()]

    problems: list[str] = []
    previous_end = -1.0
    last_end = 0.0

    for expected, block in enumerate(blocks, start=1):
        lines = block.strip().split("\n")
        if not lines[0].strip().isdigit():
            problems.append(f"Block {expected}: fehlende Nummer -> {lines[0]!r}")
            continue
        if int(lines[0]) != expected:
            problems.append(f"Block {expected}: Nummer ist {lines[0]}")
        match = TIME.match(lines[1]) if len(lines) > 1 else None
        if not match:
            problems.append(f"Cue {expected}: unlesbare Zeitzeile")
            continue

        start = to_seconds(*match.groups()[:4])
        end = to_seconds(*match.groups()[4:])
        duration = end - start

        if duration <= 0:
            problems.append(f"Cue {expected}: Ende <= Start")
        if start < previous_end:
            problems.append(
                f"Cue {expected}: ueberlappt Vorgaenger ({start:.2f}s < {previous_end:.2f}s)")
        # SRT timecodes are millisecond-rounded, so compare with a small tolerance -
        # otherwise a cue stretched to exactly the minimum duration fails this check.
        if duration > args.max_dur + TOLERANCE:
            problems.append(f"Cue {expected}: Dauer {duration:.1f}s > {args.max_dur}s")
        if 0 < duration < args.min_dur - TOLERANCE:
            problems.append(f"Cue {expected}: Dauer {duration:.1f}s < {args.min_dur}s")

        text_lines = lines[2:]
        if not any(line.strip() for line in text_lines):
            problems.append(f"Cue {expected}: leerer Text")
        if len(text_lines) > 2:
            problems.append(f"Cue {expected}: {len(text_lines)} Textzeilen (max 2)")
        for line in text_lines:
            if len(line) > args.max_chars:
                problems.append(
                    f"Cue {expected}: Zeile {len(line)} Zeichen -> {line[:50]!r}")
        if args.media_duration is not None and end > args.media_duration:
            problems.append(
                f"Cue {expected}: endet bei {end:.1f}s, Medium ist {args.media_duration:.1f}s lang")

        previous_end = end
        last_end = max(last_end, end)

    print(f"{len(blocks)} Cues, letzter endet bei {last_end:.1f}s")
    if problems:
        print(f"{len(problems)} Problem(e):")
        for problem in problems:
            print("  " + problem)
        sys.exit(1)
    print("OK - keine Probleme gefunden")


if __name__ == "__main__":
    main()
