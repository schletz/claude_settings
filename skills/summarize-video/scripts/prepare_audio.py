"""Render 16 kHz mono WAV variants of a media file's audio track for transcription.

Profile A produces a single untouched track, B a normalised one, C a set of differently
filtered renderings. Comparing several renderings is what separates a real reading from
a filter artefact on noisy analog sources.

Usage:
    python prepare_audio.py <media> --outdir <dir> --profile C
"""

import argparse
import os
import subprocess
import sys

# Variant name -> ffmpeg audio filter chain applied before resampling to 16 kHz mono.
VARIANTS = {
    "raw": "",
    "clean": "highpass=f=90,lowpass=f=6500,afftdn=nr=14:nf=-30,"
             "dynaudnorm=f=200:g=9,loudnorm=I=-18:TP=-2",
    "gentle": "highpass=f=70,dynaudnorm=f=250:g=7",
    "aggressive": "highpass=f=150,lowpass=f=5500,afftdn=nr=24:nf=-25,"
                  "dynaudnorm=f=150:g=11,alimiter=limit=0.95",
    "left": "pan=mono|c0=FL,highpass=f=90,lowpass=f=6500,afftdn=nr=16:nf=-28,"
            "dynaudnorm=f=200:g=9",
    "right": "pan=mono|c0=FR,highpass=f=90,lowpass=f=6500,afftdn=nr=16:nf=-28,"
             "dynaudnorm=f=200:g=9",
}

PROFILES = {
    "A": ["raw"],
    "B": ["clean", "raw"],
    "C": ["raw", "clean", "gentle", "left"],
}


def render(media: str, outdir: str, variant: str) -> str:
    """Render one variant to <outdir>/<variant>.wav and return its path."""
    chain = VARIANTS[variant]
    target = os.path.join(outdir, f"{variant}.wav")
    cmd = ["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", media, "-vn"]
    # 'left'/'right' already downmix via pan; everything else needs -ac 1.
    if chain:
        cmd += ["-af", chain]
    cmd += ["-ar", "16000"]
    if not chain.startswith("pan="):
        cmd += ["-ac", "1"]
    cmd += [target]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                            errors="replace")
    if result.returncode != 0:
        sys.exit(f"ffmpeg failed for variant {variant}:\n{result.stderr}")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media")
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="C")
    parser.add_argument("--variants", nargs="*",
                        help="explicit variant list, overrides --profile")
    args = parser.parse_args()

    wanted = args.variants or PROFILES[args.profile]
    unknown = [v for v in wanted if v not in VARIANTS]
    if unknown:
        sys.exit(f"Unbekannte Variante(n): {', '.join(unknown)}. "
                 f"Verfuegbar: {', '.join(sorted(VARIANTS))}")

    os.makedirs(args.outdir, exist_ok=True)
    for variant in wanted:
        path = render(args.media, args.outdir, variant)
        size_mb = os.path.getsize(path) / 1024 / 1024
        print(f"{variant:11} -> {path}  ({size_mb:.1f} MB)")

    print(f"\n{len(wanted)} Variante(n) erzeugt in {args.outdir}")


if __name__ == "__main__":
    main()
