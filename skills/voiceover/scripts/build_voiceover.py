"""Synthesise the German voice-over track with F5-TTS and place it overlap-free.

The units already carry the speaker's own timing, so nothing is regrouped here. Each
unit is fitted into the slot reaching up to the next one. Where the German does not
fit, F5-TTS raises `speed`, which shortens the delivery natively and avoids the
artefacts a post-hoc time stretch introduces.

Placement never overlaps. A unit starts no earlier than the previous one finished
speaking, and the resulting delay is absorbed at the next real pause. Allowing
overlap instead was tried and is clearly worse: on a 50-minute interview it put two
sentences of the same voice on top of each other at 57 places, up to a full second
each. Delaying instead cost at most half a second of drift.

With speakers.json from diarize.py every speaker keeps their own cloned voice, so an
interview stays followable without leaning on the original audio underneath.

Usage:
    python build_voiceover.py cues_vo.json vo.wav --duration 1843.9 \
        --ckpt model_f5tts_german.safetensors --vocab vocab.txt \
        --speakers refs/speakers.json
"""

import argparse
import json
import time
import wave

import numpy as np

GUARD = 0.12        # silence kept between two units, seconds
MAX_SPEED = 1.45    # past this the delivery is audibly rushed
PEAK = 0.89


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cues")
    parser.add_argument("out")
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--ckpt", required=True)
    parser.add_argument("--vocab", required=True)
    parser.add_argument("--speakers", help="speakers.json from diarize.py")
    parser.add_argument("--ref", help="single reference clip, if not using --speakers")
    parser.add_argument("--ref-text", help="transcript of --ref, in the source language")
    parser.add_argument("--seed", type=int, default=1234)
    args = parser.parse_args()

    with open(args.cues, encoding="utf-8") as handle:
        units = json.load(handle)

    if args.speakers:
        with open(args.speakers, encoding="utf-8") as handle:
            data = json.load(handle)
        voices = {entry["speaker"]: (entry["ref_file"], entry["ref_text"])
                  for entry in data["speakers"]}
        labels = data["labels"]
        if len(labels) != len(units):
            raise SystemExit(f"speakers.json passt nicht: {len(labels)} Zuordnungen "
                             f"gegen {len(units)} Einheiten. Beide stammen aus "
                             f"units.json - wurde dazwischen neu segmentiert?")
    elif args.ref and args.ref_text:
        voices = {0: (args.ref, args.ref_text)}
        labels = [0] * len(units)
    else:
        raise SystemExit("Entweder --speakers oder --ref plus --ref-text angeben.")

    from f5_tts.api import F5TTS
    tts = F5TTS(model="F5TTS_Base", ckpt_file=args.ckpt, vocab_file=args.vocab)
    quiet = lambda *a, **k: None

    def say(text: str, speaker: int, speed: float) -> tuple[np.ndarray, int]:
        ref_file, ref_text = voices[speaker]
        wav, rate, _ = tts.infer(ref_file=ref_file, ref_text=ref_text, gen_text=text,
                                 speed=speed, show_info=quiet, progress=None,
                                 seed=args.seed)
        return np.asarray(wav, dtype=np.float32), rate

    first, rate = say(units[0]["text"], labels[0], 1.0)
    track = np.zeros(int(args.duration * rate) + rate, dtype=np.float32)

    compressed = 0
    delayed: list[tuple[float, float]] = []
    cursor = 0.0
    started = time.time()

    for index, unit in enumerate(units):
        # An empty cue means the passage stays untranslated on purpose - leave the
        # slot silent so the original track plays through unducked.
        if not unit["text"].strip():
            continue
        start = max(unit["start"], cursor)
        slot_end = (units[index + 1]["start"] - GUARD
                    if index + 1 < len(units) else args.duration)
        slot = max(slot_end - start, 0.5)

        audio = first if index == 0 else say(unit["text"], labels[index], 1.0)[0]
        spoken = len(audio) / rate
        if spoken > slot:
            audio, _ = say(unit["text"], labels[index],
                           min(spoken / slot, MAX_SPEED))
            spoken = len(audio) / rate
            compressed += 1

        lateness = start - unit["start"]
        if lateness > 0.25:
            delayed.append((unit["start"], lateness))

        offset = int(start * rate)
        end = min(offset + len(audio), len(track))
        track[offset:end] += audio[:end - offset]
        cursor = start + spoken + GUARD

        if (index + 1) % 25 == 0:
            print(f"  {index + 1}/{len(units)} Einheiten, "
                  f"{time.time() - started:.0f}s", flush=True)

    peak = float(np.abs(track).max())
    if peak > 0:
        track = track / peak * PEAK
    with wave.open(args.out, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(rate)
        writer.writeframes((track * 32767).astype(np.int16).tobytes())

    print(f"\nGeschrieben: {args.out} ({rate} Hz)")
    print(f"Stimmen: {len(voices)}")
    print(f"Einheiten gestaucht: {compressed}/{len(units)}")
    if delayed:
        worst = max(late for _, late in delayed)
        print(f"Verzoegert eingesetzt: {len(delayed)} Einheiten, "
              f"max. {worst:.1f}s Versatz")
        for at, late in sorted(delayed, key=lambda x: -x[1])[:5]:
            print(f"  {int(at) // 60:02d}:{int(at) % 60:02d} +{late:.1f}s")
    else:
        print("Alle Einheiten sitzen exakt auf ihrer Originalzeit.")

    if compressed > len(units) // 4:
        print("\nWARNUNG: mehr als ein Viertel gestaucht - die Uebersetzung ist "
              "zu lang.\nDort kuerzen, nicht hier nachregeln.")


if __name__ == "__main__":
    main()
