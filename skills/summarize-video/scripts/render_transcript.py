"""Turn the word-level JSON of `transcribe.py --words` into a readable transcript.

The summary is written from the transcript, so the transcript has to be
readable: a single wall of text costs the reader every timestamp, and one line
per word costs the context window. This groups words into paragraphs of roughly
forty seconds, cut at the first sentence end past that mark, and stamps each
paragraph with its start time.

Speech pauses are deliberately not part of the decision, because Whisper's
word-level end times carry no pauses to speak of. Measured over a twelve-minute
English monologue: median gap between two words 0.00 s, 99th percentile 0.16 s,
largest gap in the whole file 0.40 s. Over a German monologue, the median gap
after a sentence end was likewise 0.00 s. A pause criterion never fires; the
length cap would do all the work anyway, with an extra knob to get wrong.

Punctuation is the only real signal, and it is thin: the same English file held
31 sentence ends for 2779 words, with up to 222 s between two of them. That is
why the hard cap sits at one and a half times the target rather than higher -
without it, a fast speaker produces paragraphs minutes long.

The word timestamps are kept for exactly one reason: they are what
`check_coverage.py` needs to find passages the decoder silently dropped. A
paragraph-level rendering alone would hide those.

Usage:
    python render_transcript.py words.json --out transcript.txt
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys

# A paragraph may end here; anything else mid-sentence would read as a cut.
SENTENCE_END = '.!?…:'


def load_words(path: str, variant: str | None) -> list[dict]:
    """Read a words.json written by transcribe.py and return one variant's words."""
    with open(path, encoding='utf-8') as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        key = variant or next(iter(data))
        if key not in data:
            sys.exit(f'Variante {key!r} nicht in {path}. Vorhanden: {", ".join(data)}')
        words = data[key]
    else:
        words = data
    usable = [w for w in words if w.get('start') is not None and w.get('text', '').strip()]
    if not usable:
        sys.exit('Keine brauchbaren Wortzeiten gefunden.')
    return usable


def stamp(seconds: float) -> str:
    """Format seconds as MM:SS, or H:MM:SS beyond the hour."""
    total = int(seconds)
    if total >= 3600:
        return f'{total // 3600}:{total // 60 % 60:02d}:{total % 60:02d}'
    return f'{total // 60:02d}:{total % 60:02d}'


def ends_sentence(word: dict) -> bool:
    """True if the word carries closing punctuation."""
    return word['text'].strip().endswith(tuple(SENTENCE_END))


def should_break(word: dict, length: float, target: float) -> bool:
    """Decide whether the paragraph ends after this word.

    The first sentence end past the target length wins. The hard cap catches
    material that is punctuated so sparsely that no sentence end arrives - a
    fast speaker can run minutes without one, and an unbroken block that long is
    unusable.
    """
    if length >= target and ends_sentence(word):
        return True
    return length >= target * 1.5


def paragraphs(words: list[dict], target: float) -> list[tuple[float, str]]:
    """Group words into (start time, text) paragraphs."""
    out: list[tuple[float, str]] = []
    current: list[dict] = []
    for index, word in enumerate(words):
        current.append(word)
        last = index + 1 == len(words)
        if last or should_break(word, word['end'] - current[0]['start'], target):
            text = ' '.join(w['text'].strip() for w in current)
            out.append((current[0]['start'], text))
            current = []
    return out


def main() -> None:
    """Render the transcript and report how it came out."""
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('words_json')
    ap.add_argument('--variant', help='Tonvariante; Vorgabe ist die erste im JSON')
    ap.add_argument('--out', help='Zieldatei; Vorgabe ist die Standardausgabe')
    ap.add_argument('--target', type=float, default=40.0,
                    help='angestrebte Absatzlaenge in Sekunden; umgebrochen wird '
                         'an der naechsten Satzgrenze danach')
    args = ap.parse_args()

    words = load_words(args.words_json, args.variant)
    paras = paragraphs(words, args.target)

    lines = [f'[{stamp(start)}] {text}' for start, text in paras]
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as fh:
            fh.write('\n\n'.join(lines) + '\n')
    else:
        print('\n\n'.join(lines))

    spans = [b[0] - a[0] for a, b in zip(paras, paras[1:])] or [0.0]
    chars = sum(len(text) for _, text in paras)
    print(f'{len(words)} Woerter, {chars} Zeichen, {len(paras)} Absaetze, '
          f'Median {statistics.median(spans):.0f}s, Laufzeit '
          f'{stamp(words[-1]["end"])}', file=sys.stderr)
    if args.out:
        print(f'Geschrieben: {args.out}', file=sys.stderr)


if __name__ == '__main__':
    main()
