"""Analyse the audio track of a media file and recommend a transcription profile.

Reports container/stream facts, loudness, an estimated signal-to-noise ratio, a
per-channel comparison and a pause profile, then classifies the source as quality
class A, B or C.

Measuring the whole file is only meaningful if the whole file is speech. A music
intro, applause or a long silent tail shift the average and the noise floor, so
--from/--to restrict the measurement to the part that actually matters.

Usage:
    python probe_audio.py <media file> [--json]
    python probe_audio.py <media file> --from 300 --to 600
"""

import argparse
import json
import re
import subprocess
import sys


def run(cmd: list[str]) -> str:
    """Run a command and return stdout+stderr as text, tolerating non-zero exit codes."""
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                            errors="replace")
    return (result.stdout or "") + (result.stderr or "")


def probe_streams(path: str) -> dict:
    """Collect container and stream facts via ffprobe."""
    raw = run([
        "ffprobe", "-v", "error", "-of", "json",
        "-show_entries",
        "format=duration,format_name,bit_rate:"
        "stream=index,codec_type,codec_name,sample_rate,channels,width,height",
        path,
    ])
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(f"ffprobe failed for {path}:\n{raw}")


def input_args(path: str, span: tuple[float, float | None] | None) -> list[str]:
    """Build the ffmpeg input arguments, optionally restricted to a time span."""
    if span is None:
        return ["-i", path]
    start, end = span
    args = ["-ss", str(start), "-i", path]
    if end is not None:
        args += ["-t", str(end - start)]
    return args


def measure(path: str, extra_filter: str = "",
            span: tuple[float, float | None] | None = None) -> dict:
    """Measure loudness and noise floor of the audio track with ffmpeg filters."""
    chain = "volumedetect,astats=measure_perchannel=none"
    if extra_filter:
        chain = f"{extra_filter},{chain}"
    out = run(["ffmpeg", "-hide_banner", "-nostdin", *input_args(path, span),
               "-vn", "-af", chain, "-f", "null", "-"])

    def grab(label: str) -> float | None:
        """Read one measurement, accepting the -inf ffmpeg prints for digital silence."""
        match = re.search(label + r":\s*(-?(?:inf|\d+(?:\.\d+)?))", out)
        if not match:
            return None
        return float(match.group(1))

    return {
        "mean_db": grab(r"mean_volume"),
        "max_db": grab(r"max_volume"),
        "rms_db": grab(r"RMS level dB"),
        "noise_floor_db": grab(r"Noise floor dB"),
        "peak_db": grab(r"Peak level dB"),
    }


def channel_rms(path: str, channel: str,
                span: tuple[float, float | None] | None = None) -> float | None:
    """Return the RMS level of one stereo channel, or None if unavailable."""
    return measure(path, f"pan=mono|c0={channel}", span)["rms_db"]


# Thresholds tried when looking for speech pauses, quietest first. -32 dB is what
# transcribe.py uses by default; the coarser steps are for recordings whose background
# never drops that low.
PAUSE_STEPS = (-32.0, -28.0, -24.0, -20.0)


def pause_profile(path: str, span: tuple[float, float | None] | None = None) -> dict:
    """Count detectable speech pauses at increasing silence thresholds.

    Two questions are answered at once. Whether the recording contains real silence at
    all - if it does not, the measured noise floor is not noise but quiet speech, music
    or ambient sound, and the signal-to-noise figure understates the true quality. And
    which threshold `transcribe.py --max-chunk` needs, because its chunker falls back to
    a single (undecodable) block when it finds no pause.
    """
    counts: dict[float, int] = {}
    for threshold in PAUSE_STEPS:
        out = run(["ffmpeg", "-hide_banner", "-nostats", "-nostdin",
                   *input_args(path, span),
                   "-af", f"silencedetect=noise={threshold}dB:d=0.35", "-f", "null", "-"])
        counts[threshold] = len(re.findall(r"silence_start:", out))
    usable = next((db for db in PAUSE_STEPS if counts[db] >= 2), None)
    return {"counts": counts, "usable_threshold_db": usable,
            "has_real_silence": counts[PAUSE_STEPS[0]] >= 2}


def classify(mean_db: float | None, snr_db: float | None,
             silent_floor: bool) -> tuple[str, str]:
    """Map measured loudness and SNR onto a quality class plus a short rationale.

    The signal-to-noise ratio decides, not the mean level: speech with pauses always
    has a low mean, so loudness alone would misjudge a clean recording as poor.
    """
    if silent_floor:
        return "A", ("Rauschboden -inf: die Quelle enthaelt echte digitale Stille, "
                     "also ein sauberes digitales Signal.")
    if snr_db is None:
        if mean_db is not None and mean_db < -30:
            return "C", ("Stoerabstand nicht messbar und sehr leiser Ton "
                         f"({mean_db:.1f} dB) - vorsichtshalber wie Analogquelle.")
        return "B", "Stoerabstand nicht messbar - vorsichtshalber wie Klasse B behandeln."
    # Below ~25 dB the extra effort of class C is cheaper than a bad transcript.
    if snr_db < 25:
        return "C", f"Geringer Stoerabstand ({snr_db:.1f} dB) - verrauschte Quelle."
    if snr_db < 35:
        if mean_db is not None and mean_db < -30:
            return "C", (f"Maessiger Stoerabstand ({snr_db:.1f} dB) bei sehr leisem Ton "
                         f"({mean_db:.1f} dB) - wie Analogquelle behandeln.")
        return "B", f"Brauchbarer, aber nicht sehr hoher Stoerabstand ({snr_db:.1f} dB)."
    return "A", f"Hoher Stoerabstand ({snr_db:.1f} dB) - sauberes Signal."


def floor_caveat(profile: str, pauses: dict) -> str | None:
    """Explain why a poor class may be a measurement artefact rather than a bad source.

    Without real silence there is nothing to measure the noise floor against, so a
    continuously noisy environment - a riverbank, a street, a hall with music - drags the
    computed ratio down even when the speech itself is perfectly clean.
    """
    if pauses["has_real_silence"] or profile == "A":
        return None
    usable = pauses["usable_threshold_db"]
    hint = (f"Pausen erst ab {usable:.0f} dB messbar"
            if usable is not None else "auch bei -20 dB keine Pausen messbar")
    return (
        f"Keine echte Stille im Signal, {hint}.\n"
        "   Der gemessene \"Rauschboden\" ist dann kein Rauschen, sondern leise Sprache,\n"
        "   Musik oder Umgebungsgeraeusch - der Stoerabstand faellt zu niedrig und die\n"
        "   Klasse zu pessimistisch aus. Ersten Durchlauf wie Klasse B fahren und am\n"
        "   Transkript entscheiden, nicht an dieser Zahl."
    )


FILTERS = {
    "A": "keine Aufbereitung noetig (Originalspur verwenden)",
    "B": "highpass=f=80,dynaudnorm=f=250:g=7,loudnorm=I=-18:TP=-2",
    "C": "highpass=f=90,lowpass=f=6500,afftdn=nr=14:nf=-30,"
         "dynaudnorm=f=200:g=9,loudnorm=I=-18:TP=-2",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--from", dest="start", type=float, default=0.0,
                        help="only measure from this second on (skip a music intro)")
    parser.add_argument("--to", dest="end", type=float,
                        help="only measure up to this second")
    args = parser.parse_args()
    span = None if args.start == 0.0 and args.end is None else (args.start, args.end)

    info = probe_streams(args.media)
    fmt = info.get("format", {})
    streams = info.get("streams", [])
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if audio is None:
        sys.exit("Keine Audiospur gefunden.")

    duration = float(fmt.get("duration", 0.0))
    levels = measure(args.media, span=span)
    pauses = pause_profile(args.media, span)
    floor = levels["noise_floor_db"]
    # -inf means the track contains true digital silence, i.e. an unusually clean source.
    silent_floor = floor is not None and floor == float("-inf")
    snr = None
    if levels["rms_db"] is not None and floor is not None and not silent_floor:
        snr = levels["rms_db"] - floor
    crest = None
    if levels["peak_db"] is not None and levels["rms_db"] is not None:
        crest = levels["peak_db"] - levels["rms_db"]

    channels = int(audio.get("channels", 1))
    left = right = None
    if channels >= 2:
        left = channel_rms(args.media, "FL", span)
        right = channel_rms(args.media, "FR", span)

    profile, reason = classify(levels["mean_db"], snr, silent_floor)
    caveat = floor_caveat(profile, pauses)
    report = {
        "file": args.media,
        "duration_s": round(duration, 2),
        "measured_span": span,
        "pauses": pauses,
        "floor_caveat": caveat,
        "video_codec": video.get("codec_name") if video else None,
        "audio_codec": audio.get("codec_name"),
        "sample_rate": audio.get("sample_rate"),
        "channels": channels,
        "levels": levels,
        "snr_db": round(snr, 1) if snr is not None else None,
        "digital_silence": silent_floor,
        "crest_db": round(crest, 1) if crest is not None else None,
        "channel_rms_db": {"left": left, "right": right},
        "profile": profile,
        "reason": reason,
        "filter_chain": FILTERS[profile],
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    print_report(report)


def print_report(report: dict) -> None:
    """Render the measurement as the readable block the skill's steps refer to."""
    levels, pauses = report["levels"], report["pauses"]
    profile, span = report["profile"], report["measured_span"]
    duration, channels = report["duration_s"], report["channels"]

    print(f"Datei          : {report['file']}")
    print(f"Dauer          : {duration:.1f}s ({int(duration)//60}:{int(duration)%60:02d})")
    if span:
        end_note = f"{span[1]:.0f}s" if span[1] is not None else "Ende"
        print(f"Messbereich    : {span[0]:.0f}s - {end_note} (Rest nicht gemessen)")
    print(f"Video / Audio  : {report['video_codec']} / {report['audio_codec']} "
          f"{report['sample_rate']} Hz, {channels} Kanal/Kanaele")
    print(f"Pegel          : mean {levels['mean_db']} dB, max {levels['max_db']} dB")
    print(f"RMS / Rauschen : {levels['rms_db']} dB / {levels['noise_floor_db']} dB")
    if report["digital_silence"]:
        print("Stoerabstand   : Rauschboden -inf (echte digitale Stille vorhanden)")
    elif report["snr_db"] is not None:
        print(f"Stoerabstand   : {report['snr_db']} dB")
    else:
        print("Stoerabstand   : nicht ermittelbar")
    crest = report["crest_db"]
    if crest is not None:
        print(f"Crest-Faktor   : {crest:.1f} dB "
              f"({'typisch fuer Sprache' if 15 <= crest <= 35 else 'auffaellig'})")
    left, right = report["channel_rms_db"]["left"], report["channel_rms_db"]["right"]
    if channels >= 2 and left is not None and right is not None:
        delta = abs(left - right)
        note = "Kanaele nahezu gleich (faktisch mono)" if delta < 2 else \
               f"Kanaele unterschiedlich ({delta:.1f} dB) - beide einzeln pruefen"
        print(f"Kanaele        : L {left} dB / R {right} dB - {note}")
    counts = ", ".join(f"{db:.0f} dB: {n}" for db, n in pauses["counts"].items())
    print(f"Sprechpausen   : {counts}")
    print()
    print(f"=> Qualitaetsklasse {profile}: {report['reason']}")
    if report["floor_caveat"]:
        print(f"   ACHTUNG: {report['floor_caveat']}")
    print(f"   Empfohlene Filterkette: {FILTERS[profile]}")
    usable = pauses["usable_threshold_db"]
    if usable is not None and usable != PAUSE_STEPS[0]:
        print(f"   Fuer transcribe.py --max-chunk zusaetzlich: --silence-db {usable:.0f}")
    if report["floor_caveat"]:
        print("   Vorgehen: erst ein Probelauf, dann anhand des Transkripts entscheiden.")
    elif profile == "C":
        print("   Vorgehen: mehrere Tonvarianten + Fensterlauf + Konsensbildung.")
    elif profile == "B":
        print("   Vorgehen: aufbereitete Spur, ein Durchlauf, Stichproben gegenpruefen.")
    else:
        print("   Vorgehen: ein Durchlauf, Segment-Timings direkt uebernehmen.")


if __name__ == "__main__":
    main()
