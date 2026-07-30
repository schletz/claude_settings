"""Transcribe prepared audio variants with Whisper large-v3 on the GPU.

Three modes share a single model load:

  full     one long-form pass per variant, with segment timestamps; --max-chunk splits
           long files at speech pauses so the decoder does not abort
  windows  overlapping short windows, every window decoded from every variant, so
           stable readings can be told apart from filter artefacts
  zoom     targeted re-decoding of individual spans, optionally time-stretched

Usage:
    python transcribe.py <workdir> --mode full    --variants clean --lang hu --out full.txt
    python transcribe.py <workdir> --mode full    --variants raw --lang hu --words \
        --max-chunk 300 --json words.json
    python transcribe.py <workdir> --mode windows --variants clean gentle left --lang hu
    python transcribe.py <workdir> --mode zoom    --spans "130-150@0.75" --lang hu
"""

import argparse
import json
import os
import re
import subprocess
import sys

import numpy as np
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

# Filler phrases Whisper hallucinates over noise or silence, per training-data artefacts.
FILLERS = [
    "köszönöm, hogy megnézt", "jó napot kívánok", "feliratozta", "feliratot",
    "untertitel von", "untertitelung", "vielen dank für", "abonniert",
    "thanks for watching", "subscribe", "subtitles by", "amara.org",
    "sous-titres", "sottotitoli", "subtítulos", "napisy", "titulky",
    "продолжение следует", "субтитры",
]


def is_suspicious(text: str) -> str | None:
    """Return a reason string if the text looks hallucinated, else None."""
    stripped = text.strip()
    if not stripped:
        return None
    lowered = stripped.lower()
    for filler in FILLERS:
        if filler in lowered:
            return "Floskel-Halluzination"
    words = stripped.split()
    # A short phrase repeated many times is the classic noise-loop signature.
    for size in range(1, 6):
        if len(words) < size * 4:
            break
        phrase = " ".join(words[:size])
        if len(phrase) > 2 and lowered.count(phrase.lower()) >= 4:
            return f"Wiederholungsschleife ({phrase!r})"
    unique_ratio = len(set(w.lower() for w in words)) / max(len(words), 1)
    if len(words) >= 20 and unique_ratio < 0.25:
        return "sehr geringe Wortvielfalt"
    return None


def stamp(seconds) -> str:
    """Format seconds as MM:SS, tolerating the None Whisper emits for open segments."""
    if seconds is None:
        return "  ?  "
    return f"{int(seconds) // 60:02d}:{int(seconds) % 60:02d}"


def read_slice(path: str, start: float, length: float, tempo: float = 1.0) -> np.ndarray:
    """Decode a time slice, optionally time-stretched, as a 16 kHz mono float32 array."""
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-ss", str(start), "-t", str(length),
           "-i", path]
    if tempo != 1.0:
        cmd += ["-af", f"atempo={tempo}"]
    cmd += ["-ar", "16000", "-ac", "1", "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


# Silence thresholds tried in order, quietest first. A recording made outdoors or in a
# hall never drops to -32 dB between sentences, so that threshold alone would report no
# pauses at all - and a single oversized chunk is exactly what kills the decoder.
SILENCE_STEPS = (-32.0, -28.0, -24.0, -20.0)


def detect_pauses(path: str, threshold: float) -> list[float]:
    """Return the midpoints of all silences ffmpeg detects at the given threshold."""
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-nostdin", "-i", path,
         "-af", f"silencedetect=noise={threshold}dB:d=0.25", "-f", "null", "-"],
        capture_output=True, text=True, errors="replace", check=False,
    )
    marks = [float(m) for m in re.findall(r"silence_(?:start|end): ([0-9.]+)", proc.stderr)]
    return [(marks[i] + marks[i + 1]) / 2 for i in range(0, len(marks) - 1, 2)]


def cut_at_pauses(pauses: list[float], duration: float, target: float) -> list[float]:
    """Place chunk boundaries near multiples of `target`, each inside a given pause."""
    cuts = [0.0]
    while duration - cuts[-1] > target * 1.5:
        goal = cuts[-1] + target
        window = [p for p in pauses
                  if cuts[-1] + target * 0.2 < p < cuts[-1] + target * 1.5]
        if not window:
            break
        cuts.append(min(window, key=lambda p: abs(p - goal)))
    cuts.append(duration)
    return cuts


def longest_block(cuts: list[float]) -> float:
    """Length of the largest chunk a cut list produces - the number that decides."""
    return max(end - start for start, end in zip(cuts, cuts[1:]))


def find_cut_points(path: str, duration: float, target: float,
                    silence_db: float | None = None) -> list[float]:
    """Pick chunk boundaries near multiples of `target`, each inside a speech pause.

    Cutting mid-word costs a word per boundary, so every cut is placed in the middle of
    a silence that ffmpeg detected. If the quietest threshold does not split the file,
    the threshold is raised step by step: what matters is finding the quietest moments
    relative to this recording, not an absolute level.

    The decision is made on the resulting block length, not on the number of pauses. A
    threshold can report dozens of pauses that all sit in the first few seconds - plenty
    of pauses, still one oversized block.
    """
    if silence_db is not None:
        return cut_at_pauses(detect_pauses(path, silence_db), duration, target)

    best = None
    for threshold in SILENCE_STEPS:
        cuts = cut_at_pauses(detect_pauses(path, threshold), duration, target)
        if longest_block(cuts) <= target * 1.5:
            return cuts
        if best is None or longest_block(cuts) < longest_block(best):
            best = cuts
    print(f"WARNUNG: Auch bei {SILENCE_STEPS[-1]:.0f} dB bleibt der laengste Block bei "
          f"{longest_block(best) / 60:.1f} Minuten. Bei einem Abbruch (Exitcode 5) die "
          "Bloecke von Hand schneiden - siehe SKILL.md, Schritt 4.", file=sys.stderr)
    return best


def decode_variant(asr, path: str, lang: str | None, duration: float,
                   max_chunk: float, silence_db: float | None = None
                   ) -> tuple[str, list[dict]]:
    """Decode one variant end to end, chunking the file if it is too long.

    The long-form pass with word timestamps dies on very long inputs (observed: a hard
    process abort at 42 minutes, while 25 minutes still worked). Chunking at pauses
    keeps every decode small enough; the timestamps are shifted back to absolute time.
    """
    kwargs = generate_kwargs(lang, long_form=True)
    if not max_chunk or duration <= max_chunk * 1.5:
        result = asr(path, generate_kwargs=kwargs)
        return result["text"].strip(), result.get("chunks", [])

    cuts = find_cut_points(path, duration, max_chunk, silence_db)
    blocks = len(cuts) - 1
    print(f"{os.path.basename(path)}: {blocks} Bloecke", file=sys.stderr)
    if blocks < duration // max_chunk:
        print(f"WARNUNG: {blocks} Bloecke fuer {duration / 60:.0f} Minuten - einzelne "
              "Bloecke sind deutlich laenger als --max-chunk und koennen den Dekoder "
              "hart abbrechen lassen (Exitcode 5). Mit --silence-db nachhelfen.",
              file=sys.stderr)
    texts: list[str] = []
    collected: list[dict] = []
    for start, end in zip(cuts, cuts[1:]):
        length = end - start
        result = asr(read_slice(path, start, length), generate_kwargs=kwargs)
        texts.append(result["text"].strip())
        for chunk in result.get("chunks", []):
            begin, finish = chunk["timestamp"]
            if begin is None:
                continue
            if finish is None or finish < begin:
                finish = begin
            # Clamp before shifting: Whisper sometimes stamps past the end of a slice.
            collected.append({"text": chunk["text"],
                              "timestamp": (min(begin, length) + start,
                                            min(finish, length) + start)})
        print(f"  {stamp(start)}-{stamp(end)}: {len(result.get('chunks', []))} Einheiten",
              file=sys.stderr)
    return " ".join(texts), collected


def media_duration(path: str) -> float:
    """Return the duration of a media file in seconds."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def parse_span(spec: str) -> tuple[float, float, float]:
    """Parse a '<start>-<end>[@<tempo>]' span specification into seconds and tempo."""
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*(?:@\s*(\d*\.?\d+))?\s*",
                         spec)
    if not match:
        sys.exit(f"Ungueltige Span-Angabe: {spec!r} (erwartet z. B. '130-150@0.75')")
    start, end, tempo = match.group(1), match.group(2), match.group(3)
    return float(start), float(end), float(tempo) if tempo else 1.0


def build_pipelines(model_id: str, word_timestamps: bool = False):
    """Load the model once and return (long-form pipeline, short-clip pipeline)."""
    if not torch.cuda.is_available():
        print("WARNUNG: keine CUDA-GPU gefunden - Lauf wird sehr langsam.", file=sys.stderr)
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device.startswith("cuda") else torch.float32

    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id, dtype=dtype, low_cpu_mem_usage=True, use_safetensors=True
    ).to(device)
    processor = AutoProcessor.from_pretrained(model_id)
    common = dict(model=model, tokenizer=processor.tokenizer,
                  feature_extractor=processor.feature_extractor,
                  torch_dtype=dtype, device=device)
    granularity = "word" if word_timestamps else True
    return (pipeline("automatic-speech-recognition", return_timestamps=granularity, **common),
            pipeline("automatic-speech-recognition", **common))


def generate_kwargs(lang: str | None, long_form: bool) -> dict:
    """Assemble decoding parameters; long-form adds the noise-robust fallback ladder."""
    kwargs = {"task": "transcribe", "num_beams": 5, "repetition_penalty": 1.15}
    if lang:
        kwargs["language"] = lang
    if long_form:
        kwargs.update({
            # Do not let one hallucinated segment poison the rest of the run.
            "condition_on_prev_tokens": False,
            "temperature": (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
            "logprob_threshold": -1.0,
            "compression_ratio_threshold": 1.35,
            "no_speech_threshold": 0.6,
        })
    return kwargs


def mode_full(asr, workdir, variants, lang, out, json_out, clip, words,
              duration=0.0, max_chunk=0.0, silence_db=None) -> None:
    """Run one long-form pass per variant and write timestamped segments or words."""
    collected = {}
    for variant in variants:
        path = os.path.join(workdir, f"{variant}.wav")
        text, chunks = decode_variant(asr, path, lang, duration, max_chunk, silence_db)
        collected[variant] = chunks
        out.write(f"################ {variant} ################\n")
        if words:
            # Word granularity is for timing, not for reading - print the plain text.
            out.write(text + "\n")
        else:
            for chunk in collected[variant]:
                line = chunk["text"].strip()
                flag = is_suspicious(line)
                marker = f"  <<WARN {flag}>>" if flag else ""
                out.write(f"[{stamp(chunk['timestamp'][0])}] {line[:clip]}{marker}\n")
        out.write("\n")
        out.flush()
    if json_out:
        payload = {
            variant: [{"start": c["timestamp"][0], "end": c["timestamp"][1],
                       "text": c["text"].strip()} for c in chunks]
            for variant, chunks in collected.items()
        }
        with open(json_out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        kind = "Wortzeiten" if words else "Segmente"
        print(f"{kind} als JSON: {json_out}")


def mode_windows(asr, workdir, variants, lang, out, window, step, duration, clip) -> None:
    """Decode overlapping windows from every variant so readings can be compared."""
    kwargs = generate_kwargs(lang, long_form=False)
    start = 0.0
    while start < duration:
        length = min(window, duration - start)
        out.write(f"===== {stamp(start)} ({start:.0f}-{start + length:.0f}s) =====\n")
        for variant in variants:
            audio = read_slice(os.path.join(workdir, f"{variant}.wav"), start, length)
            text = asr(audio, generate_kwargs=kwargs)["text"].strip()
            flag = is_suspicious(text)
            marker = f"  <<WARN {flag}>>" if flag else ""
            out.write(f"  {variant:11} {text[:clip]}{marker}\n")
        out.flush()
        start += step


def mode_zoom(asr, workdir, variants, lang, out, spans, clip) -> None:
    """Re-decode individual spans, optionally slowed down, to resolve doubtful passages."""
    kwargs = generate_kwargs(lang, long_form=False)
    for spec in spans:
        begin, end, tempo = parse_span(spec)
        out.write(f"######## {stamp(begin)} ({begin}-{end}s) tempo={tempo} ########\n")
        for variant in variants:
            audio = read_slice(os.path.join(workdir, f"{variant}.wav"),
                               begin, end - begin, tempo)
            text = asr(audio, generate_kwargs=kwargs)["text"].strip()
            flag = is_suspicious(text)
            marker = f"  <<WARN {flag}>>" if flag else ""
            out.write(f"  {variant:11} {text[:clip]}{marker}\n")
        out.write("\n")
        out.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workdir", help="directory holding the prepared <variant>.wav files")
    parser.add_argument("--mode", choices=["full", "windows", "zoom"], required=True)
    parser.add_argument("--variants", nargs="+", required=True)
    parser.add_argument("--lang", help="ISO 639-1 code, e.g. hu; omit to auto-detect")
    parser.add_argument("--model", default="openai/whisper-large-v3")
    parser.add_argument("--out", help="output file (default: stdout)")
    parser.add_argument("--json", dest="json_out", help="full mode: segment JSON export")
    parser.add_argument("--words", action="store_true",
                        help="full mode: word-level timestamps, for precise cue timing")
    parser.add_argument("--max-chunk", type=float, default=0.0,
                        help="full mode: split files longer than this into pause-aligned "
                             "chunks (seconds, 0 = off). Required above ~30 minutes.")
    parser.add_argument("--silence-db", type=float,
                        help="full mode: fixed silence threshold for the chunker "
                             "(e.g. -24). Default: try -32 to -20 until enough pauses "
                             "are found. probe_audio.py reports the fitting value.")
    parser.add_argument("--window", type=float, default=20.0)
    parser.add_argument("--step", type=float, default=15.0)
    parser.add_argument("--spans", nargs="*", default=[],
                        help="zoom mode: '<start>-<end>[@tempo]' entries")
    parser.add_argument("--clip", type=int, default=400,
                        help="truncate each printed line to N characters")
    args = parser.parse_args()

    for variant in args.variants:
        path = os.path.join(args.workdir, f"{variant}.wav")
        if not os.path.isfile(path):
            sys.exit(f"Fehlende Variante: {path} (erst prepare_audio.py laufen lassen)")
    if args.mode == "zoom" and not args.spans:
        sys.exit("Modus 'zoom' braucht mindestens einen --spans Eintrag.")
    for spec in args.spans:
        begin, end, _ = parse_span(spec)
        # Beyond 30 s the short-clip pipeline switches to long-form and demands timestamps.
        if end - begin > 30:
            sys.exit(f"Span {spec!r} ist laenger als 30 s - bitte aufteilen.")

    if args.words and args.mode != "full":
        sys.exit("--words gibt es nur im Modus 'full'.")
    reference = os.path.join(args.workdir, f"{args.variants[0]}.wav")
    duration = media_duration(reference)
    if args.mode == "full" and not args.max_chunk and duration > 1800:
        print(f"WARNUNG: {duration / 60:.0f} Minuten ohne --max-chunk. Lange Dateien "
              "brechen im Langform-Durchlauf hart ab - empfohlen: --max-chunk 300.",
              file=sys.stderr)
    asr_long, asr_short = build_pipelines(args.model, word_timestamps=args.words)

    out = open(args.out, "w", encoding="utf-8") if args.out else sys.stdout
    try:
        if args.mode == "full":
            mode_full(asr_long, args.workdir, args.variants, args.lang, out,
                      args.json_out, args.clip, args.words, duration, args.max_chunk,
                      args.silence_db)
        elif args.mode == "windows":
            mode_windows(asr_short, args.workdir, args.variants, args.lang, out,
                         args.window, args.step, duration, args.clip)
        else:
            mode_zoom(asr_short, args.workdir, args.variants, args.lang, out,
                      args.spans, args.clip)
    finally:
        if args.out:
            out.close()
            print(f"Geschrieben: {args.out}")


if __name__ == "__main__":
    main()
