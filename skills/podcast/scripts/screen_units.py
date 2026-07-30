"""Point at the units that probably hold no speech, so they can be dropped.

detect_speech.py removes the passages a speech gate is sure about. What survives
is the harder half: applause with a shout in it, the murmur of a hall, a bar of
music tucked against the first sentence. Whisper answers those with text — a
subscribe phrase, a repeated fragment, a single word stretched over ten seconds —
and that text reads plausibly enough to be translated by mistake.

Nothing is deleted here. The script marks candidates and says why, and the reader
decides, because the same signature is also produced by legitimate speech: a
short interjection is short, and a speaker who trails off does leave a thin unit
behind. Dropping a real sentence is worse than keeping a bar of music, so the
verdict stays with the person reading the transcript.

Signals, and what each one is worth:

    Floskel        a phrase Whisper produces over noise; the strongest signal
    Schleife       the same fragment several times over; almost always noise
    gedehnt        few characters over many seconds — the classic music artefact
    Randlage       first or last unit of a region, short: sits against the cut
    isoliert       a whole region carrying next to no text

Usage:
    python screen_units.py units.json --regions speech_regions.json
    python screen_units.py units.json --regions speech_regions.json --list
"""

from __future__ import annotations

import argparse
import json

from voiceover_link import scripts

scripts()
from transcribe import is_suspicious  # noqa: E402  — needs the path above

# A unit this thin has fewer characters per second than any real delivery. Slow
# speech runs about 10 characters/s; music and applause come out below three.
THIN_DENSITY = 4.0
THIN_MIN_SPAN = 2.5
# Short units at a region edge are where a cut leaves half a bar of music.
EDGE_WORDS = 4
EDGE_MARGIN = 0.6
# A region whose whole transcript stays under this many characters per second.
REGION_DENSITY = 3.0


def stamp(seconds: float) -> str:
    """Format seconds as MM:SS."""
    return f"{int(seconds) // 60:02d}:{int(seconds) % 60:02d}"


def text_of(unit: dict) -> str:
    """Read a unit's source text, tolerating files written before the rename."""
    return (unit.get("text") or unit.get("hu") or "").strip()


def edges(units: list[dict], regions: list[dict]) -> set[int]:
    """Indices of units that touch the start or the end of a speech region."""
    marked: set[int] = set()
    for region in regions:
        for index, unit in enumerate(units):
            if abs(unit["start"] - region["start"]) <= EDGE_MARGIN:
                marked.add(index)
            if abs(unit["end"] - region["end"]) <= EDGE_MARGIN:
                marked.add(index)
    return marked


def thin_regions(units: list[dict], regions: list[dict]) -> list[tuple[dict, float]]:
    """Regions whose entire transcript is too thin to be speech."""
    out = []
    for region in regions:
        span = region["end"] - region["start"]
        chars = sum(len(text_of(unit)) for unit in units
                    if region["start"] - 0.5 <= unit["start"] < region["end"])
        if span >= 3.0 and chars / span < REGION_DENSITY:
            out.append((region, chars / span))
    return out


def screen(units: list[dict], regions: list[dict]) -> dict[int, list[str]]:
    """Collect every reason to doubt each unit."""
    at_edge = edges(units, regions) if regions else set()
    found: dict[int, list[str]] = {}

    for index, unit in enumerate(units):
        text = text_of(unit)
        span = max(unit["end"] - unit["start"], 0.01)
        reasons: list[str] = []

        flag = is_suspicious(text)
        if flag:
            reasons.append(flag)
        if span >= THIN_MIN_SPAN and len(text) / span < THIN_DENSITY:
            reasons.append(f"gedehnt ({len(text) / span:.1f} Zeichen/s)")
        if index in at_edge and len(text.split()) <= EDGE_WORDS:
            reasons.append("Randlage")
        if index and text and text == text_of(units[index - 1]):
            reasons.append("Wiederholung der vorigen Einheit")

        if reasons:
            found[index] = reasons
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("units")
    parser.add_argument("--regions", help="speech_regions.json from detect_speech.py")
    parser.add_argument("--list", action="store_true",
                        help="nur die Indizes ausgeben, zum Weiterreichen")
    args = parser.parse_args()

    with open(args.units, encoding="utf-8") as handle:
        units = json.load(handle)
    regions = []
    if args.regions:
        with open(args.regions, encoding="utf-8") as handle:
            regions = json.load(handle)["regions"]

    found = screen(units, regions)
    if args.list:
        print(" ".join(str(index) for index in sorted(found)))
        return

    print(f"{len(units)} Einheiten geprueft, {len(found)} auffaellig\n")
    for index in sorted(found):
        unit = units[index]
        print(f"{index:4d}  {stamp(unit['start'])}  {unit['end'] - unit['start']:5.1f}s  "
              f"{', '.join(found[index])}")
        print(f"      {text_of(unit)[:110]}")

    thin = thin_regions(units, regions) if regions else []
    if thin:
        print(f"\nRegionen fast ohne Text ({len(thin)}) - dort steht vermutlich "
              f"Musik oder Applaus:")
        for region, density in thin:
            print(f"  {stamp(region['start'])} - {stamp(region['end'])}  "
                  f"{density:.1f} Zeichen/s")

    print("\nJede Meldung selbst nachlesen. Was wirklich keine Sprache ist, "
          "bekommt in der Uebersetzung eine Zeile '<index>|-' und faellt damit "
          "aus dem Podcast.")


if __name__ == "__main__":
    main()
