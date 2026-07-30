"""Master the synthesised track and write the podcast as FLAC, 48 kHz stereo.

Three things happen here that the raw synthesis output cannot do for itself.

Loudness is measured over the whole programme and corrected in a second pass.
One-pass loudnorm works from a running estimate, so the first minute comes out
at a different level than the last — audible on a programme that alternates
between a hall and a studio clip. The two-pass form applies one constant gain,
which is what a podcast player expects: ``-16 LUFS`` is the spoken-word target,
and the true peak stays below ``-1.5 dBTP`` so a lossy re-encode downstream has
headroom.

The rate is then forced back to 48 kHz. loudnorm switches its output to 192 kHz
regardless of what precedes it in the graph, and without the final resample the
encoder simply keeps that — a file three times the size for nothing.

Stereo is dual mono, on purpose. Cloned voices belong in the centre; panning
speakers apart sounds like a gimmick on headphones and collapses to nothing in
a car.

Usage:
    python encode_podcast.py podcast.wav "kanal-titel.de.flac" --title "..." \
        --artist "Kanal" --date 2026-08-18 --source "https://..."
    python encode_podcast.py podcast.wav probe.flac --sample 300 45
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

RATE = 48000
TARGET_I = -16.0
TARGET_TP = -1.5
TARGET_LRA = 11.0


def run(cmd: list[str], capture: bool = False) -> str:
    """Run ffmpeg, aborting with its stderr if it fails."""
    result = subprocess.run(cmd, capture_output=True, text=True, check=False,
                            encoding="utf-8", errors="replace")
    if result.returncode != 0:
        sys.exit(f"ffmpeg failed:\n{result.stderr[-4000:]}")
    return result.stderr if capture else ""


def measure(source: str) -> dict:
    """First loudnorm pass: return the measured loudness of the whole programme."""
    stderr = run(["ffmpeg", "-v", "info", "-nostdin", "-i", source,
                  "-af", f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:"
                         "print_format=json",
                  "-f", "null", "-"], capture=True)
    match = re.search(r"\{[^{}]*input_i[^{}]*\}", stderr, re.S)
    if not match:
        sys.exit("loudnorm hat keine Messwerte geliefert:\n" + stderr[-2000:])
    return json.loads(match.group(0))


def filter_chain(stats: dict | None) -> str:
    """Assemble the mastering chain, with measured values when they exist."""
    if stats:
        norm = (f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:"
                f"measured_I={stats['input_i']}:measured_TP={stats['input_tp']}:"
                f"measured_LRA={stats['input_lra']}:"
                f"measured_thresh={stats['input_thresh']}:"
                f"offset={stats['target_offset']}:linear=true")
    else:
        norm = f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}"
    # The resample after loudnorm is not optional; see the module docstring.
    return f"{norm},aresample={RATE},aformat=sample_fmts=s16:channel_layouts=stereo"


def tags(args) -> list[str]:
    """Vorbis comments for the FLAC container."""
    pairs = {"title": args.title, "artist": args.artist, "album": args.album,
             "date": args.date, "genre": "Podcast",
             "comment": args.source and f"Deutsche Fassung von {args.source}"}
    out: list[str] = []
    for key, value in pairs.items():
        if value:
            out += ["-metadata", f"{key}={value}"]
    return out


def duration(path: str) -> float:
    """Runtime of a media file in seconds."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True).stdout.strip()
    return float(out or 0.0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("track", help="podcast.wav from build_podcast.py")
    parser.add_argument("out", help="target .flac")
    parser.add_argument("--title")
    parser.add_argument("--artist", help="Kanal oder Herausgeber der Quelle")
    parser.add_argument("--album")
    parser.add_argument("--date")
    parser.add_argument("--source",
                        help="URL der Quelle, landet im Kommentarfeld")
    parser.add_argument("--sample", nargs=2, type=float, metavar=("START", "LEN"),
                        help="nur einen Ausschnitt schreiben, zum Hineinhoeren")
    parser.add_argument("--compression", type=int, default=8,
                        help="FLAC-Kompressionsstufe 0-12")
    args = parser.parse_args()

    if args.sample:
        start, length = args.sample
        run(["ffmpeg", "-y", "-v", "error", "-nostdin",
             "-ss", str(start), "-t", str(length), "-i", args.track,
             "-af", filter_chain(None), "-c:a", "flac",
             "-compression_level", str(args.compression), args.out])
        print(f"Hoerprobe: {args.out}  ({start:.0f}s bis {start + length:.0f}s)")
        return

    stats = measure(args.track)
    print(f"Gemessen   : {float(stats['input_i']):.1f} LUFS, "
          f"True Peak {float(stats['input_tp']):.1f} dBTP, "
          f"LRA {float(stats['input_lra']):.1f}")

    run(["ffmpeg", "-y", "-v", "error", "-stats", "-nostdin", "-i", args.track,
         "-af", filter_chain(stats), "-c:a", "flac",
         "-compression_level", str(args.compression), *tags(args), args.out])

    size = os.path.getsize(args.out) / 1e6
    print(f"\nGeschrieben: {args.out}")
    print(f"             {duration(args.out):.0f}s, {size:.1f} MB, "
          f"FLAC {RATE} Hz stereo, Ziel {TARGET_I} LUFS")


if __name__ == "__main__":
    main()
