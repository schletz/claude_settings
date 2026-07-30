"""Mix the voice-over over the ducked original and mux the result into an MKV.

The original is side-chain ducked by the voice-over, which is the usual voice-over
treatment: the original stays audible enough to tell who is speaking and drops
away while the German voice runs. It is deliberately not muted — with one voice
for all speakers, the original underneath is what still identifies them.

The result keeps two audio tracks: the German mix as default and the untouched
original. No subtitle track is produced.

Usage:
    python mux_voiceover.py <video> <vo.wav> <out.mkv> --audio-lang hun
    python mux_voiceover.py <video> <vo.wav> preview.m4a --sample 300 45
"""

import argparse
import os
import shutil
import subprocess
import sys

# Baseline attenuation of the original before ducking, as linear gain.
ORIGINAL_GAIN = 0.55


def build_filter(gain: float, duck: dict, rate: int) -> str:
    """Assemble the ducking graph for the given balance and output rate.

    Two resampling steps are deliberate. loudnorm switches its output to 192 kHz
    regardless of what came before it, so the chain is pulled back to the working
    rate right after it, and the finished mix is resampled once more to the target
    rate. Without the final step the AAC encoder picks its own maximum, which came
    out as 96 kHz — playable on a PC, but silent or distorted on TV sets whose
    decoders stop at 48 kHz.
    """
    return (
        "[0:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
        f"volume={gain}[orig];"
        "[1:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
        "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,asplit=2[vo1][vo2];"
        f"[orig][vo1]sidechaincompress=threshold={duck['threshold']}:"
        f"ratio={duck['ratio']}:attack=15:release={duck['release']}:makeup=1[duck];"
        "[duck][vo2]amix=inputs=2:duration=first:normalize=0,"
        f"aresample={rate}[mix]"
    )


def run(cmd: list[str]) -> None:
    """Run ffmpeg and abort with its stderr if it fails."""
    result = subprocess.run(cmd, capture_output=True, text=True, check=False,
                            encoding="utf-8", errors="replace")
    if result.returncode != 0:
        sys.exit(f"ffmpeg failed:\n{result.stderr[-4000:]}")


def build_preview(video: str, vo: str, graph: str, rate: int, target: str,
                  span: tuple[float, float]) -> None:
    """Render a short excerpt of the mix so levels can be judged cheaply."""
    start, length = span
    run(["ffmpeg", "-y", "-v", "error", "-nostdin",
         "-ss", str(start), "-t", str(length), "-i", video,
         "-ss", str(start), "-t", str(length), "-i", vo,
         "-filter_complex", graph, "-map", "[mix]",
         "-c:a", "aac", "-b:a", "192k", "-ar", str(rate), target])
    print(f"Hoerprobe: {target}  ({start:.0f}s bis {start + length:.0f}s)")


def build_mkv(video: str, vo: str, graph: str, rate: int, lang: str,
              target: str) -> None:
    """Mux video, German mix and original audio into one MKV."""
    free = shutil.disk_usage(os.path.dirname(target) or ".").free
    needed = os.path.getsize(video) * 1.2
    if free < needed:
        sys.exit(f"Zu wenig freier Speicher: {free / 1e9:.1f} GB frei, "
                 f"{needed / 1e9:.1f} GB noetig")

    run(["ffmpeg", "-y", "-v", "error", "-stats", "-nostdin",
         "-i", video, "-i", vo,
         "-filter_complex", graph,
         "-map", "0:v:0", "-map", "[mix]", "-map", "0:a:0",
         "-c:v", "copy", "-c:a:0", "aac", "-b:a:0", "192k",
         "-ar:a:0", str(rate), "-c:a:1", "copy",
         "-metadata:s:a:0", "language=deu",
         "-metadata:s:a:0", "title=Deutsch (Voice-over)",
         "-metadata:s:a:1", f"language={lang}",
         "-metadata:s:a:1", "title=Original",
         "-disposition:a:0", "default", "-disposition:a:1", "0",
         target])
    print(f"\nGeschrieben: {target} ({os.path.getsize(target) / 1e9:.2f} GB)")


def main() -> None:
    """Render either a preview or the full MKV."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video")
    parser.add_argument("vo")
    parser.add_argument("out")
    parser.add_argument("--audio-lang", default="und",
                        help="ISO 639-2 code of the original audio")
    parser.add_argument("--sample", nargs=2, type=float, metavar=("START", "LEN"),
                        help="render only a short preview of the mix")
    parser.add_argument("--original-gain", type=float, default=ORIGINAL_GAIN,
                        help="baseline level of the original, lower is quieter")
    parser.add_argument("--duck-threshold", type=float, default=0.025)
    parser.add_argument("--duck-ratio", type=int, default=20)
    parser.add_argument("--duck-release", type=int, default=450,
                        help="raise if the ducking pumps audibly")
    parser.add_argument("--sample-rate", type=int, default=44100,
                        help="output rate; TV decoders often stop above 48000")
    args = parser.parse_args()

    duck = {"threshold": args.duck_threshold, "ratio": args.duck_ratio,
            "release": args.duck_release}
    graph = build_filter(args.original_gain, duck, args.sample_rate)
    if args.sample:
        build_preview(args.video, args.vo, graph, args.sample_rate, args.out,
                      (args.sample[0], args.sample[1]))
    else:
        build_mkv(args.video, args.vo, graph, args.sample_rate, args.audio_lang,
                  args.out)


if __name__ == "__main__":
    main()
