"""Find passages the transcription silently dropped.

The long-form decoder occasionally throws away a whole stretch of speech without any
error - observed twice in one 42-minute file, each time about half a minute, once right
at the start. The text that comes back reads perfectly fluent, so nothing in the output
hints at the loss. Only the timeline does: where speech was dropped, the words thin out
or a single word is stamped as lasting half a minute.

This script reads the JSON written by `transcribe.py --words` and reports every stretch
that looks like a dropout. Run it before building cues; re-decode the reported ranges
from their own clip and splice them in with `patch_words.py`.

Usage:
    python check_coverage.py words.json [--variant raw] [--bucket 30] [--min-words 60]
"""

import argparse
import json
import sys


def load_words(path: str, variant: str | None) -> list[dict]:
    """Read a words.json and return the word list of one variant."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        key = variant or next(iter(data))
        if key not in data:
            sys.exit(f"Variante {key!r} nicht in {path}. Vorhanden: {', '.join(data)}")
        words = data[key]
    else:
        words = data
    usable = [w for w in words if w.get("start") is not None]
    if not usable:
        sys.exit("Keine brauchbaren Wortzeiten gefunden.")
    return usable


def stamp(seconds: float) -> str:
    """Format seconds as MM:SS."""
    return f"{int(seconds) // 60:02d}:{int(seconds) % 60:02d}"


def sparse_buckets(words: list[dict], bucket: float, minimum: int) -> list[tuple]:
    """Return (start, count) for every time bucket holding suspiciously few words.

    The final bucket is left out: it is only partly covered by the recording, so a low
    count there says nothing.
    """
    counts: dict[int, int] = {}
    for word in words:
        index = int(word["start"] // bucket)
        counts[index] = counts.get(index, 0) + 1
    last = int(words[-1]["end"] // bucket)
    return [(index * bucket, counts.get(index, 0))
            for index in range(last) if counts.get(index, 0) < minimum]


def main() -> None:
    """Report thin buckets, long gaps and stalled words as dropout candidates."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("words_json")
    parser.add_argument("--variant", default=None)
    parser.add_argument("--bucket", type=float, default=30.0,
                        help="length of a time bucket in seconds")
    parser.add_argument("--min-words", type=int, default=45,
                        help="a bucket below this word count is reported; normal speech "
                             "runs well above it, a dropout falls far below")
    parser.add_argument("--gap", type=float, default=2.5,
                        help="silence between two words that is reported")
    parser.add_argument("--stall", type=float, default=3.0,
                        help="duration of a single word that is reported")
    args = parser.parse_args()

    words = load_words(args.words_json, args.variant)
    print(f"{len(words)} Woerter, {stamp(words[0]['start'])} - {stamp(words[-1]['end'])}")

    thin = sparse_buckets(words, args.bucket, args.min_words)
    gaps = [(words[i]["end"], words[i + 1]["start"] - words[i]["end"], i)
            for i in range(len(words) - 1)
            if words[i + 1]["start"] - words[i]["end"] > args.gap]
    # A word stamped as lasting several seconds is the decoder skipping over speech.
    stalls = [w for w in words if w["end"] - w["start"] > args.stall]

    if thin:
        print(f"\nDuenn besetzte Abschnitte (< {args.min_words} Woerter je "
              f"{args.bucket:.0f}s):")
        for start, count in thin:
            print(f"  {stamp(start)} - {stamp(start + args.bucket)} : {count} Woerter")
    if gaps:
        print(f"\nLuecken ueber {args.gap}s:")
        for end, gap, index in gaps:
            around = " ".join(w["text"] for w in words[max(0, index - 2):index + 3])
            print(f"  {stamp(end)} : {gap:.1f}s   ...{around}...")
    if stalls:
        print(f"\nWoerter ueber {args.stall}s Dauer:")
        for word in stalls:
            print(f"  {stamp(word['start'])} : {word['end'] - word['start']:.1f}s  "
                  f"{word['text']}")

    if thin or gaps or stalls:
        print("\nDiese Bereiche einzeln nachdekodieren (eigener Clip, --mode full "
              "--words) und mit patch_words.py einsetzen.")
        sys.exit(1)
    print("\nOK - keine Hinweise auf verschluckte Passagen.")


if __name__ == "__main__":
    main()
