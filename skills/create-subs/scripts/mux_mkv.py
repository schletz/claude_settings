"""Mux a media file and a German SubRip file into an MKV without re-encoding.

Video and audio are stream-copied, so the result is lossless and fast. The subtitle
track is tagged German and set as default. If the source is already an .mkv, the output
gets a .sub.mkv suffix so the source is never overwritten.

Usage:
    python mux_mkv.py <media> <subtitles.srt> [--audio-lang hu] [--output out.mkv]
"""

import argparse
import os
import shutil
import subprocess
import sys

# ISO 639-1 -> ISO 639-2/B, the codes Matroska expects.
LANG3 = {
    "de": "deu", "en": "eng", "hu": "hun", "fr": "fra", "it": "ita", "es": "spa",
    "pt": "por", "nl": "nld", "pl": "pol", "cs": "ces", "sk": "slk", "sl": "slv",
    "hr": "hrv", "sr": "srp", "ro": "ron", "bg": "bul", "ru": "rus", "uk": "ukr",
    "tr": "tur", "el": "ell", "sv": "swe", "no": "nor", "da": "dan", "fi": "fin",
    "ja": "jpn", "zh": "zho", "ko": "kor", "ar": "ara", "he": "heb", "la": "lat",
}


def to_iso3(code: str | None) -> str | None:
    """Normalise a language code to ISO 639-2/B, passing three-letter codes through."""
    if not code:
        return None
    code = code.strip().lower()
    if len(code) == 3:
        return code
    return LANG3.get(code)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media")
    parser.add_argument("subtitles")
    parser.add_argument("--audio-lang", help="spoken language, ISO 639-1 or -2")
    parser.add_argument("--output", help="explicit output path")
    parser.add_argument("--title", default="Deutsch",
                        help="subtitle track title shown by players")
    parser.add_argument("--not-default", action="store_true",
                        help="do not mark the subtitle track as default")
    args = parser.parse_args()

    for path in (args.media, args.subtitles):
        if not os.path.isfile(path):
            sys.exit(f"Datei nicht gefunden: {path}")

    base, ext = os.path.splitext(args.media)
    output = args.output or (f"{base}.sub.mkv" if ext.lower() == ".mkv" else f"{base}.mkv")
    if os.path.abspath(output) == os.path.abspath(args.media):
        sys.exit("Ausgabe wuerde die Quelle ueberschreiben - bitte --output setzen.")

    source_size = os.path.getsize(args.media)
    free = shutil.disk_usage(os.path.dirname(os.path.abspath(output))).free
    if free < source_size * 1.1:
        sys.exit(f"Zu wenig freier Speicher: {free / 2**30:.1f} GB frei, "
                 f"benoetigt werden rund {source_size / 2**30:.1f} GB.")
    if os.path.exists(output):
        sys.exit(f"Zieldatei existiert bereits: {output}")

    cmd = [
        "ffmpeg", "-y", "-v", "error", "-stats", "-nostdin",
        "-i", args.media, "-i", args.subtitles,
        "-map", "0:v:0", "-map", "0:a:0", "-map", "1:0",
        "-c:v", "copy", "-c:a", "copy", "-c:s", "srt",
        "-metadata:s:s:0", "language=deu",
        "-metadata:s:s:0", f"title={args.title}",
    ]
    audio_lang = to_iso3(args.audio_lang)
    if audio_lang:
        cmd += ["-metadata:s:a:0", f"language={audio_lang}"]
    if not args.not_default:
        cmd += ["-disposition:s:0", "default"]
    cmd.append(output)

    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit("ffmpeg ist fehlgeschlagen.")

    print(f"\nGeschrieben: {output} ({os.path.getsize(output) / 2**30:.2f} GB)")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=index,codec_type,codec_name:stream_tags=language,title",
         "-of", "default=noprint_wrappers=1", output],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    print(probe.stdout)


if __name__ == "__main__":
    main()
