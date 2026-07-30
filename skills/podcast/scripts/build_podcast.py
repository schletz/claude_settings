"""Synthesise the German units with F5-TTS and string them into one audio programme.

This is where the podcast parts company with the voice-over. There is no picture
to stay in sync with and no original track underneath, so no unit has to fit a
slot: every one is spoken at the model's natural pace, and the result is as long
as it needs to be. Nothing is ever compressed, which removes the one source of
rushed delivery the voice-over has to live with.

What replaces the slot is a pause model. The gap in the source is a real signal —
it separates a breath from a change of speaker from the applause between two
speeches — but it cannot be used raw: after detect_speech.py the gap across a
removed passage is minutes long. So gaps are capped, floored, and widened where
the speaker changes.

    within one turn      the source gap, capped at MAX_PAUSE
    after a full stop    at least SENTENCE_PAUSE
    speaker change       at least TURN_PAUSE
    across a cut         SECTION_PAUSE, the audible seam of the programme

The full-stop floor is not cosmetic. segment_speech.py closes a unit at a sentence
end even when the speaker ran straight on, so the measured gap there is zero — and
zero is wrong for the podcast, because each unit is now synthesised as its own
utterance with its own falling close. Measured on a 35-minute session, 78 of some
180 joins sat at the floor, so this one number decides how the programme breathes.

Every synthesised unit is trimmed of its leading and trailing silence first,
otherwise the model's own padding — which varies from unit to unit — would drown
the pause model in noise.

Usage:
    python build_podcast.py cues_pod.json podcast.wav \
        --ckpt model_f5tts_german.safetensors --vocab vocab.txt \
        --speakers refs/speakers.json
"""

from __future__ import annotations

import argparse
import json
import time
import wave

import numpy as np

# Pause lengths in seconds, all measured on the finished programme.
MIN_PAUSE = 0.12       # two halves of one sentence, split only by a forced cut
SENTENCE_PAUSE = 0.32  # floor once the previous unit closed a sentence
MAX_PAUSE = 0.90       # a speaker's own pause never buys more than this
TURN_PAUSE = 0.45      # floor when the next unit belongs to someone else
SECTION_PAUSE = 1.20   # applause, music or anything else detect_speech.py cut
SECTION_GAP = 3.0      # a source gap this long counts as a section boundary
SENTENCE_END = (".", "!", "?", ":")

# Silence trimming of a synthesised unit.
FRAME = 0.02
TRIM_FLOOR = 0.02      # share of the unit's peak that still counts as sound
TRIM_KEEP = 0.04       # seconds of the fade left in place at each end

PEAK = 0.89


def trim(audio: np.ndarray, rate: int) -> np.ndarray:
    """Cut the model's own leading and trailing silence off one unit."""
    frame = max(int(FRAME * rate), 1)
    usable = len(audio) - len(audio) % frame
    if usable < frame * 3:
        return audio
    frames = audio[:usable].reshape(-1, frame)
    energy = np.sqrt((frames.astype(np.float64) ** 2).mean(axis=1))
    loud = np.flatnonzero(energy > max(energy.max() * TRIM_FLOOR, 1e-4))
    if not len(loud):
        return audio
    keep = int(TRIM_KEEP * rate)
    start = max(loud[0] * frame - keep, 0)
    end = min((loud[-1] + 1) * frame + keep, len(audio))
    return audio[start:end]


def pause_before(gap: float, changed: bool, closed: bool) -> float:
    """Length of the silence that goes in front of a unit."""
    if gap >= SECTION_GAP:
        return SECTION_PAUSE
    floor = SENTENCE_PAUSE if closed else MIN_PAUSE
    natural = min(max(gap, floor), MAX_PAUSE)
    return max(natural, TURN_PAUSE) if changed else natural


def load_voices(args, count: int) -> tuple[dict, list[int], dict]:
    """Return the reference clip per speaker, the label per unit and their names."""
    if args.speakers:
        with open(args.speakers, encoding="utf-8") as handle:
            data = json.load(handle)
        voices = {entry["speaker"]: (entry["ref_file"], entry["ref_text"])
                  for entry in data["speakers"]}
        names = {entry["speaker"]: entry.get("name") or f"Sprecher {entry['speaker']}"
                 for entry in data["speakers"]}
        labels = data["labels"]
        if len(labels) != count:
            raise SystemExit(f"speakers.json passt nicht: {len(labels)} Zuordnungen "
                             f"gegen {count} Einheiten. Beide stammen aus units.json - "
                             f"wurde dazwischen neu segmentiert?")
        return voices, labels, names
    if args.ref and args.ref_text:
        return {0: (args.ref, args.ref_text)}, [0] * count, {0: "Sprecher 0"}
    raise SystemExit("Entweder --speakers oder --ref plus --ref-text angeben.")


def stamp(seconds: float) -> str:
    """Format seconds as MM:SS."""
    return f"{int(seconds) // 60:02d}:{int(seconds) % 60:02d}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cues")
    parser.add_argument("out")
    parser.add_argument("--ckpt", required=True)
    parser.add_argument("--vocab", required=True)
    parser.add_argument("--speakers", help="speakers.json from the diarisation")
    parser.add_argument("--ref", help="single reference clip, if not using --speakers")
    parser.add_argument("--ref-text", help="transcript of --ref, in the source language")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="global delivery speed; 1.0 is the model's own pace")
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--timeline", help="write the unit map as JSON (default: <out>.timeline.json)")
    args = parser.parse_args()

    with open(args.cues, encoding="utf-8") as handle:
        units = json.load(handle)
    voices, labels, names = load_voices(args, len(units))

    from f5_tts.api import F5TTS
    tts = F5TTS(model="F5TTS_Base", ckpt_file=args.ckpt, vocab_file=args.vocab)
    quiet = lambda *a, **k: None

    def say(text: str, speaker: int) -> tuple[np.ndarray, int]:
        ref_file, ref_text = voices[speaker]
        wav, rate, _ = tts.infer(ref_file=ref_file, ref_text=ref_text, gen_text=text,
                                 speed=args.speed, show_info=quiet, progress=None,
                                 seed=args.seed)
        return trim(np.asarray(wav, dtype=np.float32), rate), rate

    pieces: list[np.ndarray] = []
    timeline: list[dict] = []
    spoken_by: dict[int, float] = {}
    position = 0.0
    rate = 24000
    previous_end: float | None = None
    previous_label: int | None = None
    previous_closed = False
    spoken_count = 0
    started = time.time()

    for index, unit in enumerate(units):
        text = unit["text"].strip()
        if not text:
            # A unit dropped on purpose — a hallucination over applause, a passage
            # that could not be made out. It contributes its gap and nothing else.
            continue
        label = labels[index]
        if previous_end is not None:
            gap = pause_before(unit["start"] - previous_end,
                               label != previous_label, previous_closed)
            pieces.append(np.zeros(int(gap * rate), dtype=np.float32))
            position += gap

        audio, rate = say(text, label)
        pieces.append(audio)
        length = len(audio) / rate
        timeline.append({"index": index, "at": round(position, 2),
                         "length": round(length, 2),
                         "source": round(unit["start"], 2), "speaker": label})
        spoken_by[label] = spoken_by.get(label, 0.0) + length
        position += length
        previous_end, previous_label = unit["end"], label
        previous_closed = text.endswith(SENTENCE_END)
        spoken_count += 1

        if spoken_count % 25 == 0:
            print(f"  {index + 1}/{len(units)} Einheiten, "
                  f"{stamp(position)} Programm, {time.time() - started:.0f}s",
                  flush=True)

    if not pieces:
        raise SystemExit("Keine einzige Einheit hat Text - nichts zu synthetisieren.")

    track = np.concatenate(pieces)
    peak = float(np.abs(track).max())
    if peak > 0:
        track = track / peak * PEAK
    with wave.open(args.out, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(rate)
        writer.writeframes((track * 32767).astype(np.int16).tobytes())

    path = args.timeline or f"{args.out}.timeline.json"
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(timeline, handle, ensure_ascii=False, indent=1)

    source_span = units[-1]["end"] - units[0]["start"]
    print(f"\nGeschrieben: {args.out} ({rate} Hz, mono)")
    print(f"Laufzeit   : {position:.0f}s ({stamp(position)}), "
          f"Quelle {stamp(source_span)}")
    print(f"Einheiten  : {spoken_count} gesprochen, "
          f"{len(units) - spoken_count} uebersprungen")
    for label, seconds in sorted(spoken_by.items(), key=lambda item: -item[1]):
        print(f"  {names.get(label, label):24} {stamp(seconds)}  "
              f"({seconds / position * 100:.0f} %)")
    print(f"Zeitachse  : {path}")


if __name__ == "__main__":
    main()
