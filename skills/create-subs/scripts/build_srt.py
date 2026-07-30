"""Build a normalised SubRip file from a JSON cue list.

Input is a JSON array of objects with "start" and "end" in seconds and "text".
The script wraps text onto at most two lines, enforces minimum and maximum display
durations, removes overlaps and renumbers, so the result passes check_srt.py.

Usage:
    python build_srt.py cues.json output.de.srt [--max-chars 45] [--min 1.2] [--max 8.0]
"""

import argparse
import json
import sys


def wrap(text: str, max_chars: int) -> tuple[str, bool]:
    """Wrap text onto two balanced lines without splitting words.

    Returns (wrapped text, overflow). Text is never truncated: if it does not fit
    two lines of max_chars, it is still emitted in full and overflow is True so the
    caller can ask for the cue to be split.
    """
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text, False

    words = text.split()
    if len(words) == 1:
        # A single over-long word cannot be broken without splitting it.
        return text, True

    def best_split(require_fit: bool) -> tuple[str, str] | None:
        """Pick the word boundary that balances both lines best."""
        best, best_cost = None, None
        for index in range(1, len(words)):
            first = " ".join(words[:index])
            second = " ".join(words[index:])
            if require_fit and (len(first) > max_chars or len(second) > max_chars):
                continue
            cost = abs(len(first) - len(second))
            if best_cost is None or cost < best_cost:
                best, best_cost = (first, second), cost
        return best

    fitting = best_split(require_fit=True)
    if fitting:
        return "\n".join(fitting), False

    # Too long for two lines: keep every word, report the overflow.
    balanced = best_split(require_fit=False)
    return "\n".join(balanced), True


def timecode(seconds: float) -> str:
    """Format seconds as an SRT timecode HH:MM:SS,mmm."""
    if seconds < 0:
        seconds = 0.0
    total_ms = int(round(seconds * 1000))
    hours, rest = divmod(total_ms, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, ms = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def normalise(cues: list[dict], min_dur: float, max_dur: float,
              gap: float) -> list[dict]:
    """Sort cues, clamp durations and push overlapping starts apart."""
    ordered = sorted((c for c in cues if c.get("text", "").strip()),
                     key=lambda c: float(c["start"]))
    result = []
    previous_end = -1.0
    for cue in ordered:
        start = max(float(cue["start"]), previous_end + gap)
        end = float(cue.get("end", start + min_dur))
        if end - start < min_dur:
            end = start + min_dur
        if end - start > max_dur:
            end = start + max_dur
        # A cue pushed past its successor's start would reorder the list; drop instead.
        if end <= start:
            continue
        result.append({"start": start, "end": end, "text": cue["text"].strip()})
        previous_end = end
    return result


def main() -> None:
    """Read the cue list, normalise it and write a SubRip file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cues_json")
    parser.add_argument("output")
    parser.add_argument("--max-chars", type=int, default=45)
    parser.add_argument("--min", dest="min_dur", type=float, default=1.2)
    parser.add_argument("--max", dest="max_dur", type=float, default=8.0)
    parser.add_argument("--gap", type=float, default=0.08,
                        help="minimum gap between consecutive cues in seconds")
    args = parser.parse_args()

    with open(args.cues_json, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        data = data.get("cues", [])
    if not isinstance(data, list) or not data:
        sys.exit("Erwartet wird eine nicht-leere JSON-Liste mit start/end/text.")

    cues = normalise(data, args.min_dur, args.max_dur, args.gap)

    overflowing = []
    with open(args.output, "w", encoding="utf-8", newline="\n") as fh:
        for index, cue in enumerate(cues, start=1):
            text, overflow = wrap(cue["text"], args.max_chars)
            if overflow:
                overflowing.append((index, cue["start"]))
            fh.write(f"{index}\n")
            fh.write(f"{timecode(cue['start'])} --> {timecode(cue['end'])}\n")
            fh.write(text + "\n\n")

    dropped = len(data) - len(cues)
    print(f"{len(cues)} Cues geschrieben nach {args.output}"
          + (f" ({dropped} leer/ungueltig verworfen)" if dropped else ""))
    print(f"Letzter Cue endet bei {cues[-1]['end']:.1f}s")
    if overflowing:
        print(f"\nWARNUNG: {len(overflowing)} Cue(s) passen nicht in zwei Zeilen a "
              f"{args.max_chars} Zeichen. Der Text wurde vollstaendig geschrieben, "
              f"ist aber zu lang zum Lesen - bitte inhaltlich aufteilen:")
        for index, start in overflowing:
            print(f"  Cue {index} bei {int(start)//60:02d}:{int(start)%60:02d}")
    print("\nJetzt pruefen: python check_srt.py "
          f"\"{args.output}\" --media-duration <sek>")


if __name__ == "__main__":
    main()
