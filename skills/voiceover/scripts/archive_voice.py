"""Put one person's voice into the library, from a URL or a file and a time range.

This stands apart from the voice-over pipeline on purpose. Whether a voice is
worth keeping and which passage represents it well are judgements a person makes
better than a measurement: you know that a minister will keep turning up, and you
can hear that the passage at 1:00 is him speaking calmly rather than being shouted
over. So you name the range, and the script does the mechanical part.

    python archive_voice.py "https://www.youtube.com/watch?v=..." \
        --from 1:00 --to 2:00 --name "Magyar Peter" --lang hu

Inside the range it still has to choose, because F5-TTS truncates a reference past
twelve seconds: it transcribes the range, cuts it into speech units, and joins a
run of them that starts and ends on a sentence, speaks at the right tempo — density
sets the clone's speaking rate — and is as long as that allows. Then it measures
that rate once, averages an ECAPA embedding over the whole range as the
fingerprint, and writes the entry.

Give it a minute or more of speech if you can. The clip is one sentence either
way, but the fingerprint is the average over everything in the range, and an
average over more material recognises the person again under a different
microphone.
"""

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np

import voice_library as lib
from check_refs import DENSITY_BAND, DENSITY_GOOD, clean_edges
from segment_speech import unit_text

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "hvoss-techfak/F5-TTS-German"
CKPT = "model_f5tts_german.safetensors"
VOCAB = "vocab.txt"

CLIP_MIN = 4.0
CLIP_WANTED = 6.0    # below this the clone gets thin; above it length stops helping
CLIP_MAX = 11.0
MAX_GAP = 0.6        # longer pauses must not end up inside the reference clip
THIN_RANGE = 30.0    # below this the fingerprint rests on very little material

# Seconds of audio transcribed on either side of the requested range, used for
# context only: no clip is cut from it and no embedding is averaged over it.
#
# The clip is chosen by sentence boundaries, and Whisper's punctuation depends on
# what surrounds a sentence. Transcribing a range in isolation therefore finds
# different — and measurably worse — candidates than transcribing it in context.
# Measured on the same 116 seconds: alone it yielded a single usable clip at 12.5
# characters per second, in context a 10.1 s one at 18.3, which is the difference
# between a sluggish clone and a good one.
CONTEXT_PAD = 45.0


def parse_time(value: str) -> float:
    """Accept 90, 1:30 and 1:02:03 alike."""
    parts = value.strip().split(":")
    if not all(parts):
        raise SystemExit(f"Zeitangabe unverstaendlich: {value!r}")
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + float(part)
    return seconds


def run(*command: str) -> None:
    subprocess.run([sys.executable, *command], check=True,
                   env={**os.environ, "PYTHONIOENCODING": "utf-8"})


def cut(source: str, target: str, rate: int, start: float | None = None,
        duration: float | None = None) -> None:
    """Render a mono WAV of one stretch of the source."""
    command = ["ffmpeg", "-y", "-v", "error", "-nostdin"]
    if start is not None:
        command += ["-ss", f"{start:.3f}"]
    if duration is not None:
        command += ["-t", f"{duration:.3f}"]
    command += ["-i", source, "-vn", "-ac", "1", "-ar", str(rate),
                "-c:a", "pcm_s16le", target]
    subprocess.run(command, check=True)


def fetch_audio(url: str, start: float, end: float,
                workdir: str) -> tuple[str, str, bool]:
    """Download the original-language audio, ideally only the wanted stretch.

    The language matters more here than anywhere else in the skill: YouTube serves
    machine-dubbed alternate tracks for many videos, and a dub archived under a
    person's name would put a synthetic voice into the library permanently.
    fetch_source.py already knows how to find the original track, so its choice is
    reused rather than reimplemented.

    Fetching only the range is the fast path, but it lets ffmpeg pull the byte
    range straight from the CDN, and YouTube answers that with a sporadic 403 —
    the same flakiness fetch_source.py retries around. After a couple of tries the
    whole track is downloaded and cut locally: slower, but it always works.
    Returns whether the file is already trimmed to the range.
    """
    import fetch_source as fs

    meta = fs.probe(url, [])
    auds = fs.audio_formats(meta)
    original = fs.original_language(auds)
    chosen, reason = fs.pick_audio(auds, original, None)
    if chosen is None:
        raise SystemExit(reason or "Keine brauchbare Tonspur gefunden.")
    lang = meta.get("language") or meta.get("original_language") or ""
    print(f"Quelle     : {meta.get('title')}")
    print(f"Tonspur    : {chosen['format_id']} {chosen.get('acodec')} "
          f"lang={chosen.get('language')}")

    base = [sys.executable, "-m", "yt_dlp", "--no-warnings", "--no-playlist",
            "-f", str(chosen["format_id"])]
    for attempt in range(2):
        done = subprocess.run(
            base + ["--download-sections", f"*{start:.2f}-{end:.2f}",
                    "-o", os.path.join(workdir, "section.%(ext)s"), url])
        got = [f for f in os.listdir(workdir) if f.startswith("section.")]
        if done.returncode == 0 and got:
            return os.path.join(workdir, got[0]), lang, True
        for stale in got:
            os.remove(os.path.join(workdir, stale))
        print(f"Bereichsabruf gescheitert (Versuch {attempt + 1} von 2).")

    print("Faellt auf den vollen Tonspur-Download zurueck.")
    subprocess.run(base + ["-o", os.path.join(workdir, "full.%(ext)s"), url],
                   check=True)
    got = [f for f in os.listdir(workdir) if f.startswith("full.")]
    if not got:
        raise SystemExit("yt-dlp hat keine Tonspur geschrieben.")
    return os.path.join(workdir, got[0]), lang, False


def candidates(units: list[dict]) -> list[dict]:
    """Every stretch of consecutive units that could serve as a reference clip.

    A clip is not required to be one unit. Segmentation cuts at sentence ends, so
    a two-minute range often holds nothing but three- and four-second units, and
    insisting on a single one caps the clip far below what F5-TTS can use. Runs of
    units are joined instead — but only across short pauses, because a long
    silence inside the reference is itself a defect the clone copies.
    """
    found = []
    for first in range(len(units)):
        if not unit_text(units[first]).strip()[:1].isupper():
            continue
        text = ""
        for last in range(first, len(units)):
            if last > first:
                gap = units[last]["start"] - units[last - 1]["end"]
                if gap > MAX_GAP:
                    break
            seconds = units[last]["end"] - units[first]["start"]
            if seconds > CLIP_MAX:
                break
            text = (text + " " + unit_text(units[last]).strip()).strip()
            if seconds < CLIP_MIN or not clean_edges(text):
                continue
            found.append({"index": first, "start": units[first]["start"],
                          "seconds": seconds, "density": len(text) / seconds,
                          "text": text, "edges": True})
    return found


def pick_clip(units: list[dict]) -> dict:
    """The stretch that makes the best reference: whole sentences, right tempo."""
    scored = candidates(units)
    if not scored:
        # Fall back to single units, ignoring sentence boundaries, so the run
        # produces something the user can listen to and judge.
        for index, unit in enumerate(units):
            seconds = unit["end"] - unit["start"]
            text = unit_text(unit).strip()
            if CLIP_MIN <= seconds <= CLIP_MAX and seconds:
                scored.append({"index": index, "start": unit["start"],
                               "seconds": seconds, "density": len(text) / seconds,
                               "text": text, "edges": clean_edges(text)})
    if not scored:
        raise SystemExit("Im Zeitbereich liegt kein Abschnitt zwischen "
                         f"{CLIP_MIN:.0f} und {CLIP_MAX:.0f} Sekunden. "
                         "Nimm einen laengeren Bereich.")

    whole = [c for c in scored if c["edges"]]
    if not whole:
        print("WARNUNG: keine Einheit im Bereich beginnt und endet auf einem "
              "ganzen Satz.\n         Der Klon bekommt davon leicht ein Fuellwort "
              "vorgeklebt - anderen Bereich\n         waehlen, wenn das Ergebnis "
              "stoert.")
        whole = scored

    in_band = [c for c in whole if DENSITY_GOOD <= c["density"] <= DENSITY_BAND[1]]
    if in_band:
        # Longest, not densest. Density decides the clone's speaking rate, and
        # every candidate here already sits in the right band — so the remaining
        # question is how much voice F5-TTS gets to work from. Ranking by density
        # inside the band quietly favours short units and produced a 4.3 s clip
        # where a 9 s one was available.
        long_enough = [c for c in in_band if c["seconds"] >= CLIP_WANTED]
        return max(long_enough or in_band, key=lambda c: c["seconds"])
    # Nothing in the good band: take the densest, which is the closest we get.
    best = max(whole, key=lambda c: c["density"])
    print(f"WARNUNG: dichtester Kandidat liegt bei {best['density']:.1f} Zeichen/s, "
          f"das Band ist\n         {DENSITY_GOOD:.0f} bis {DENSITY_BAND[1]:.0f}. "
          f"Der Klon spricht entsprechend langsam oder hastig.")
    return best


def checkpoint() -> tuple[str, str]:
    """Where the German checkpoint lives, downloading it into the HF cache once."""
    from huggingface_hub import hf_hub_download
    return hf_hub_download(REPO, CKPT), hf_hub_download(REPO, VOCAB)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="URL oder lokale Datei")
    parser.add_argument("--from", dest="start", required=True, metavar="ZEIT")
    parser.add_argument("--to", dest="end", required=True, metavar="ZEIT")
    parser.add_argument("--name", required=True)
    parser.add_argument("--id", help="default: aus --name gebildet")
    parser.add_argument("--note", default="", help="Rolle oder Kontext")
    parser.add_argument("--origin",
                        help="Herkunft fuer den Eintrag, wenn source eine lokale "
                             "Kopie ist — sonst steht dort nur ein Dateiname, "
                             "der spaeter niemandem mehr sagt, woher der Clip kam")
    parser.add_argument("--lang", help="Sprache im Clip, z. B. hu")
    parser.add_argument("--library", default=lib.default_dir())
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--keep", help="Arbeitsordner behalten statt loeschen")
    args = parser.parse_args()

    start, end = parse_time(args.start), parse_time(args.end)
    if end <= start:
        raise SystemExit("--to liegt nicht hinter --from.")
    span = end - start

    voice_id = args.id or lib.slug(args.name)
    if not voice_id:
        raise SystemExit("Aus --name laesst sich keine id bilden, --id angeben.")
    index = lib.load(args.library)
    existing = next((v for v in index["voices"] if v["id"] == voice_id), None)
    if existing and not args.replace:
        raise SystemExit(f"'{voice_id}' liegt schon im Archiv "
                         f"(aus {existing.get('source') or 'unbekannt'}).\n"
                         f"Zum Ersetzen --replace angeben.")
    if span < THIN_RANGE:
        print(f"Hinweis    : {span:.0f} s sind wenig. Der Clip wird trotzdem gut, "
              f"aber der\n             Fingerabdruck ruht auf wenig Material und "
              f"erkennt die Person\n             unter anderem Mikrofon schlechter "
              f"wieder.")

    workdir = args.keep or tempfile.mkdtemp(prefix="voice_")
    os.makedirs(workdir, exist_ok=True)
    try:
        # The window is the range plus context on both sides; the range keeps its
        # own bounds inside it, expressed relative to the window start.
        pad_before = min(CONTEXT_PAD, start)
        window_start = start - pad_before
        window_span = span + pad_before + CONTEXT_PAD
        if "://" in args.source:
            media, meta_lang, trimmed = fetch_audio(
                args.source, window_start, window_start + window_span, workdir)
            offset, length = ((None, None) if trimmed
                              else (window_start, window_span))
        else:
            media, meta_lang = args.source, ""
            offset, length = window_start, window_span
        lang = args.lang or meta_lang
        if not lang:
            raise SystemExit("Sprache unbekannt - --lang angeben, damit Whisper "
                             "nicht raet.")

        cut(media, os.path.join(workdir, "raw.wav"), 16000, offset, length)
        clip_source = os.path.join(workdir, "src24.wav")
        cut(media, clip_source, lib.REF_RATE, offset, length)

        print(f"\nZeitbereich: {args.start} - {args.end}  ({span:.0f} s), "
              f"Sprache {lang}")
        print(f"             transkribiert mit {pad_before:.0f} s davor und "
              f"{CONTEXT_PAD:.0f} s danach als Kontext")
        run(os.path.join(HERE, "transcribe.py"), workdir, "--mode", "full",
            "--variants", "raw", "--lang", lang, "--words", "--max-chunk", "240",
            "--out", os.path.join(workdir, "words.txt"),
            "--json", os.path.join(workdir, "words.json"))
        run(os.path.join(HERE, "segment_speech.py"),
            os.path.join(workdir, "words.json"), os.path.join(workdir, "units.json"),
            "--rate", "14", "--duration", f"{window_span:.0f}")

        with open(os.path.join(workdir, "units.json"), encoding="utf-8") as handle:
            window_units = json.load(handle)
        # Only what the user vouched for counts: the padding gave Whisper context
        # and nothing else. It may well hold another speaker.
        units = [u for u in window_units
                 if u["start"] >= pad_before - 0.05
                 and u["end"] <= pad_before + span + 0.05]
        if not units:
            raise SystemExit("Im Zeitbereich liegt keine vollstaendige "
                             "Sprech-Einheit. Nimm einen laengeren Bereich.")
        clip = pick_clip(units)
        print(f"\nClip       : {clip['seconds']:.1f}s ab "
              f"{clip['start'] - pad_before:.1f}s im Bereich, "
              f"{clip['density']:.1f} Zeichen/s")
        print(f"             {clip['text'][:70]}")

        os.makedirs(args.library, exist_ok=True)
        audio = f"{voice_id}.wav"
        cut(clip_source, os.path.join(args.library, audio), lib.REF_RATE,
            clip["start"], clip["seconds"])

        # Embed the range only, never the context padding — the padding exists to
        # punctuate sentences and may hold a different speaker. Times stay relative
        # to raw.wav, which is the whole window.
        range_units = os.path.join(workdir, "units_range.json")
        with open(range_units, "w", encoding="utf-8") as handle:
            json.dump(units, handle, ensure_ascii=False)
        run(os.path.join(HERE, "embed_units.py"), os.path.join(workdir, "raw.wav"),
            range_units, os.path.join(workdir, "emb.npy"))
        embeddings = np.load(os.path.join(workdir, "emb.npy"))

        ckpt, vocab = checkpoint()
        from f5_tts.api import F5TTS
        from measure_rate import CALIBRATION, CALIBRATION_SAFETY, measure, report
        tts = F5TTS(model="F5TTS_Base", ckpt_file=ckpt, vocab_file=vocab)
        print()
        rate = report(measure(tts, os.path.join(args.library, audio), clip["text"],
                              CALIBRATION, 1234), "Kalibriertext", CALIBRATION_SAFETY)

        voice = {
            "id": voice_id,
            "name": args.name,
            "note": args.note,
            "audio": audio,
            "ref_text": clip["text"],
            "ref_lang": lang,
            "ref_seconds": round(clip["seconds"], 2),
            "rate": rate,
            "source": args.origin or args.source,
            "source_range": [round(start, 1), round(end, 1)],
            "from_units": len(units),
            "added": datetime.date.today().isoformat(),
            "embedding": [round(float(x), 6) for x in
                          lib.centroid(embeddings, range(len(units)))],
        }
        index["voices"] = [v for v in index["voices"]
                           if v["id"] != voice_id] + [voice]
        index["voices"].sort(key=lambda v: v["id"])
        index["model"] = index.get("model") or REPO
        lib.save(args.library, index)
    finally:
        if not args.keep:
            shutil.rmtree(workdir, ignore_errors=True)

    print(f"\n'{voice_id}' gespeichert in {args.library}")
    print(f"  Clip   {audio}  {clip['seconds']:.1f}s  {lib.REF_RATE} Hz mono")
    print(f"  Rate   {rate} Zeichen/s")
    print(f"  Basis  {len(units)} Einheiten aus {span:.0f} s")
    print(f"\nJetzt {lib.count(len(index['voices']))} im Archiv.")



if __name__ == "__main__":
    sys.exit(main())
