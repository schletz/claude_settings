"""Translate word timings from the cut speech track back onto the source timeline.

detect_speech.py hands Whisper a track with the music and the applause removed,
so every timestamp it returns is short of the truth by whatever was cut before
it. Everything downstream cuts audio out of the untouched source — the
diarisation, the reference clips, the report the user checks against the video —
so the offsets have to go back in before segmentation.

A word that straddles a splice is clamped to the region it starts in. That word
is the last one before a cut, its end is guesswork either way, and letting it
run into the next region would produce a unit that spans the removed passage.

The output is a plain list, never a variant dictionary. Which key a words file
carries depends on which script wrote it last — transcribe.py names it after the
variant, patch_words.py always writes "raw" — and every consumer downstream then
needs the matching --variant. A list has no key to get wrong.

Usage:
    python map_words.py <words_speech.json> <speech_regions.json> <words.json>
"""

from __future__ import annotations

import argparse
import bisect
import json
import sys


def locate(offsets: list[float], regions: list[dict], position: float) -> dict:
    """Return the region holding this position on the cut track."""
    index = bisect.bisect_right(offsets, position) - 1
    return regions[max(index, 0)]


def convert(words: list[dict], regions: list[dict]) -> list[dict]:
    """Shift every word, dropping the ones that fall outside any region."""
    offsets = [region["offset"] for region in regions]
    last = regions[-1]["offset"] + regions[-1]["length"]
    out: list[dict] = []
    for word in words:
        if word["start"] > last:
            continue
        region = locate(offsets, regions, word["start"])
        shift = region["start"] - region["offset"]
        start = word["start"] + shift
        end = min(word["end"] + shift, region["end"])
        out.append({"text": word["text"], "start": round(start, 3),
                    "end": round(max(end, start), 3)})
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("words", help="words.json, decoded from speech.wav")
    parser.add_argument("regions", help="speech_regions.json from detect_speech.py")
    parser.add_argument("out", help="words file on the source timeline")
    parser.add_argument("--variant",
                        help="Variante, falls die Eingabe mehrere enthaelt")
    args = parser.parse_args()

    with open(args.words, encoding="utf-8") as handle:
        data = json.load(handle)
    with open(args.regions, encoding="utf-8") as handle:
        regions = json.load(handle)["regions"]

    if isinstance(data, dict):
        key = args.variant or next(iter(data))
        if key not in data:
            sys.exit(f"Variante {key!r} nicht in {args.words}. "
                     f"Vorhanden: {', '.join(data)}")
        data = data[key]
    mapped = convert(data, regions)
    if not mapped:
        sys.exit("Keine Woerter uebertragen — passen words.json und regions.json "
                 "zusammen?")

    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(mapped, handle, ensure_ascii=False, indent=1)

    span = regions[-1]["end"] - regions[0]["start"]
    print(f"{len(mapped)} Woerter auf die Quellzeitachse uebertragen "
          f"({len(regions)} Regionen, {span:.0f}s Spanne)")
    print(f"Geschrieben: {args.out}")


if __name__ == "__main__":
    main()
