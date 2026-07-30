"""Measure how fast F5-TTS actually speaks, so segment_speech.py can budget characters.

The rate is a property of the cloned voice, not of the model: a fast reference speaker
produces fast German. Measure it with the same reference clip you will synthesise
with, or the budgets will be wrong.

Take the p25 value, not the median. With the median half of all units come out too
long and get compressed. Calibration prose is also easier to speak than real material,
so the calibration figure carries a safety factor; the --cues figure, measured on the
actual translation, does not need one.

Usage:
    python measure_rate.py --ref refs/spk0.wav --ref-text "..." \
        --ckpt model_f5tts_german.safetensors --vocab vocab.txt
    python measure_rate.py --ref ... --cues cues_vo.json
"""

import argparse
import json
import statistics

import numpy as np

# Calibration sentences: plain German prose across a range of lengths, including
# the compounds and subordinate clauses that dominate spoken commentary.
CALIBRATION = [
    "Der Pegel ist niedrig.",
    "Darüber müssen wir noch sprechen.",
    "Das Kraftwerk liefert die Hälfte der Stromversorgung.",
    "Die Regierung hat die Lage seit Wochen gekannt.",
    "Man hätte den Strom deutlich früher einkaufen können.",
    "Es gibt hier eine klare Zwangslage, auf die jeder anders antwortet.",
    "Die Frage ist, ob wir mit den vorhandenen Mitteln trotzdem etwas anfangen.",
    "Wer die Ereignisse der letzten Wochen verfolgt hat, kennt die Vorwürfe.",
    "Eine sehr schlechte Entwicklung, von der man unbedingt zurückkommen müsste.",
    "Das sind langfristige Investitionen, und die Entscheidungen sind nicht leicht.",
    "Auf offiziellen Kanälen ist davon bisher nichts zu sehen gewesen.",
    "Er zeigt, wie die Landschaft vor tausend Jahren ausgesehen hat, mit weiten "
    "Feuchtgebieten und Auen entlang der großen Flüsse.",
    "Die Anwohner wollen vielleicht keinen Trockenturm, und es gibt daneben "
    "Nasskühltürme oder ergänzende Lösungen, die vor Ort Fragen aufwerfen.",
]

# Calibration prose is easier to speak than real material.
CALIBRATION_SAFETY = 0.92


def measure(tts, ref_file: str, ref_text: str, texts: list[str],
            seed: int) -> list[float]:
    """Synthesise each text with this voice and return characters per second."""
    quiet = lambda *a, **k: None
    rates = []
    for text in texts:
        wav, rate, _ = tts.infer(ref_file=ref_file, ref_text=ref_text,
                                 gen_text=text, show_info=quiet, progress=None,
                                 seed=seed)
        seconds = len(np.asarray(wav)) / rate
        if seconds > 0:
            rates.append(len(text) / seconds)
    return sorted(rates)


def report(rates: list[float], label: str, safety: float) -> float:
    """Print the distribution and return the rate to hand to segment_speech.py."""
    p25 = statistics.quantiles(rates, n=4)[0] if len(rates) >= 4 else min(rates)
    print(f"{len(rates)} Saetze gemessen ({label})")
    print(f"Zeichen/Sekunde  min : {min(rates):.1f}")
    print(f"                 p25 : {p25:.1f}")
    print(f"                 med : {statistics.median(rates):.1f}")
    print(f"                 max : {max(rates):.1f}")
    print(f"--rate: {p25 * safety:.1f}")
    return round(p25 * safety, 1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", help="single reference clip")
    parser.add_argument("--ref-text", help="transcript of --ref")
    parser.add_argument("--speakers",
                        help="speakers.json - measures every speaker at once")
    parser.add_argument("--update", action="store_true",
                        help="write the measured rate back into speakers.json")
    parser.add_argument("--only-missing", action="store_true",
                        help="skip speakers that already carry a rate — voices "
                             "taken from the library bring theirs along")
    parser.add_argument("--ckpt", required=True)
    parser.add_argument("--vocab", required=True)
    parser.add_argument("--cues", help="measure on real translated text instead")
    parser.add_argument("--count", type=int, default=13)
    parser.add_argument("--seed", type=int, default=1234)
    args = parser.parse_args()

    if not args.speakers and not (args.ref and args.ref_text):
        raise SystemExit("Entweder --speakers oder --ref plus --ref-text angeben.")

    if args.cues:
        with open(args.cues, encoding="utf-8") as handle:
            cues = json.load(handle)
        step = max(len(cues) // args.count, 1)
        texts = [cue["text"] for cue in cues[::step]][:args.count]
        label, safety = "Cues", 1.0
    else:
        texts = CALIBRATION
        label, safety = "Kalibriertext", CALIBRATION_SAFETY

    from f5_tts.api import F5TTS
    tts = F5TTS(model="F5TTS_Base", ckpt_file=args.ckpt, vocab_file=args.vocab)

    if not args.speakers:
        report(measure(tts, args.ref, args.ref_text, texts, args.seed),
               label, safety)
        print("\nDie Rate haengt an der Referenzstimme, nicht am Modell. Bei "
              "mehreren Sprechern\n--speakers benutzen, sonst bekommt der "
              "langsamste das Budget des schnellsten.")
        return

    with open(args.speakers, encoding="utf-8") as handle:
        data = json.load(handle)
    for entry in data["speakers"]:
        if args.only_missing and entry.get("rate"):
            print(f"\n=== Sprecher {entry['speaker']} === uebersprungen, Rate "
                  f"{entry['rate']} liegt vor"
                  + (f" ({entry['voice_id']})" if entry.get("voice_id") else ""))
            continue
        print(f"\n=== Sprecher {entry['speaker']} ===")
        rate = report(measure(tts, entry["ref_file"], entry["ref_text"],
                              texts, args.seed), label, safety)
        entry["rate"] = rate

    if args.update:
        with open(args.speakers, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=1)
        print(f"\nRaten in {args.speakers} geschrieben.")
        print("Jetzt segment_speech.py mit --speakers erneut laufen lassen - "
              "die Schnittpunkte\naendern sich dabei nicht, nur die Budgets.")
    else:
        print("\nOhne --update wurde nichts geschrieben.")

    spread = [entry["rate"] for entry in data["speakers"] if entry.get("rate")]
    if len(spread) > 1 and max(spread) / min(spread) > 1.15:
        print(f"\nDie Stimmen sprechen unterschiedlich schnell "
              f"({min(spread):.1f} bis {max(spread):.1f} Zeichen/s). "
              f"Ein gemeinsames Budget\nwaere fuer die langsame Stimme zu "
              f"grosszuegig - deshalb --speakers benutzen.")


if __name__ == "__main__":
    main()
