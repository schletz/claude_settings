"""Synthesise cue units to 16 kHz WAVs so the intelligibility check can read them.

Stage one of the two-stage check. Whisper and F5-TTS both want the GPU, so the two
stages exchange WAV files and a manifest rather than objects and neither has to hold
the other's model in memory. Output is resampled to 16 kHz here, which is what Whisper
wants anyway.

The label carries the speaker, so a multi-voice run produces one row per voice in the
comparison table. A reference clip that clones badly shows up there and nowhere else.

Usage:
    python synth_samples.py cues_vo.json <workdir>/bench \
        --ckpt model_f5tts_german.safetensors --vocab vocab.txt \
        --speakers refs/speakers.json --count 12
"""

import argparse
import json
import os
import time
import wave

import numpy as np

TARGET_RATE = 16000


def to_16k(audio: np.ndarray, rate: int) -> np.ndarray:
    """Linear resample to 16 kHz — accurate enough as recogniser input."""
    if rate == TARGET_RATE:
        return audio
    count = int(len(audio) * TARGET_RATE / rate)
    return np.interp(np.linspace(0, len(audio) - 1, count),
                     np.arange(len(audio)), audio)


def write_wav(path: str, audio: np.ndarray) -> None:
    """Write mono 16 kHz int16, normalising instead of clipping.

    F5-TTS returns peaks above 1.0 (measured 1.29), so plain clipping would distort
    exactly the loud syllables the recogniser needs most.
    """
    peak = float(np.abs(audio).max())
    if peak > 1.0:
        audio = audio / peak
    with wave.open(path, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(TARGET_RATE)
        writer.writeframes((audio * 32767).astype(np.int16).tobytes())


def pick(total: int, count: int | None) -> list[int]:
    """Choose which units to render: all, or a spread that starts with the short ones.

    Short units come first because that is where a clone falls apart, and a sample of
    only long units would miss it.
    """
    if count is None or count >= total:
        return list(range(total))
    head = list(range(min(4, total)))
    step = max(total // (count - len(head)), 1)
    rest = [i for i in range(0, total, step) if i not in head]
    return sorted(head + rest[:count - len(head)])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cues")
    parser.add_argument("outdir")
    parser.add_argument("--ckpt", required=True)
    parser.add_argument("--vocab", required=True)
    parser.add_argument("--speakers", help="speakers.json from diarize.py")
    parser.add_argument("--ref", help="single reference clip, if not using --speakers")
    parser.add_argument("--ref-text", help="transcript of --ref, in the source language")
    parser.add_argument("--count", type=int, help="units to sample (default: all)")
    parser.add_argument("--seed", type=int, default=1234)
    args = parser.parse_args()

    with open(args.cues, encoding="utf-8") as handle:
        cues = json.load(handle)

    if args.speakers:
        with open(args.speakers, encoding="utf-8") as handle:
            data = json.load(handle)
        voices = {entry["speaker"]: (entry["ref_file"], entry["ref_text"])
                  for entry in data["speakers"]}
        labels = data["labels"]
    elif args.ref and args.ref_text:
        voices = {0: (args.ref, args.ref_text)}
        labels = [0] * len(cues)
    else:
        raise SystemExit("Entweder --speakers oder --ref plus --ref-text angeben.")

    chosen = pick(len(cues), args.count)
    os.makedirs(args.outdir, exist_ok=True)

    from f5_tts.api import F5TTS
    tts = F5TTS(model="F5TTS_Base", ckpt_file=args.ckpt, vocab_file=args.vocab)
    quiet = lambda *a, **k: None

    manifest = []
    started = time.time()
    for position, index in enumerate(chosen):
        speaker = labels[index]
        ref_file, ref_text = voices[speaker]
        label = f"f5-spk{speaker}"
        wav, rate, _ = tts.infer(ref_file=ref_file, ref_text=ref_text,
                                 gen_text=cues[index]["text"], show_info=quiet,
                                 progress=None, seed=args.seed)
        target = os.path.join(args.outdir, f"{label}_{index:03d}.wav")
        write_wav(target, to_16k(np.asarray(wav, dtype=np.float64), rate))
        manifest.append({"voice": label, "index": index,
                         "text": cues[index]["text"], "path": target})
        if (position + 1) % 25 == 0:
            print(f"  {position + 1}/{len(chosen)} Einheiten, "
                  f"{time.time() - started:.0f}s", flush=True)

    with open(os.path.join(args.outdir, "manifest.json"), "w",
              encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=1)

    for speaker in sorted(voices):
        count = sum(1 for entry in manifest if entry["voice"] == f"f5-spk{speaker}")
        print(f"  f5-spk{speaker}: {count} Einheiten")
    print(f"\nManifest: {os.path.join(args.outdir, 'manifest.json')}")


if __name__ == "__main__":
    main()
