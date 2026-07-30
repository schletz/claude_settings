"""Check a voice-over translation against the rules the synthesiser depends on.

Anything a rule-based phonemiser reads out literally, or reads wrongly, has to be
gone before synthesis: digits, ellipses, bracketed editor's notes, abbreviations.
On top of that every unit has to fit the speaking time it was budgeted for, and
the index set has to be complete — a missing index silently shifts the whole
track against the picture, and nothing downstream would notice.

Merges the numbered translation files and writes the cue JSON once everything
passes. Length corrections go into a separate --override file so the main
translation stays untouched and reviewable.

Usage:
    python validate_vo.py <units.json> <cues_vo.json> vo_*.txt --override vo_fix.txt
"""

import argparse
import json
import re
import sys

# Patterns that must not survive into the synthesis input, with the reason.
FORBIDDEN = [
    (re.compile(r"\d"), "Ziffer, muss ausgeschrieben sein"),
    (re.compile(r"\.\.\.|…"), "Auslassungspunkte"),
    (re.compile(r"[\[\]]"), "eckige Klammer"),
    (re.compile(r"\bz\.\s*B\.|\bbzw\.|\bca\.|\bu\.\s*a\.|\bd\.\s*h\.|\bevtl\."),
     "Abkürzung"),
    (re.compile(r"[%&@#*_<>|]"), "Sonderzeichen"),
    (re.compile(r"\s/\s|\w/\w"), "Schrägstrich"),
]

# A unit may exceed its budget by this share before it is reported.
TOLERANCE = 1.06


def _entries(path: str, problems: list[str]):
    """Yield (line number, index, text) for one pipe-separated file."""
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            index, _, text = line.partition("|")
            if not index.strip().isdigit():
                problems.append(f"{path}:{number}: kein Index")
                continue
            yield number, int(index), text.strip()


def load_translations(paths: list[str], overrides: list[str]
                      ) -> tuple[dict[int, str], list[str]]:
    """Read the translation files, then apply the override files.

    A repeated index inside the translation set is an accident and is reported.
    An override entry replacing a translation is the point of the file, but a
    second override for the same index is an accident again: the later line
    wins silently, and that is as likely to be the discarded fix as the wanted
    one. Both cases are therefore reported.
    """
    texts: dict[int, str] = {}
    problems: list[str] = []
    for path in paths:
        for number, index, text in _entries(path, problems):
            if index in texts:
                problems.append(f"{path}:{number}: Index {index} doppelt")
            texts[index] = text
    overridden: dict[int, str] = {}
    for path in overrides:
        for number, index, text in _entries(path, problems):
            if index not in texts:
                problems.append(f"{path}:{number}: Index {index} ersetzt nichts")
            if index in overridden:
                problems.append(f"{path}:{number}: Index {index} doppelt "
                                f"ueberschrieben (zuerst in {overridden[index]})")
            overridden[index] = f"{path}:{number}"
            texts[index] = text
    return texts, problems


def check_units(units: list[dict], texts: dict[int, str], problems: list[str]
                ) -> list[tuple[int, int, int]]:
    """Apply the forbidden patterns and collect over-budget units."""
    over: list[tuple[int, int, int]] = []
    for index, unit in enumerate(units):
        text = texts.get(index)
        if not text:
            continue
        stamp = f"{int(unit['start']) // 60:02d}:{int(unit['start']) % 60:02d}"
        for pattern, reason in FORBIDDEN:
            found = pattern.search(text)
            if found:
                problems.append(
                    f"Einheit {index} ({stamp}): {reason} -> {found.group(0)!r}")
        if len(text) > unit["budget"] * TOLERANCE:
            over.append((index, len(text), unit["budget"]))
    return over


def main() -> None:
    """Validate, then write the cue file if the translation is clean."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("units")
    parser.add_argument("out")
    parser.add_argument("translations", nargs="+")
    parser.add_argument("--override", nargs="*", default=[],
                        help="files whose entries replace earlier ones")
    args = parser.parse_args()

    with open(args.units, encoding="utf-8") as handle:
        units = json.load(handle)
    texts, problems = load_translations(args.translations, args.override)

    missing = [i for i in range(len(units)) if i not in texts]
    extra = [i for i in texts if i >= len(units)]
    if missing:
        problems.append(f"fehlende Indizes: {missing}")
    if extra:
        problems.append(f"ueberzaehlige Indizes: {extra}")

    over = check_units(units, texts, problems)

    print(f"{len(units)} Einheiten, {len(texts)} uebersetzt")
    if over:
        print(f"\nUeber Budget ({len(over)}), die groessten Ueberhaenge:")
        for index, length, budget in sorted(over, key=lambda o: o[1] / o[2],
                                            reverse=True)[:15]:
            unit = units[index]
            stamp = f"{int(unit['start']) // 60:02d}:{int(unit['start']) % 60:02d}"
            print(f"  {index:3d} {stamp}  {length} Zeichen bei Budget {budget}"
                  f"  ({length / budget:.2f}x)")
        print("Bis etwa 1.25x faengt die Stauchung das ab, darueber kuerzen.")

    if problems:
        print(f"\nFEHLER ({len(problems)}):")
        for problem in problems[:40]:
            print(f"  {problem}")
        sys.exit(1)

    cues = [{"start": u["start"], "end": u["end"], "text": texts[i]}
            for i, u in enumerate(units)]
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(cues, handle, ensure_ascii=False, indent=1)
    print(f"\nOK - geschrieben nach {args.out}")


if __name__ == "__main__":
    main()
