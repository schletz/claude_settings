"""Check the podcast translation and write the cue file the synthesis reads.

Two of the voice-over's three checks apply unchanged. Anything a phonemiser reads
out literally or reads wrongly — digits, ellipses, bracketed notes, abbreviations
— has to be gone before synthesis, and the index set has to be complete, because
a silently missing index costs a sentence that nobody will notice is absent.

The third check, the character budget, is gone with the picture. Nothing has to
fit anywhere, so a unit may be as long as the sentence needs.

What comes in its place is the drop. A passage that carries no usable speech —
applause that Whisper answered with a subscribe phrase, a bar of music against
the first sentence — is marked ``<index>|-`` and leaves no audio behind. It has
to be written out rather than left blank, so that a forgotten line stays
distinguishable from a deliberate one.

Usage:
    python validate_podcast.py units.json cues_pod.json pod_*.txt --override pod_fix.txt
"""

from __future__ import annotations

import argparse
import json
import sys

from voiceover_link import scripts

scripts()
from validate_vo import FORBIDDEN, load_translations  # noqa: E402  — needs the path

# The single character that marks a unit as deliberately not spoken.
DROP = "-"


def stamp(seconds: float) -> str:
    """Format seconds as MM:SS."""
    return f"{int(seconds) // 60:02d}:{int(seconds) % 60:02d}"


def check_units(units: list[dict], texts: dict[int, str],
                problems: list[str]) -> list[int]:
    """Apply the forbidden patterns and collect the deliberately dropped units."""
    dropped: list[int] = []
    for index, unit in enumerate(units):
        text = (texts.get(index) or "").strip()
        if text == DROP:
            dropped.append(index)
            continue
        if not text:
            problems.append(f"Einheit {index} ({stamp(unit['start'])}): leer. "
                            f"Absichtliche Auslassungen mit '{index}|{DROP}' "
                            f"kennzeichnen.")
            continue
        for pattern, reason in FORBIDDEN:
            found = pattern.search(text)
            if found:
                problems.append(f"Einheit {index} ({stamp(unit['start'])}): "
                                f"{reason} -> {found.group(0)!r}")
    return dropped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("units")
    parser.add_argument("out")
    parser.add_argument("translations", nargs="+")
    parser.add_argument("--override", nargs="*", default=[],
                        help="Dateien, deren Zeilen frueher gelesene ersetzen")
    args = parser.parse_args()

    with open(args.units, encoding="utf-8") as handle:
        units = json.load(handle)
    texts, problems = load_translations(args.translations, args.override)

    missing = [index for index in range(len(units)) if index not in texts]
    extra = [index for index in texts if index >= len(units)]
    if missing:
        problems.append(f"fehlende Indizes: {missing[:40]}")
    if extra:
        problems.append(f"ueberzaehlige Indizes: {extra[:40]}")

    dropped = check_units(units, texts, problems)

    spoken = len(units) - len(dropped)
    print(f"{len(units)} Einheiten, {spoken} gesprochen, {len(dropped)} verworfen")
    if dropped:
        print("Verworfen: " + ", ".join(
            f"{index} ({stamp(units[index]['start'])})" for index in dropped[:25]))

    if problems:
        print(f"\nFEHLER ({len(problems)}):")
        for problem in problems[:40]:
            print(f"  {problem}")
        sys.exit(1)

    cues = [{"start": unit["start"], "end": unit["end"],
             "text": "" if texts[index].strip() == DROP else texts[index].strip()}
            for index, unit in enumerate(units)]
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(cues, handle, ensure_ascii=False, indent=1)

    chars = sum(len(cue["text"]) for cue in cues)
    print(f"\nZeichen gesamt: {chars}  (grob {chars / 15 / 60:.0f} Minuten Sprache)")
    print(f"OK - geschrieben nach {args.out}")


if __name__ == "__main__":
    main()
