"""Group word-level timestamps into cue-sized units ready for translation.

Reads the JSON written by `transcribe.py --words` and cuts the word stream at sentence
ends, at clause boundaries once a unit gets long, and at speech pauses. The result is a
cue skeleton with accurate start/end times whose `text` still holds the original
language — replace each text with its German translation and feed it to build_srt.py.

Usage:
    python segment_cues.py words.json cues_src.json [--variant raw] [--max 6.0]
"""

import argparse
import json
import sys

SENTENCE_END = (".", "?", "!", "…")
CLAUSE_END = (",", ";", ":", "–", "-")


def flush(unit: list[dict]) -> dict:
    """Turn a list of word entries into one cue dictionary."""
    return {
        "start": round(unit[0]["start"], 2),
        "end": round(unit[-1]["end"], 2),
        "text": " ".join(w["text"].strip() for w in unit).strip(),
    }


def group(words: list[dict], soft_max: float, hard_max: float,
          pause: float) -> list[dict]:
    """Cut the word stream into units at sentence, clause and pause boundaries."""
    cues: list[dict] = []
    unit: list[dict] = []

    for index, word in enumerate(words):
        if word.get("start") is None or word.get("end") is None:
            continue
        unit.append(word)
        text = word["text"].strip()
        elapsed = unit[-1]["end"] - unit[0]["start"]
        following = words[index + 1] if index + 1 < len(words) else None
        gap = (following["start"] - word["end"]) if following and following.get("start") else 0.0

        ends_sentence = text.endswith(SENTENCE_END)
        ends_clause = text.endswith(CLAUSE_END)
        # A long silence is a natural cut even mid-sentence.
        long_pause = gap >= pause

        if ends_sentence or long_pause or (ends_clause and elapsed >= soft_max) \
                or elapsed >= hard_max:
            cues.append(flush(unit))
            unit = []

    if unit:
        cues.append(flush(unit))
    return cues


def main() -> None:
    """Read word timings, group them and write a cue skeleton."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("words_json")
    parser.add_argument("output")
    parser.add_argument("--variant", default=None,
                        help="which variant key to read (default: the first one)")
    parser.add_argument("--max", dest="soft_max", type=float, default=4.0,
                        help="from this length on, split at clause boundaries")
    parser.add_argument("--hard-max", type=float, default=7.0,
                        help="never let a unit grow past this")
    parser.add_argument("--pause", type=float, default=0.7,
                        help="gap between words that forces a cut")
    args = parser.parse_args()

    with open(args.words_json, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        key = args.variant or next(iter(data))
        if key not in data:
            sys.exit(f"Variante {key!r} nicht in {args.words_json}. "
                     f"Vorhanden: {', '.join(data)}")
        words = data[key]
    else:
        words = data
    if not words:
        sys.exit("Keine Wortzeiten gefunden.")

    cues = group(words, args.soft_max, args.hard_max, args.pause)
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(cues, fh, ensure_ascii=False, indent=2)

    longest = max(c["end"] - c["start"] for c in cues)
    print(f"{len(cues)} Cue-Einheiten geschrieben nach {args.output}")
    print(f"Laengste Einheit: {longest:.1f}s, letzte endet bei {cues[-1]['end']:.1f}s")
    print("Jetzt jeden 'text' durch die deutsche Uebersetzung ersetzen, "
          "dann build_srt.py aufrufen.")


if __name__ == "__main__":
    main()
