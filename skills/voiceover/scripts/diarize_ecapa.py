"""Split speakers from ECAPA embeddings and write speakers.json for the pipeline.

Stage two of the two-stage speaker split, and a drop-in replacement for diarize.py
when several people share a room and a microphone type. Output schema is identical,
so measure_rate.py, segment_speech.py and build_voiceover.py consume it unchanged.

Three things this does that blind clustering cannot:

  it clusters speaker-verification embeddings, not MFCC statistics. On a four-person
  panel the MFCC route merged the two female voices (silhouette 0.19); this kept them
  apart;
  it pins played video inserts by index. Those are not panellists and must not inherit
  a panellist's cloned voice. Their boundaries are certain because the host announces
  every insert, so they are given rather than guessed;
  it scores the result against anchors taken from the dialogue — who is called on by
  name, who answers, who refers to whom in the third person. That turns "check the
  assignment" into a number, and lets several clustering methods be compared.

Structure file (optional, both keys optional):

    {"inserts": [[20, 37, "Magyar Peter"]],
     "anchors": {"Dorottya": [0, 1, 47], "Tamas": [49, 51]}}

Usage:
    python diarize_ecapa.py <media> units.json emb.npy <outdir> --speakers 4 \
        --structure structure.json
"""

import argparse
import json
import os
import subprocess
import sys

import numpy as np

from segment_speech import unit_text

REF_MIN = 4.0        # shorter references make the clone unstable
REF_MAX = 11.0       # F5-TTS truncates anything past ~12 s anyway
REF_RATE = 24000     # what F5-TTS resamples to internally
GOOD_PURITY = 0.95


def fit(matrix: np.ndarray, method: str, count: int) -> np.ndarray:
    """Cluster the panel embeddings with one named method."""
    from sklearn.cluster import AgglomerativeClustering, KMeans

    if method == "kmeans":
        # On L2-normalised rows this is spherical k-means: cosine geometry without
        # agglomerative clustering's chaining, which collapsed everything into one
        # cluster on tightly packed embeddings.
        return KMeans(n_clusters=count, n_init=50,
                      random_state=0).fit_predict(matrix)
    if method == "ward":
        return AgglomerativeClustering(n_clusters=count,
                                       linkage="ward").fit_predict(matrix)
    return AgglomerativeClustering(n_clusters=count, metric="cosine",
                                   linkage=method).fit_predict(matrix)


def purity(assignment: dict[int, str], anchors: dict[str, list[int]]
           ) -> tuple[float, dict[str, str]]:
    """Share of anchor units landing in their speaker's dominant cluster."""
    mapping: dict[str, str] = {}
    claimed: set[str] = set()
    hits = total = 0
    for name, indices in anchors.items():
        counts: dict[str, int] = {}
        for index in indices:
            key = assignment[index]
            counts[key] = counts.get(key, 0) + 1
        best, count = max(counts.items(), key=lambda kv: kv[1])
        # A cluster may stand for only one speaker; a second claimant scores zero.
        if best in claimed:
            count = 0
        else:
            claimed.add(best)
            mapping[best] = name
        hits += count
        total += len(indices)
    return (hits / total if total else 0.0), mapping


def cut_reference(media: str, unit: dict, target: str) -> None:
    """Cut one unit out of the source as a 24 kHz mono reference clip."""
    end = min(unit["end"], unit["start"] + REF_MAX)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", media,
         "-ss", f"{unit['start']:.2f}", "-to", f"{end:.2f}",
         "-vn", "-ac", "1", "-ar", str(REF_RATE), target], check=True)


def pick_reference(units: list[dict], indices: list[int],
                   embeddings: np.ndarray) -> int:
    """Pick the most typical unit of the right length to clone this voice from."""
    centre = embeddings[indices].mean(axis=0)
    usable = [i for i in indices
              if REF_MIN <= units[i]["end"] - units[i]["start"] <= REF_MAX]
    pool = usable or indices
    return min(pool, key=lambda i: float(np.linalg.norm(embeddings[i] - centre)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media")
    parser.add_argument("units")
    parser.add_argument("embeddings")
    parser.add_argument("outdir")
    parser.add_argument("--speakers", type=int, required=True,
                        help="number of people in the room, inserts excluded")
    parser.add_argument("--structure", help="JSON with 'inserts' and 'anchors'")
    parser.add_argument("--text-key",
                        help="override the key holding the source text in "
                             "units.json; normally detected automatically")
    args = parser.parse_args()

    with open(args.units, encoding="utf-8") as handle:
        units = json.load(handle)
    embeddings = np.load(args.embeddings)
    if len(embeddings) != len(units):
        raise SystemExit(f"emb.npy passt nicht: {len(embeddings)} Zeilen "
                         f"gegen {len(units)} Einheiten.")

    structure = {}
    if args.structure:
        with open(args.structure, encoding="utf-8") as handle:
            structure = json.load(handle)
    inserts = [tuple(row) for row in structure.get("inserts", [])]
    anchors = {k: list(v) for k, v in structure.get("anchors", {}).items()}

    def insert_of(index: int) -> str | None:
        for first, last, label in inserts:
            if first <= index <= last:
                return label
        return None

    panel = [i for i in range(len(units)) if insert_of(i) is None]
    matrix = embeddings[panel]

    best = (-1.0, None, None)
    for method in ("kmeans", "ward", "complete", "average"):
        trial = fit(matrix, method, args.speakers)
        candidate = {index: f"P{trial[pos]}" for pos, index in enumerate(panel)}
        score = purity(candidate, anchors)[0] if anchors else 0.0
        if anchors:
            print(f"  {method:9s} Ankertreue {score:.3f}")
        if score > best[0] or best[1] is None:
            best = (score, method, trial)
    score, method, labels = best
    if anchors:
        print(f"\nGewaehlt: {method} (Ankertreue {score:.3f})")
        if score < GOOD_PURITY:
            print("  WARNUNG: die Anker sitzen nicht sauber in eigenen Clustern.\n"
                  "  Mehr Anker setzen oder die Sprecherzahl pruefen, bevor du "
                  "synthetisierst.")
    else:
        print(f"Gewaehlt: {method} (keine Anker angegeben - ungeprueft!)")

    assignment = {index: f"P{labels[pos]}" for pos, index in enumerate(panel)}
    for index in range(len(units)):
        if (label := insert_of(index)) is not None:
            assignment[index] = label

    mapping = purity(assignment, anchors)[1] if anchors else {}
    named = {index: mapping.get(key, key) for index, key in assignment.items()}

    groups: dict[str, list[int]] = {}
    for index, name in named.items():
        groups.setdefault(name, []).append(index)
    # Stable order: most speech first, so index 0 is the busiest voice.
    order = sorted(groups, key=lambda n: -sum(units[i]["end"] - units[i]["start"]
                                              for i in groups[n]))

    os.makedirs(args.outdir, exist_ok=True)
    entries, speaker_labels = [], [0] * len(units)
    print()
    for number, name in enumerate(order):
        indices = sorted(groups[name])
        chosen = pick_reference(units, indices, embeddings)
        target = os.path.join(args.outdir, f"spk{number}.wav")
        cut_reference(args.media, units[chosen], target)
        for index in indices:
            speaker_labels[index] = number

        seconds = sum(units[i]["end"] - units[i]["start"] for i in indices)
        entries.append({"speaker": number, "name": name, "ref_file": target,
                        "ref_text": (units[chosen][args.text_key] if args.text_key
                                     else unit_text(units[chosen])),
                        "ref_unit": chosen, "units": len(indices),
                        "seconds": round(seconds, 1)})
        start = units[chosen]["start"]
        print(f"  {number}  {name:18s} {len(indices):4d} Einheiten "
              f"{seconds / 60:5.1f} min | Referenz Einheit {chosen} aus "
              f"{int(start) // 60:02d}:{int(start) % 60:02d}")

    path = os.path.join(args.outdir, "speakers.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"speakers": entries, "labels": speaker_labels},
                  handle, ensure_ascii=False, indent=1)
    print(f"\nGeschrieben: {path}")


if __name__ == "__main__":
    sys.exit(main())
