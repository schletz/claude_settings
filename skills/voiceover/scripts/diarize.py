"""Group speech units by speaker and cut one reference clip per speaker.

F5-TTS clones a voice from a few seconds of reference audio. With one reference for
the whole file every speaker in an interview gets the same German voice, and the
listener loses track of who is talking. This script assigns each unit to a speaker
and cuts the reference clips the synthesis step needs.

The features are deliberately plain — MFCC, spectral shape and pitch statistics,
clustered with k-means. That is weaker than a trained speaker-embedding model, but
it needs no extra download, no gated weights and no token, and the case it has to
solve is usually easy: a studio host against a guest on a video call differs in
bandwidth and noise floor, not just in timbre. Check the reported separation before
you trust it.

Usage:
    python diarize.py <media> units.json <outdir>
    python diarize.py <media> units.json <outdir> --speakers 2
"""

import argparse
import json
import os
import subprocess
import sys

import numpy as np

from segment_speech import unit_text

REF_MIN = 4.0        # shorter references make the clone unstable
REF_MAX = 11.0       # longer ones the model truncates anyway
REF_RATE = 24000     # what F5-TTS resamples to internally
WEAK_SEPARATION = 0.22


def load_mono(path: str, rate: int = 16000) -> np.ndarray:
    """Decode the whole track to mono float32 at the given rate via ffmpeg."""
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-nostdin", "-i", path, "-vn",
         "-ac", "1", "-ar", str(rate), "-f", "f32le", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float32)


def features(audio: np.ndarray, rate: int, units: list[dict]) -> np.ndarray:
    """One feature vector per unit: timbre, spectral shape and pitch."""
    import librosa

    rows = []
    for unit in units:
        lo = int(unit["start"] * rate)
        hi = min(int(unit["end"] * rate), len(audio))
        clip = audio[lo:hi]
        if len(clip) < rate // 2:                     # too short to characterise
            rows.append(np.zeros(31, dtype=np.float32))
            continue
        mfcc = librosa.feature.mfcc(y=clip, sr=rate, n_mfcc=13)
        centroid = librosa.feature.spectral_centroid(y=clip, sr=rate)
        rolloff = librosa.feature.spectral_rolloff(y=clip, sr=rate)
        bandwidth = librosa.feature.spectral_bandwidth(y=clip, sr=rate)
        f0 = librosa.yin(clip, fmin=60, fmax=400, sr=rate)
        f0 = f0[np.isfinite(f0)]
        rows.append(np.concatenate([
            mfcc.mean(axis=1), mfcc.std(axis=1),
            [centroid.mean(), rolloff.mean(), bandwidth.mean(),
             np.median(f0) if len(f0) else 0.0,
             np.percentile(f0, 90) - np.percentile(f0, 10) if len(f0) else 0.0],
        ]).astype(np.float32))
    return np.vstack(rows)


def cluster(matrix: np.ndarray, forced: int | None) -> tuple[np.ndarray, float, int]:
    """Cluster units into speakers; return labels, silhouette and speaker count."""
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler

    scaled = StandardScaler().fit_transform(matrix)
    if forced == 1:
        return np.zeros(len(scaled), dtype=int), 1.0, 1

    candidates = [forced] if forced else [2, 3]
    best = None
    for count in candidates:
        if count >= len(scaled):
            continue
        labels = KMeans(n_clusters=count, n_init=10, random_state=0).fit_predict(scaled)
        score = silhouette_score(scaled, labels)
        if best is None or score > best[1]:
            best = (labels, score, count)
    if best is None:
        return np.zeros(len(scaled), dtype=int), 1.0, 1

    labels, score, count = best
    # Without a forced count, weak separation is far more likely to mean "one
    # speaker" than "three badly split ones".
    if forced is None and score < WEAK_SEPARATION:
        return np.zeros(len(scaled), dtype=int), score, 1
    return labels, score, count


def cut_reference(media: str, unit: dict, target: str) -> None:
    """Cut one unit out of the source as a 24 kHz mono reference clip."""
    end = min(unit["end"], unit["start"] + REF_MAX)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", media,
         "-ss", f"{unit['start']:.2f}", "-to", f"{end:.2f}",
         "-vn", "-ac", "1", "-ar", str(REF_RATE), target], check=True)


def pick_reference(units: list[dict], indices: list[int],
                   matrix: np.ndarray, centre: np.ndarray) -> int:
    """Pick the unit that best represents a speaker: right length, most typical."""
    usable = [i for i in indices
              if REF_MIN <= units[i]["end"] - units[i]["start"] <= REF_MAX]
    pool = usable or indices
    return min(pool, key=lambda i: float(np.linalg.norm(matrix[i] - centre)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media")
    parser.add_argument("units")
    parser.add_argument("outdir")
    parser.add_argument("--speakers", type=int,
                        help="force the speaker count instead of detecting it")
    parser.add_argument("--rate", type=int, default=16000)
    args = parser.parse_args()

    with open(args.units, encoding="utf-8") as handle:
        units = json.load(handle)
    os.makedirs(args.outdir, exist_ok=True)

    audio = load_mono(args.media, args.rate)
    matrix = features(audio, args.rate, units)
    labels, score, count = cluster(matrix, args.speakers)

    print(f"{len(units)} Einheiten -> {count} Sprecher "
          f"(Trennschaerfe {score:.2f})")
    if count > 1 and score < WEAK_SEPARATION:
        print("  WARNUNG: schwache Trennung. Zuordnung stichprobenartig pruefen,\n"
              "  sonst wechselt die deutsche Stimme mitten im Satz.")

    refs = []
    for speaker in range(count):
        indices = [i for i, label in enumerate(labels) if label == speaker]
        centre = matrix[indices].mean(axis=0)
        chosen = pick_reference(units, indices, matrix, centre)
        target = os.path.join(args.outdir, f"spk{speaker}.wav")
        cut_reference(args.media, units[chosen], target)
        seconds = sum(units[i]["end"] - units[i]["start"] for i in indices)
        refs.append({"speaker": speaker, "ref_file": target,
                     "ref_text": unit_text(units[chosen]), "ref_unit": chosen,
                     "units": len(indices), "seconds": round(seconds, 1)})
        start = units[chosen]["start"]
        print(f"  Sprecher {speaker}: {len(indices)} Einheiten, {seconds / 60:.1f} min"
              f" | Referenz aus {int(start) // 60:02d}:{int(start) % 60:02d}")

    assignment = os.path.join(args.outdir, "speakers.json")
    with open(assignment, "w", encoding="utf-8") as handle:
        json.dump({"speakers": refs, "labels": [int(v) for v in labels]},
                  handle, ensure_ascii=False, indent=1)
    print(f"\nGeschrieben: {assignment}")
    print("Zuordnung gegenlesen, bevor du synthetisierst - eine falsch "
          "einsortierte Einheit\nwechselt hoerbar die Stimme.")


if __name__ == "__main__":
    sys.exit(main())
