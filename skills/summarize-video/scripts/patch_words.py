"""Splice re-decoded passages into a word timeline.

A dropout reported by `check_coverage.py` is repaired by cutting the affected range into
its own clip, decoding that clip with `transcribe.py --mode full --words`, and swapping
the result into the base timeline. The patch clip starts at zero, so its timestamps are
shifted by the offset it was cut at.

Choose the replaced range slightly wider than the dropout and put both edges inside a
speech pause - a seam in the middle of a word loses that word or duplicates it. The
script drops duplicates at the seam and keeps the timeline monotonic, but it cannot
invent a word that neither side contributed.

Usage:
    python patch_words.py words.json words_final.json \
        --patch g0/words.json 0 0 49.1 \
        --patch g1/words.json 1900 1905 1994 \
        --drop-after 2493
"""

import argparse
import json
import sys


def load_words(path: str, variant: str | None = None) -> list[dict]:
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
    clean = []
    for word in words:
        start, end = word.get("start"), word.get("end")
        if start is None:
            continue
        if end is None or end < start:
            end = start
        clean.append({"start": start, "end": end, "text": word["text"]})
    return clean


def dedupe_seam(words: list[dict], window: float) -> list[dict]:
    """Drop a word that both sides of a seam contributed."""
    out: list[dict] = []
    for word in words:
        previous = out[-1] if out else None
        if previous and previous["text"].lower() == word["text"].lower() \
                and word["start"] - previous["start"] < window:
            continue
        out.append(word)
    return out


def main() -> None:
    """Apply every patch, then normalise the resulting timeline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("words_json")
    parser.add_argument("output")
    parser.add_argument("--variant", default=None)
    parser.add_argument("--patch", nargs=4, action="append", default=[],
                        metavar=("JSON", "OFFSET", "FROM", "TO"),
                        help="patch file, the second it was cut at, and the absolute "
                             "range it replaces")
    parser.add_argument("--drop-after", type=float, default=None,
                        help="discard everything from this second on (trailing "
                             "hallucinated credits)")
    parser.add_argument("--seam-window", type=float, default=0.5,
                        help="two identical words closer than this count as one")
    args = parser.parse_args()

    words = load_words(args.words_json, args.variant)
    print(f"Basis: {len(words)} Woerter")

    for path, offset, low, high in args.patch:
        offset, low, high = float(offset), float(low), float(high)
        shifted = [{"start": w["start"] + offset, "end": w["end"] + offset,
                    "text": w["text"]} for w in load_words(path)]
        patch = [w for w in shifted if low <= w["start"] < high]
        if not patch:
            sys.exit(f"{path}: keine Woerter im Bereich {low}-{high}s - "
                     "Offset oder Bereich falsch?")
        removed = sum(1 for w in words if low <= w["start"] < high)
        words = [w for w in words if not low <= w["start"] < high] + patch
        print(f"{path}: {removed} Woerter ersetzt durch {len(patch)} "
              f"({low:.1f}-{high:.1f}s)")

    if args.drop_after is not None:
        before = len(words)
        words = [w for w in words if w["start"] < args.drop_after]
        print(f"Nach {args.drop_after:.1f}s verworfen: {before - len(words)} Woerter")

    words.sort(key=lambda w: (w["start"], w["end"]))
    words = dedupe_seam(words, args.seam_window)

    previous = 0.0
    for word in words:
        word["start"] = max(word["start"], previous)
        word["end"] = max(word["end"], word["start"])
        previous = word["start"]

    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump({"raw": words}, fh, ensure_ascii=False, indent=2)
    print(f"{len(words)} Woerter, Ende bei {words[-1]['end']:.1f}s -> {args.output}")
    print("Jetzt check_coverage.py erneut laufen lassen.")


if __name__ == "__main__":
    main()
