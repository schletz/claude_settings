"""Cut word timings into speech-sized units for a voice-over translation.

Reading-sized cues are the wrong translation unit for dubbing: they break
mid-clause, so the translator cannot reorder a sentence and the synthesiser gets
chopped prosody. This cuts on the speaker's own pauses and sentence ends instead,
producing units that can be rendered as whole German sentences.

Each unit carries the slot reaching to the start of the next one — the pause
after a sentence is usable speaking time — and a character budget derived from
the measured speaking rate of the target voice.

Two ways of splitting an over-long run were tried and are wrong:

  cutting at the word where the cap is reached lands mid-clause, which is exactly
  what makes a unit untranslatable;
  cutting at the widest pause anywhere in the run leaves stubs, because the widest
  pause often sits right next to an edge. On a 50-minute interview that produced
  556 units, 171 of them under two seconds.

Searching only the middle half of the run fixes both: 421 units, median slot 6.6s,
25 under two seconds.

Usage:
    python segment_speech.py <words.json> <units.json> --rate 16.6 --duration 3028.9
"""

import argparse
import json

# A pause at least this long ends a unit even mid-sentence.
PAUSE_BREAK = 0.45
# Units shorter than this are not closed yet; longer than this are force-split.
MIN_UNIT = 1.2
MAX_UNIT = 15.0
SENTENCE_END = (".", "!", "?")

# Share of the slot the German text may claim, leaving room for the pause.
BUDGET_SHARE = 0.92

# Key holding a unit's source-language text. Named for its role, not for a
# language: an earlier version hardcoded "hu", which left English material
# sitting under a Hungarian key and misled every reader of the file.
TEXT_KEY = "text"
LEGACY_TEXT_KEY = "hu"


def unit_text(unit: dict) -> str:
    """Read a unit's source text, tolerating files written before TEXT_KEY."""
    if TEXT_KEY in unit:
        return unit[TEXT_KEY]
    return unit[LEGACY_TEXT_KEY]


def _split_at_widest_gap(run: list[dict]) -> list[list[dict]]:
    """Halve an over-long run at the widest pause in its middle, recursively."""
    span = run[-1]["end"] - run[0]["start"]
    if span <= MAX_UNIT or len(run) < 6:
        return [run]

    low, high = len(run) // 4, (3 * len(run)) // 4
    best, widest = None, -1.0
    for index in range(max(low, 1), max(high, 2)):
        gap = run[index + 1]["start"] - run[index]["end"]
        if gap > widest:
            best, widest = index, gap
    if best is None:
        return [run]
    return (_split_at_widest_gap(run[:best + 1])
            + _split_at_widest_gap(run[best + 1:]))


def cut(words: list[dict]) -> list[dict]:
    """Group words into units at sentence ends and pauses."""
    runs: list[list[dict]] = []
    buffer: list[dict] = []

    for index, word in enumerate(words):
        buffer.append(word)
        is_last = index == len(words) - 1
        gap = 0.0 if is_last else words[index + 1]["start"] - word["end"]
        span = word["end"] - buffer[0]["start"]
        closes = word["text"].rstrip().endswith(SENTENCE_END)
        if is_last or (closes and span >= MIN_UNIT) or (
                gap > PAUSE_BREAK and span >= MIN_UNIT):
            runs.append(buffer)
            buffer = []
    if buffer:
        runs.append(buffer)

    units: list[dict] = []
    for run in runs:
        for piece in _split_at_widest_gap(run):
            units.append({
                "start": round(piece[0]["start"], 2),
                "end": round(piece[-1]["end"], 2),
                TEXT_KEY: " ".join(w["text"] for w in piece),
            })
    return units


def add_budgets(units: list[dict], rates: list[float], duration: float) -> None:
    """Annotate each unit with its slot and the character budget it implies."""
    for index, unit in enumerate(units):
        slot_end = (units[index + 1]["start"] if index + 1 < len(units)
                    else duration)
        slot = max(slot_end - unit["start"], 0.6)
        unit["slot"] = round(slot, 2)
        unit["budget"] = int(slot * rates[index] * BUDGET_SHARE)


def per_unit_rates(count: int, fallback: float, speakers: str | None) -> list[float]:
    """One rate per unit — cloned voices differ in speed, so budgets must too.

    A slow speaker given a fast speaker's budget produces a translation that only
    fits when it is rushed. Measured on one interview: 12.9 against 16.0
    characters/second between guest and host, a fifth of the budget.
    """
    if not speakers:
        return [fallback] * count
    with open(speakers, encoding="utf-8") as handle:
        data = json.load(handle)
    rates = {entry["speaker"]: entry.get("rate") for entry in data["speakers"]}
    missing = [key for key, value in rates.items() if not value]
    if missing:
        raise SystemExit(f"speakers.json kennt keine Rate fuer Sprecher {missing}. "
                         f"Erst measure_rate.py --speakers ... --update laufen lassen.")
    labels = data["labels"]
    if len(labels) != count:
        raise SystemExit(f"speakers.json passt nicht: {len(labels)} Zuordnungen "
                         f"gegen {count} Einheiten. Die Schnittpunkte haben sich "
                         f"geaendert - diarize.py erneut laufen lassen.")
    return [rates[label] for label in labels]


def main() -> None:
    """Cut, annotate, write and report the distribution."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("words")
    parser.add_argument("out")
    parser.add_argument("--rate", type=float, required=True,
                        help="speaking rate, characters/second; fallback when "
                             "--speakers is not given")
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--speakers",
                        help="speakers.json with a measured rate per speaker")
    parser.add_argument("--variant", default="raw",
                        help="which variant inside words.json to read")
    args = parser.parse_args()

    with open(args.words, encoding="utf-8") as handle:
        data = json.load(handle)
    words = data[args.variant] if isinstance(data, dict) else data

    units = cut(words)
    rates = per_unit_rates(len(units), args.rate, args.speakers)
    add_budgets(units, rates, args.duration)

    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(units, handle, ensure_ascii=False, indent=1)

    slots = sorted(u["slot"] for u in units)
    tight = sum(1 for u in units if u["slot"] < 2.0)
    print(f"{len(words)} Woerter -> {len(units)} Sprech-Einheiten")
    print(f"Slot min/median/max: {slots[0]:.1f} / "
          f"{slots[len(slots) // 2]:.1f} / {slots[-1]:.1f}s")
    print(f"Einheiten unter 2s Slot: {tight}")
    print(f"Zeichenbudget gesamt: {sum(u['budget'] for u in units)}")
    if tight > len(units) // 8:
        print("WARNUNG: viele sehr kurze Einheiten - PAUSE_BREAK erhoehen "
              "oder MIN_UNIT anheben.")


if __name__ == "__main__":
    main()
