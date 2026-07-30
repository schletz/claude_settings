"""Judge every reference clip, and say whether the video holds a better one.

Two different situations look the same in speakers.json: a clip that is poor
because the automatic pick was unlucky, and a clip that is poor because the
person was recorded at a roadside and nothing better exists. The first is worth
fixing, the second only worth accepting — and telling the two apart is what this
script is for. It measures the chosen clip against the whole pool of clips that
could have been chosen for the same voice:

    Dichte     characters per second in the source, which predicts the clone
               rate almost one to one; the German band is roughly 11 to 19
    Rauschen   signal-to-noise inside the unit, from the gap between its quiet
               frames and its loud ones
    Satzgrenze whether the clip starts a sentence and ends one

A large gap between the chosen clip and the best candidate means a better clip
is there for the taking. A pool that is uniformly bad means the source is
exhausted; synthesise with what there is and say so in the report.

Only speakers who did not come out of the voice archive are examined — for the
others the question is already settled. Nothing here feeds the archive back:
filling it is a separate job the user asks for by name.

Usage:
    python check_refs.py <media> units.json refs/speakers.json
"""

import argparse
import json
import os
import subprocess
import sys

import numpy as np

from segment_speech import unit_text

RATE = 16000
FRAME = 400          # 25 ms at 16 kHz
HOP = 160            # 10 ms
CLIP_MIN = 6.0       # shorter units rarely carry a full sentence
CLIP_MAX = 10.5      # F5-TTS truncates past ~12 s, diarisation cuts at 11

# Characters per second in the source, the only property shown to predict the
# clone rate — it followed the clip within half a character per second across
# four measured clips. Candidates are ranked by it, never by noise.
#
# The band is where German clones land at all; DENSITY_GOOD is where they come
# out clean. The gap between the two is not cosmetic: at 13.4 a clip that broke
# no other rule still stuck a filler word in front of every third unit, while
# 17.9 and 18.4 were artefact-free. Anything in between is usable but worth
# replacing if the video holds something denser.
DENSITY_BAND = (11.0, 19.0)
DENSITY_GOOD = 16.0

# Noise is a veto, not a ranking key. The figure is the distance in dB between a
# unit's quiet frames and its loud ones, which in clean studio material runs to
# 40 dB and beyond — chasing the maximum would trade a good clip for a slow one.
#
# It is a coarse instrument, and three of its blind spots matter. It measures
# dynamic range as much as noise, so a loudness-normalised studio address scores
# lower than a raw studio recording: a scripted piece to camera came out at
# 18 dB while a panel discussion in the same quality class sat at 25 to 32. It
# does not see reverb, because a hall adds no energy in the pauses. And it does
# not see a music bed either — the two effects cancel, since music raises the
# quiet frames and the mix is compressed to make room for it. Measured on the
# same speaker: a speech with music under it scored 24.4 dB, his own clean studio
# address 18.4. The music-backed clip looked six decibels *better*.
#
# So the floor only rules out the clearly hopeless — a running engine, a road —
# and everything above it is decided by density and by ear. Background music is
# caught in step 2, not here; see probe_audio.py's pause profile.
SNR_POOR = 15.0


def load_mono(path: str) -> np.ndarray:
    """Decode the whole track to mono float32 at 16 kHz via ffmpeg."""
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-nostdin", "-i", path, "-vn",
         "-ac", "1", "-ar", str(RATE), "-f", "f32le", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float32).copy()


def snr_of(clip: np.ndarray) -> float:
    """Distance in dB between the quiet and the loud frames of one unit.

    Speech is not continuous: even a dense sentence has stops and breath pauses,
    and those frames carry the noise floor. Comparing the 10th against the 90th
    percentile of frame energy therefore separates the room from the voice
    without needing a silence detector. It only works on units long enough to
    contain pauses, which is why the pool is filtered by length first.
    """
    if len(clip) < FRAME * 4:
        return float("nan")
    frames = np.lib.stride_tricks.sliding_window_view(clip, FRAME)[::HOP]
    energy = np.sqrt(np.maximum((frames.astype(np.float64) ** 2).mean(axis=1), 1e-20))
    noise = float(np.quantile(energy, 0.10))
    speech = float(np.quantile(energy, 0.90))
    return 20.0 * float(np.log10(speech / max(noise, 1e-12)))


def clean_edges(text: str) -> bool:
    """Does the unit start a sentence and finish one?"""
    text = text.strip()
    return bool(text) and text[:1].isupper() and text[-1:] in ".!?"


def describe(clip: dict) -> str:
    faults = []
    if not clip["edges"]:
        faults.append("keine Satzgrenze")
    if clip["density"] < DENSITY_BAND[0]:
        faults.append("viel zu langsam")
    elif clip["density"] < DENSITY_GOOD:
        faults.append("traege")
    elif clip["density"] > DENSITY_BAND[1]:
        faults.append("sehr schnell")
    if clip["snr"] == clip["snr"] and clip["snr"] < SNR_POOR:
        faults.append("verrauscht")
    return ", ".join(faults) if faults else "gut"


def usable(clip: dict) -> bool:
    """Good enough to synthesise from without looking for a replacement."""
    return (clip["edges"] and clip["snr"] >= SNR_POOR
            and DENSITY_GOOD <= clip["density"] <= DENSITY_BAND[1])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media")
    parser.add_argument("units")
    parser.add_argument("speakers")
    parser.add_argument("--text-key")
    args = parser.parse_args()

    with open(args.units, encoding="utf-8") as handle:
        units = json.load(handle)
    with open(args.speakers, encoding="utf-8") as handle:
        data = json.load(handle)
    labels = data["labels"]

    text_of = ((lambda u: u[args.text_key]) if args.text_key else unit_text)
    audio = load_mono(args.media)

    def score(clip: np.ndarray, seconds: float, text: str, index) -> dict:
        return {"index": index, "seconds": seconds,
                "density": len(text) / seconds if seconds else 0.0,
                "snr": snr_of(clip), "edges": clean_edges(text), "text": text}

    def measure(index: int) -> dict:
        """One candidate unit, cut out of the decoded source."""
        unit = units[index]
        lo = max(int(unit["start"] * RATE), 0)
        hi = min(int(unit["end"] * RATE), len(audio))
        return score(audio[lo:hi], unit["end"] - unit["start"],
                     text_of(unit).strip(), index)

    def measure_file(path: str, text: str) -> dict:
        """The reference clip as it actually is on disk.

        Reading the wav instead of looking up ref_unit is what makes this survive
        a hand-cut replacement: after one, the index still points at the unit the
        automatic pick chose, and every figure derived from it describes a clip
        that is no longer in use.
        """
        clip = load_mono(path)
        return score(clip, len(clip) / RATE, text.strip(), None)

    for entry in data["speakers"]:
        number = entry["speaker"]
        name = entry.get("name", f"P{number}")
        print(f"\n=== {number}  {name} ===")

        if entry.get("voice_id"):
            print(f"  Stimme aus dem Archiv ({entry['voice_id']}) - "
                  f"nicht zu pruefen.")
            continue

        if not os.path.exists(entry["ref_file"]):
            print(f"  Clip fehlt: {entry['ref_file']}")
            continue

        chosen = entry.get("ref_unit")
        current = measure_file(entry["ref_file"], entry["ref_text"])
        print(f"  Clip     {os.path.basename(entry['ref_file']):12s} "
              f"{current['seconds']:5.1f}s  {current['density']:5.1f} z/s  "
              f"{current['snr']:5.1f} dB  -> {describe(current)}")
        print(f"           {current['text'][:70]}")

        eligible = [measure(i) for i, label in enumerate(labels)
                    if label == number and i != chosen
                    and CLIP_MIN <= units[i]["end"] - units[i]["start"] <= CLIP_MAX]
        eligible = [c for c in eligible if c["edges"] and c["snr"] == c["snr"]]
        quiet = [c for c in eligible if c["snr"] >= SNR_POOR]
        pool = [c for c in quiet if usable(c)]
        if eligible:
            print(f"  Pool     {len(eligible):3d} Kandidaten, davon "
                  f"{len(quiet)} ueber der Rauschgrenze und {len(pool)} auch "
                  f"dicht genug | SNR Median "
                  f"{np.median([c['snr'] for c in eligible]):.1f} dB")

        if usable(current):
            print("  -> Clip ist brauchbar, kein Wechsel noetig.")
        elif pool:
            # Highest density inside the band: the top of the band cloned clean
            # in every measured run, the bottom of it did not.
            candidate = max(pool, key=lambda c: c["density"])
            print(f"  -> Besserer Clip vorhanden: Einheit {candidate['index']} "
                  f"({candidate['seconds']:.1f}s, {candidate['density']:.1f} z/s, "
                  f"{candidate['snr']:.1f} dB)")
            print(f"     {candidate['text'][:70]}")
            print("     Lies den Wortlaut selbst gegen, bevor du schneidest - "
                  "eine Floskel am\n     Anfang ueberlebt jeden Filter.")
        elif quiet:
            candidate = max(quiet, key=lambda c: c["density"])
            if candidate["density"] <= current["density"]:
                print("  -> Nichts Besseres im Video: kein sauberer Kandidat "
                      "spricht dichter als der\n     aktuelle Clip. So "
                      "synthetisieren und die knappen Budgets einplanen.")
            else:
                print("  -> Kein Kandidat ist wirklich dicht genug. Der beste "
                      "verfuegbare:")
                print(f"     Einheit {candidate['index']} "
                      f"({candidate['density']:.1f} z/s, "
                      f"{candidate['snr']:.1f} dB) {candidate['text'][:50]}")
        else:
            print("  -> Kein besserer Clip im Video: alles ist zu kurz, ohne "
                  "Satzgrenze oder zu\n     verrauscht. Die Quelle gibt nicht "
                  "mehr her. Mit diesem Clip synthetisieren\n     und es im "
                  "Bericht erwaehnen — eine fremde Ersatzstimme klingt nicht "
                  "nach\n     dieser Person und ist selten der bessere Tausch.")


if __name__ == "__main__":
    sys.exit(main())
