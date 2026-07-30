"""Find the passages that carry speech and render them as one gap-free track.

A podcast has no picture to fill, so everything that is not speech is dead air:
a musical intro, applause, the hum of a hall between two speakers. Cutting it
here rather than later pays twice. Whisper never sees the music, so it cannot
invent words over it — the subscribe-phrase hallucination is largely a music and
silence artefact — and the decoder only works on the material that carries text,
which on a session with a seven-minute intro is a quarter of the runtime saved.

Detection is Silero VAD: a small neural gate, some 2 MB, that runs far faster
than real time on the CPU and was trained to tell speech from music and noise.
An energy gate cannot do this job — music is loud, and ``silencedetect`` would
keep every note of it.

Two files come out, and the split matters:

    speech.wav    16 kHz mono, the speech regions back to back, for Whisper
    regions.json  where each of them sat in the source, for map_words.py

Everything after the transcription therefore works on source timestamps again,
so the diarisation cuts its reference clips from the untouched original and any
time this run reports back is a time the user can find in the video.

Usage:
    python detect_speech.py <media> --outdir <workdir>
    python detect_speech.py <media> --outdir <workdir> --pad 0.4 --merge 2.0
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import wave

import numpy as np

RATE = 16000

# Silero reports the syllables it is sure about; a word's onset and its decaying
# tail sit outside that. Padding is deliberately generous — a clipped word costs
# a transcription error, half a second of room tone costs nothing.
PAD = 0.30
# Gaps shorter than this stay in the track. Breathing pauses belong to the
# delivery, and cutting them produces the chopped rhythm of a badly edited
# interview. Only blocks longer than this are worth removing.
MERGE_GAP = 1.20
# An isolated blip this short is a cough, a chair, a shout inside applause. It
# carries no sentence, but it does invite Whisper to hallucinate one.
MIN_REGION = 0.80
# Fade at every cut edge, seconds. Without it the splice clicks, and a click is
# a broadband transient that the decoder reads as a consonant.
FADE = 0.012


def decode(path: str) -> np.ndarray:
    """Decode the whole file to 16 kHz mono float32."""
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-i", path, "-vn",
           "-ar", str(RATE), "-ac", "1", "-f", "f32le", "-"]
    proc = subprocess.run(cmd, capture_output=True, check=False)
    if proc.returncode != 0:
        sys.exit(f"ffmpeg konnte {path} nicht dekodieren:\n"
                 f"{proc.stderr.decode('utf-8', 'replace')[-2000:]}")
    return np.frombuffer(proc.stdout, dtype=np.float32).copy()


def speech_runs(audio: np.ndarray, threshold: float) -> list[tuple[float, float]]:
    """Return Silero's speech spans in seconds."""
    try:
        from silero_vad import get_speech_timestamps, load_silero_vad
    except ImportError:
        sys.exit("silero-vad fehlt. Installieren mit:\n"
                 "  python -m pip install --no-deps silero-vad")
    import torch

    model = load_silero_vad()
    stamps = get_speech_timestamps(
        torch.from_numpy(audio), model, sampling_rate=RATE,
        threshold=threshold,
        min_speech_duration_ms=200,
        # Silero's own merging is left coarse; the real merging happens below,
        # where the gap length can be reported and tuned.
        min_silence_duration_ms=400,
        speech_pad_ms=0,
    )
    return [(s["start"] / RATE, s["end"] / RATE) for s in stamps]


def consolidate(runs: list[tuple[float, float]], duration: float, pad: float,
                merge: float, min_region: float) -> list[tuple[float, float]]:
    """Pad, merge and drop, in that order — the order decides the result.

    Padding before merging is what keeps a normal speaking pause intact: two
    sentences 1.5 s apart are 0.9 s apart once both are padded, and fall under
    the merge gap. Dropping last means a short run that merged into a long
    region is judged as part of that region, not on its own.
    """
    padded = [(max(start - pad, 0.0), min(end + pad, duration))
              for start, end in runs]
    merged: list[list[float]] = []
    for start, end in padded:
        if merged and start - merged[-1][1] < merge:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged if end - start >= min_region]


def render(audio: np.ndarray, regions: list[tuple[float, float]], out: str) -> list[dict]:
    """Write the regions back to back and return their map into that track."""
    pieces: list[np.ndarray] = []
    mapping: list[dict] = []
    offset = 0.0
    fade = int(FADE * RATE)
    for start, end in regions:
        piece = audio[int(start * RATE):int(end * RATE)].copy()
        if len(piece) > 2 * fade:
            ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
            piece[:fade] *= ramp
            piece[-fade:] *= ramp[::-1]
        pieces.append(piece)
        length = len(piece) / RATE
        mapping.append({"start": round(start, 3), "end": round(end, 3),
                        "offset": round(offset, 3), "length": round(length, 3)})
        offset += length

    track = np.concatenate(pieces) if pieces else np.zeros(0, dtype=np.float32)
    with wave.open(out, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(RATE)
        writer.writeframes(np.clip(track * 32767, -32768, 32767).astype(np.int16).tobytes())
    return mapping


def stamp(seconds: float) -> str:
    """Format seconds as MM:SS."""
    return f"{int(seconds) // 60:02d}:{int(seconds) % 60:02d}"


def report(mapping: list[dict], duration: float, min_gap: float) -> None:
    """Print the kept share and every dropped block worth a second look."""
    kept = sum(entry["length"] for entry in mapping)
    print(f"Quelle       : {duration:.1f}s ({stamp(duration)})")
    print(f"Sprachanteil : {kept:.1f}s ({stamp(kept)}, {kept / duration * 100:.0f} %)")
    print(f"Regionen     : {len(mapping)}")

    dropped: list[tuple[float, float]] = []
    cursor = 0.0
    for entry in mapping:
        if entry["start"] - cursor >= min_gap:
            dropped.append((cursor, entry["start"]))
        cursor = entry["end"]
    if duration - cursor >= min_gap:
        dropped.append((cursor, duration))

    if not dropped:
        print("\nKeine nennenswerten Bloecke ohne Sprache.")
        return
    total = sum(end - start for start, end in dropped)
    print(f"\nWeggeschnitten: {len(dropped)} Bloecke, {total:.0f}s gesamt "
          f"(ab {min_gap:.0f}s Laenge):")
    for start, end in sorted(dropped, key=lambda d: d[0] - d[1])[:15]:
        print(f"  {stamp(start)} - {stamp(end)}   {end - start:6.1f}s")
    print("\nSieh die langen Bloecke durch, bevor du weiterlaeufst: Vorspann, "
          "Abspann und Applaus gehoeren hierher, eine Rede nicht.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media")
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--name", default="speech",
                        help="Basisname der beiden Ausgabedateien")
    parser.add_argument("--threshold", type=float, default=0.5,
                        help="Silero-Schwelle; niedriger haelt mehr fuer Sprache")
    parser.add_argument("--pad", type=float, default=PAD,
                        help="Zugabe vor und nach jeder erkannten Passage, Sekunden")
    parser.add_argument("--merge", type=float, default=MERGE_GAP,
                        help="Luecken unter diesem Wert bleiben erhalten")
    parser.add_argument("--min-region", type=float, default=MIN_REGION,
                        help="kuerzere Einzelregionen werden verworfen")
    parser.add_argument("--min-gap", type=float, default=3.0,
                        help="ab dieser Laenge wird ein Schnitt gemeldet")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    audio = decode(args.media)
    duration = len(audio) / RATE

    runs = speech_runs(audio, args.threshold)
    regions = consolidate(runs, duration, args.pad, args.merge, args.min_region)
    if not regions:
        sys.exit("Keine Sprache gefunden. Mit --threshold 0.3 erneut versuchen.")

    wav_path = os.path.join(args.outdir, f"{args.name}.wav")
    mapping = render(audio, regions, wav_path)
    json_path = os.path.join(args.outdir, f"{args.name}_regions.json")
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump({"source": os.path.abspath(args.media),
                   "source_duration": round(duration, 3),
                   "rate": RATE, "regions": mapping}, handle,
                  ensure_ascii=False, indent=1)

    report(mapping, duration, args.min_gap)
    print(f"\nGeschrieben: {wav_path}\n             {json_path}")


if __name__ == "__main__":
    main()
