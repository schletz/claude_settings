"""Write the units out as one line each, ready to be translated.

The translation is done by reading this file and writing a second one beside it,
so the format is fixed here rather than improvised per run: it has to carry the
index that validate_podcast.py checks against, the time the reader needs to find
a passage in the source, and the speaker, because a line reads differently when
you know it is the host asking rather than the guest answering.

    <index>|<mm:ss>|<sprecher>|<originaltext>

Usage:
    python export_units.py units.json --speakers refs/speakers.json --out source.txt
    python export_units.py units.json --speakers refs/speakers.json --range 40 80
"""

from __future__ import annotations

import argparse
import json
import sys


def stamp(seconds: float) -> str:
    """Format seconds as MM:SS."""
    return f"{int(seconds) // 60:02d}:{int(seconds) % 60:02d}"


def speaker_names(path: str | None, count: int) -> list[str]:
    """One display name per unit, or a blank column when nothing is known."""
    if not path:
        return [""] * count
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    names = {entry["speaker"]: (entry.get("name") or f"S{entry['speaker']}")
             for entry in data["speakers"]}
    labels = data["labels"]
    if len(labels) != count:
        sys.exit(f"speakers.json passt nicht: {len(labels)} Zuordnungen gegen "
                 f"{count} Einheiten. Wurde dazwischen neu segmentiert?")
    return [names[label] for label in labels]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("units")
    parser.add_argument("--speakers", help="refs/speakers.json aus der Diarisierung")
    parser.add_argument("--out", help="Zieldatei; ohne Angabe nach stdout")
    parser.add_argument("--range", nargs=2, type=int, metavar=("VON", "BIS"),
                        help="nur diesen Indexbereich, Ende ausschliesslich")
    args = parser.parse_args()

    with open(args.units, encoding="utf-8") as handle:
        units = json.load(handle)
    names = speaker_names(args.speakers, len(units))

    low, high = args.range if args.range else (0, len(units))
    lines = [f"{index}|{stamp(units[index]['start'])}|{names[index]}|"
             f"{(units[index].get('text') or units[index].get('hu') or '').strip()}"
             for index in range(max(low, 0), min(high, len(units)))]

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        print(f"{len(lines)} Einheiten -> {args.out}")
    else:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print("\n".join(lines))


if __name__ == "__main__":
    main()
