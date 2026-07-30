"""Score synthesised units by reading them back with Whisper.

Stage two of the two-stage check, on the system Python because it needs torch.

Spectral measures — fundamental frequency, noise floor, high-frequency share —
say nothing about whether a voice says the right words. A model that babbles scores
a clean noise floor. Transcribing the synthesis and comparing it against the text
the voice was given measures intelligibility directly, and it is the only check
that catches a model collapsing into a loop.

Reading: under 10 percent is good, and most of the remainder is the recogniser
rather than the voice — Whisper writes "86-jährigen" where the cue said
"sechsundachtzigjährigen" and that counts as three errors. Above 30 percent on a
single unit, look at it. Above 100 percent the model is emitting more words than it
was given, which means it is hallucinating.

Usage:
    python check_intelligibility.py <workdir>/bench
    python check_intelligibility.py <workdir>/bench --worst 10
"""

import argparse
import json
import os
import re
import wave

import numpy as np
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

MODEL = "openai/whisper-large-v3"


def normalise(text: str) -> list[str]:
    """Lowercase word list without punctuation, for the edit distance."""
    return re.sub(r"[^\wäöüß ]", " ", text.lower()).split()


def word_error_rate(reference: list[str], hypothesis: list[str]) -> float:
    """Levenshtein distance over words, divided by the reference length."""
    previous = list(range(len(hypothesis) + 1))
    for i, ref in enumerate(reference, 1):
        current = [i]
        for j, hyp in enumerate(hypothesis, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1,
                               previous[j - 1] + (ref != hyp)))
        previous = current
    return previous[-1] / max(len(reference), 1)


def main() -> None:
    """Transcribe every entry and report the error rate per voice."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bench", help="folder written by synth_samples.py")
    parser.add_argument("--worst", type=int, default=5,
                        help="how many bad units to print per voice")
    args = parser.parse_args()

    with open(os.path.join(args.bench, "manifest.json"), encoding="utf-8") as handle:
        manifest = json.load(handle)

    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        MODEL, dtype=torch.float16).to("cuda")
    processor = AutoProcessor.from_pretrained(MODEL)
    asr = pipeline("automatic-speech-recognition", model=model,
                   tokenizer=processor.tokenizer,
                   feature_extractor=processor.feature_extractor,
                   dtype=torch.float16, device="cuda")

    results: dict[str, list] = {}
    for entry in manifest:
        with wave.open(entry["path"]) as reader:
            audio = np.frombuffer(reader.readframes(reader.getnframes()),
                                  dtype=np.int16).astype(np.float32) / 32768
        heard = asr({"array": audio, "sampling_rate": 16000},
                    generate_kwargs={"language": "de", "task": "transcribe"})
        value = word_error_rate(normalise(entry["text"]),
                                normalise(heard["text"]))
        results.setdefault(entry["voice"], []).append(
            (value, entry["index"], entry["text"], heard["text"].strip()))

    print(f"\n{'Stimme':>26} {'WER':>7} {'>30%':>7} {'>100%':>7}")
    for voice, rows in sorted(results.items(),
                              key=lambda kv: np.mean([r[0] for r in kv[1]])):
        values = [r[0] for r in rows]
        print(f"{voice:>26} {np.mean(values) * 100:6.1f}% "
              f"{sum(v > 0.3 for v in values):6d} {sum(v > 1.0 for v in values):6d}")

    for voice, rows in results.items():
        rows.sort(reverse=True)
        print(f"\nSchlechteste Einheiten — {voice}:")
        for value, index, want, got in rows[:args.worst]:
            if value == 0:
                break
            print(f"  [{index}] {value * 100:3.0f}%  SOLL: {want[:78]}")
            print(f"              IST : {got[:78]}")


if __name__ == "__main__":
    main()
