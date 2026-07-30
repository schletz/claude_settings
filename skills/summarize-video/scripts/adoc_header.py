"""Write the AsciiDoc header and the source data block of a video summary.

Everything in this file comes straight from yt-dlp's ``<id>.info.json``. Typing
the upload date, the runtime and the URL by hand from a report on screen is
where a summary picks up its first wrong fact, and it is the one part of the
document that can be produced mechanically.

The body — abstract, sections, commentary — is written separately and passed in
with ``--body``. Appending it through the shell instead is a trap on Windows: a
heredoc carrying Umlauts, typographic quotes and Hungarian accents runs into
quoting and code page problems that cost more time than this option.

For the same reason the title is best carried *inside* the body file as its
first line (``= Deutscher Titel``): a title passed on the command line loses its
Umlauts on the way through the shell. ``--title`` remains for the case where the
body is written without one.

Usage:
    python adoc_header.py <id>.info.json --body body.adoc --out name.adoc
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# The attribute block the user's documents are built with, taken verbatim.
HEADER_ATTRIBUTES = """:source-highlighter: rouge
:icons: font
:lang: DE
:hyphens:
:figure-caption!:
ifndef::root_dir[:root_dir: .]
ifndef::github_url[:github_url: ..]
ifndef::env-github[:icons: font]
ifdef::env-github[]
:caution-caption: :fire:
:important-caption: :exclamation:
:note-caption: :paperclip:
:tip-caption: :bulb:
:warning-caption: :warning:
endif::[]"""

# Only the languages this skill realistically meets; anything else is reported
# as its raw code rather than guessed at.
LANGUAGES = {
    'de': 'Deutsch', 'en': 'Englisch', 'hu': 'Ungarisch', 'sk': 'Slowakisch',
    'cs': 'Tschechisch', 'pl': 'Polnisch', 'sl': 'Slowenisch', 'hr': 'Kroatisch',
    'sr': 'Serbisch', 'ro': 'Rumaenisch', 'ru': 'Russisch', 'uk': 'Ukrainisch',
    'it': 'Italienisch', 'fr': 'Franzoesisch', 'es': 'Spanisch', 'tr': 'Tuerkisch',
}


def language_name(code: str | None) -> str:
    """Render a language tag as a German name, falling back to the raw code."""
    if not code:
        return 'unbekannt'
    name = LANGUAGES.get(code.split('-')[0].lower())
    return f'{name} ({code})' if name else code


def format_date(raw: str | None) -> str:
    """Turn yt-dlp's YYYYMMDD into DD.MM.YYYY."""
    if not raw or len(raw) != 8 or not raw.isdigit():
        return 'unbekannt'
    return f'{raw[6:8]}.{raw[4:6]}.{raw[0:4]}'


def format_duration(seconds: float | None) -> str:
    """Runtime as MM:SS, or H:MM:SS once it passes the hour."""
    if not seconds:
        return 'unbekannt'
    total = int(seconds)
    if total >= 3600:
        return f'{total // 3600}:{total // 60 % 60:02d}:{total % 60:02d}'
    return f'{total // 60:02d}:{total % 60:02d}'


def sanitize(value: str | None) -> str:
    """Collapse a metadata field to one line so it cannot break the list syntax."""
    return ' '.join((value or '').split()) or 'unbekannt'


def source_block(meta: dict) -> str:
    """The labelled list of source data that opens every summary."""
    url = meta.get('webpage_url') or meta.get('original_url') or ''
    rows = [
        ('Originaltitel', sanitize(meta.get('title'))),
        ('Kanal', sanitize(meta.get('uploader') or meta.get('channel'))),
        ('Hochgeladen', format_date(meta.get('upload_date') or meta.get('release_date'))),
        ('Laufzeit', format_duration(meta.get('duration'))),
        ('Sprache', language_name(meta.get('language'))),
        ('Quelle', url or 'unbekannt'),
    ]
    lines = ['[horizontal]']
    # A URL as the last item of a labelled list needs no macro; Asciidoctor
    # autolinks it. The trailing blank line separates the list from the abstract.
    lines += [f'{label}:: {value}' for label, value in rows]
    return '\n'.join(lines)


def split_title(body: str, fallback: str | None) -> tuple[str, str]:
    """Peel a leading '= Titel' line off the body, else fall back to --title."""
    stripped = body.lstrip()
    if stripped.startswith('= '):
        head, _, rest = stripped.partition('\n')
        return head[2:].strip(), rest.lstrip()
    if not fallback:
        sys.exit('Kein Titel: entweder --title angeben oder den Rumpf mit einer '
                 'Zeile "= Deutscher Titel" beginnen lassen.')
    return fallback, stripped


def main() -> None:
    """Assemble title, attributes and source data, then write or print them."""
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('info_json', help='die von yt-dlp geschriebene <id>.info.json')
    ap.add_argument('--title',
                    help='deutscher Titel, wenn der Rumpf keinen mitbringt; '
                         'Umlaute ueberleben den Weg durch die Shell nicht')
    ap.add_argument('--body', help='Datei mit dem Rumpf, optional mit "= Titel" '
                                   'als erster Zeile')
    ap.add_argument('--out', help='Zieldatei; Vorgabe ist die Standardausgabe')
    args = ap.parse_args()

    meta = json.loads(Path(args.info_json).read_text(encoding='utf-8'))
    body = Path(args.body).read_text(encoding='utf-8') if args.body else ''
    title, body = split_title(body, args.title)

    document = f'= {sanitize(title)}\n{HEADER_ATTRIBUTES}\n\n{source_block(meta)}\n'
    if body:
        document += f'\n{body}'

    if args.out:
        Path(args.out).write_text(document, encoding='utf-8')
        print(f'Geschrieben: {args.out}')
    else:
        print(document)


if __name__ == '__main__':
    main()
