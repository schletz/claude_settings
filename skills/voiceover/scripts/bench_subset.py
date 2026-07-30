"""Build a speaker-balanced cue subset for the intelligibility check.

synth_samples.py --count samples by index position across the whole file. When a
voice occupies a narrow index range — a played video insert does — that voice can
draw zero samples, and a reference clip that clones badly then goes unmeasured,
which is the one failure the rest of the pipeline cannot see.

This picks a fixed number of units per speaker instead, shortest first, because
short units are where a clone falls apart: with little context F5-TTS can run past
the text or loop a syllable.

Units with no text are skipped. An empty cue is a passage left untranslated on
purpose, and "shortest first" would otherwise pick every one of them before any
real unit — the synthesiser then returns nothing at all and the run dies inside
the resampler, several minutes after the mistake was made.

Writes <out>_cues.json and <out>_speakers.json, whose labels array is aligned to the
subset, so both feed synth_samples.py unchanged.

Usage:
    python bench_subset.py cues_vo.json refs/speakers.json <workdir>/bench \
        --per-speaker 10
"""

import argparse
import json
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cues")
    parser.add_argument("speakers")
    parser.add_argument("out", help="path prefix for the two output files")
    parser.add_argument("--per-speaker", type=int, default=10)
    parser.add_argument("--only", type=int, nargs="*",
                        help="use exactly these cue indices instead of sampling")
    args = parser.parse_args()

    with open(args.cues, encoding="utf-8") as handle:
        cues = json.load(handle)
    with open(args.speakers, encoding="utf-8") as handle:
        data = json.load(handle)
    labels = data["labels"]

    if args.only:
        chosen = sorted(set(args.only))
    else:
        groups: dict[int, list[int]] = {}
        for index, speaker in enumerate(labels):
            if not cues[index]["text"].strip():
                continue
            groups.setdefault(speaker, []).append(index)

        chosen = []
        for speaker in sorted(groups):
            indices = groups[speaker]
            by_length = sorted(indices, key=lambda i: len(cues[i]["text"]))
            half = max(args.per_speaker // 2, 1)
            picked = by_length[:half]
            step = max(len(indices) // max(args.per_speaker - half, 1), 1)
            picked += [i for i in indices[::step] if i not in picked][
                :args.per_speaker - half]
            chosen += picked
        chosen = sorted(set(chosen))

    subset = [cues[i] for i in chosen]
    with open(f"{args.out}_cues.json", "w", encoding="utf-8") as handle:
        json.dump(subset, handle, ensure_ascii=False, indent=1)
    with open(f"{args.out}_speakers.json", "w", encoding="utf-8") as handle:
        json.dump({"speakers": data["speakers"],
                   "labels": [labels[i] for i in chosen]},
                  handle, ensure_ascii=False, indent=1)

    names = {e["speaker"]: e.get("name", "") for e in data["speakers"]}
    counts: dict[int, int] = {}
    for index in chosen:
        counts[labels[index]] = counts.get(labels[index], 0) + 1
    print(f"{len(subset)} Einheiten -> {args.out}_cues.json")
    for speaker in sorted(counts):
        print(f"  Sprecher {speaker} {names.get(speaker, ''):18s} {counts[speaker]}")
    print("\nPosition im Bench -> Einheit:")
    for position, index in enumerate(chosen):
        print(f"  {position:3d} -> {index}")


if __name__ == "__main__":
    sys.exit(main())
