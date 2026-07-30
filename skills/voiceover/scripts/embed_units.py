"""Compute one ECAPA-TDNN speaker embedding per speech unit.

Stage one of the two-stage speaker split. diarize.py's MFCC features separate a
studio host from a phone guest because their channels differ; they do not separate
several people sitting at one table on identical microphones. A trained
speaker-verification embedding does.

The checkpoint (speechbrain/spkrec-ecapa-voxceleb) downloads without a token and
without gated weights, so this keeps the skill's "no extra hurdles" property.

Usage:
    python embed_units.py <media> units.json emb.npy
"""

import argparse
import json
import os
import subprocess
import sys

import numpy as np

RATE = 16000
# Embeddings from very short clips are noisy; widen them symmetrically first.
MIN_SECONDS = 1.5
MAX_SECONDS = 12.0
DIMS = 192


def load_mono(path: str) -> np.ndarray:
    """Decode the whole track to mono float32 at 16 kHz via ffmpeg."""
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-nostdin", "-i", path, "-vn",
         "-ac", "1", "-ar", str(RATE), "-f", "f32le", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float32).copy()


def build_encoder(savedir: str):
    """Load the ECAPA encoder, copying its files instead of symlinking them."""
    import torch
    from speechbrain.inference.speaker import EncoderClassifier
    from speechbrain.utils.fetching import LocalStrategy

    device = "cuda" if torch.cuda.is_available() else "cpu"
    # Windows without developer mode cannot create symlinks, and speechbrain's
    # default fetch strategy does exactly that: OSError WinError 1314.
    return EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir=savedir,
        local_strategy=LocalStrategy.COPY_SKIP_CACHE,
        run_opts={"device": device}), device


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media")
    parser.add_argument("units")
    parser.add_argument("out")
    parser.add_argument("--savedir", help="where to put the checkpoint "
                                          "(default: next to --out)")
    args = parser.parse_args()

    import torch

    with open(args.units, encoding="utf-8") as handle:
        units = json.load(handle)

    savedir = args.savedir or os.path.join(os.path.dirname(
        os.path.abspath(args.out)) or ".", "ecapa")
    audio = load_mono(args.media)
    encoder, device = build_encoder(savedir)

    rows = []
    for index, unit in enumerate(units):
        start, end = unit["start"], unit["end"]
        if end - start < MIN_SECONDS:
            pad = (MIN_SECONDS - (end - start)) / 2
            start, end = start - pad, end + pad
        end = min(end, start + MAX_SECONDS)

        lo = max(int(start * RATE), 0)
        hi = min(int(end * RATE), len(audio))
        clip = audio[lo:hi]
        if len(clip) < RATE // 4:
            rows.append(np.zeros(DIMS, dtype=np.float32))
            continue

        with torch.no_grad():
            wav = torch.from_numpy(clip).unsqueeze(0).to(device)
            rows.append(encoder.encode_batch(wav).squeeze().cpu()
                        .numpy().astype(np.float32))

        if (index + 1) % 100 == 0:
            print(f"  {index + 1}/{len(units)} Einheiten eingebettet")

    matrix = np.vstack(rows)
    matrix /= np.maximum(np.linalg.norm(matrix, axis=1, keepdims=True), 1e-9)
    np.save(args.out, matrix)
    print(f"\nGeschrieben: {args.out} {matrix.shape}")
    print("Naechster Schritt: diarize_ecapa.py")


if __name__ == "__main__":
    sys.exit(main())
