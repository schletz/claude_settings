"""Recognise speakers of this video in the stored voice library.

Runs straight after diarize_ecapa.py and before any clip is judged or any rate
measured. For every cluster it compares the ECAPA centroid against every stored
voice; a hit replaces the freshly cut clip with the stored one and carries its
measured rate along, so the person sounds the same as in every earlier video and
measure_rate.py has nothing left to do for them.

Nothing is applied silently. Without --apply the script only reports; with --apply
it takes the certain hits and leaves the doubtful ones to --accept. The thresholds
lean towards matching rather than away from it — see voice_library.py for why a
false match costs less here than a missed one — with a single hard rule against
two speakers of one video landing on the same voice.

Usage:
    python match_voices.py units.json emb.npy refs/speakers.json
    python match_voices.py units.json emb.npy refs/speakers.json --apply
    python match_voices.py units.json emb.npy refs/speakers.json --apply \
        --accept 1=kiraly-tamas
"""

import argparse
import json
import sys

import numpy as np

import voice_library as lib


def rank(centre: np.ndarray, voices: list[dict]) -> list[tuple[float, dict]]:
    """All stored voices, most similar first."""
    scored = [(float(centre @ lib.embedding_of(voice)), voice) for voice in voices]
    return sorted(scored, key=lambda pair: -pair[0])


def resolve_collisions(decisions: list) -> tuple[list, list]:
    """Let at most one speaker per video claim any one stored voice.

    This is the single place where a wrong match really hurts. Giving someone
    another person's voice is tolerable — the clone never sounded like them
    anyway. Giving *two* speakers of the same video the same voice is not: they
    become indistinguishable, and telling speakers apart is the reason this
    pipeline clones at all. The higher score wins; the loser falls back to the
    clip cut from the video, which is exactly what would have happened without
    a library.

    A hand-confirmed match via --accept outranks any computed score.
    """
    best: dict[str, tuple] = {}
    dropped = []
    for decision in sorted(decisions,
                           key=lambda d: (d[3], d[2]), reverse=True):
        voice_id = decision[1]["id"]
        if voice_id in best:
            dropped.append((decision[0], decision[1], decision[2]))
        else:
            best[voice_id] = decision
    keep = [d for d in decisions if best.get(d[1]["id"]) is d]
    return keep, dropped


def apply_voice(entry: dict, voice: dict, library: str) -> None:
    """Point one speakers.json entry at a stored voice."""
    entry["ref_file"] = lib.clip_path(library, voice)
    entry["ref_text"] = voice["ref_text"]
    entry["voice_id"] = voice["id"]
    if voice.get("rate"):
        entry["rate"] = voice["rate"]
    entry.pop("ref_unit", None)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("units")
    parser.add_argument("embeddings")
    parser.add_argument("speakers", help="refs/speakers.json from the diarisation")
    parser.add_argument("--library", default=lib.default_dir())
    parser.add_argument("--apply", action="store_true",
                        help="write certain hits into speakers.json")
    parser.add_argument("--accept", action="append", default=[],
                        metavar="SPK=ID",
                        help="confirm a doubtful hit by hand, repeatable")
    parser.add_argument("--min-units", type=int, default=3,
                        help="clusters below this are too thin to match on")
    args = parser.parse_args()

    index = lib.load(args.library)
    voices = index.get("voices", [])
    if not voices:
        print(f"Das Archiv {args.library} ist leer - nichts zu vergleichen.")
        print("Referenzclips wie bisher aus dem Video schneiden.")
        return

    with open(args.units, encoding="utf-8") as handle:
        units = json.load(handle)
    embeddings = np.load(args.embeddings)
    with open(args.speakers, encoding="utf-8") as handle:
        data = json.load(handle)
    if len(embeddings) != len(units):
        raise SystemExit(f"emb.npy passt nicht: {len(embeddings)} Zeilen gegen "
                         f"{len(units)} Einheiten.")

    labels = data["labels"]
    forced = dict(pair.split("=", 1) for pair in args.accept)

    print(f"{lib.count(len(voices))} in {args.library}\n")
    decisions: list[tuple[dict, dict, float, bool]] = []

    for entry in data["speakers"]:
        number = entry["speaker"]
        indices = [i for i, label in enumerate(labels) if label == number]
        name = entry.get("name", f"P{number}")
        if len(indices) < args.min_units:
            print(f"  {number}  {name:20s} nur {len(indices)} Einheiten - "
                  f"uebersprungen")
            continue

        centre = lib.centroid(embeddings, indices)
        scored = rank(centre, voices)
        score, best = scored[0]
        runner = f", zweitbeste {scored[1][0]:.2f} ({scored[1][1]['id']})" \
            if len(scored) > 1 else ""

        wanted = forced.get(str(number))
        if wanted:
            chosen = next((v for v in voices if v["id"] == wanted), None)
            if chosen is None:
                raise SystemExit(f"--accept {number}={wanted}: unbekannte Stimme.")
            hit = float(centre @ lib.embedding_of(chosen))
            print(f"  {number}  {name:20s} -> {chosen['id']} "
                  f"(bestaetigt, {hit:.2f})")
            decisions.append((entry, chosen, hit, True))
            continue

        if score >= lib.MATCH_SURE:
            print(f"  {number}  {name:20s} -> {best['id']:22s} {score:.2f}{runner}")
            decisions.append((entry, best, score, False))
        elif score >= lib.MATCH_MAYBE:
            print(f"  {number}  {name:20s} ?  {best['id']:22s} {score:.2f}{runner}")
            print(f"       unsicher, vorerst nicht uebernommen. Nennt das "
                  f"Transkript den Namen, oder gibt\n       check_refs.py fuer "
                  f"diesen Sprecher keinen brauchbaren Clip her? Dann\n       "
                  f"--accept {number}={best['id']}")
        else:
            print(f"  {number}  {name:20s} neu (beste Aehnlichkeit {score:.2f} "
                  f"zu {best['id']})")

    decisions, dropped = resolve_collisions(decisions)
    for entry, voice, score in dropped:
        print(f"\n  Sprecher {entry['speaker']} bekommt {voice['id']} NICHT "
              f"({score:.2f}) - die Stimme ist\n  schon an einen Sprecher mit "
              f"hoeherer Aehnlichkeit vergeben. Zwei Sprecher desselben\n  Videos "
              f"duerfen nicht dieselbe Stimme bekommen, sonst sind sie nicht mehr "
              f"zu\n  unterscheiden. Fuer diesen Sprecher gilt der Clip aus dem "
              f"Video.")

    if not args.apply:
        print("\nOhne --apply wurde nichts geschrieben.")
        return
    if not decisions:
        print("\nKeine Treffer zum Uebernehmen.")
        return

    for entry, voice, _, _ in decisions:
        apply_voice(entry, voice, args.library)
    with open(args.speakers, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=1)

    print(f"\n{lib.count(len(decisions))} aus dem Archiv in "
          f"{args.speakers} eingetragen.")
    without = [e["speaker"] for e in data["speakers"] if not e.get("voice_id")]
    if without:
        print(f"Ohne Archivstimme: {without} - fuer diese den Referenzclip "
              f"wie gewohnt\npruefen (check_refs.py) und die Rate messen "
              f"(measure_rate.py --only-missing).")
    else:
        print("Alle Sprecher kommen aus dem Archiv - measure_rate.py "
              "entfaellt.")


if __name__ == "__main__":
    sys.exit(main())
