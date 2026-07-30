"""Render a summary to PDF with Asciidoctor in Docker, and report its warnings.

This is the real syntax check. `check_adoc.py` only knows the rules this skill
made up; Asciidoctor knows AsciiDoc. Running it turns silent breakage — an image
that does not resolve, an attribute reference that renders empty, a heading level
that jumps — into a message, and the PDF is a deliverable the user wants anyway.

The image and the conversion flags follow the user's own `convert_adoc.cmd`:
`asciidoctor/docker-asciidoctor` plus pandoc, and a `<basename>.yml` next to the
document is picked up as the PDF theme.

Asciidoctor exits 0 even when it warns, so the exit code alone proves nothing.
This script reads the diagnostics out of the container output and fails on
errors, which is the part that makes it a check rather than a converter.

Usage:
    python render_adoc.py summary.adoc [--out summary.pdf] [--verbose]
"""

from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

try:
    import docker
    from docker.errors import BuildError, ContainerError, DockerException, ImageNotFound
except ImportError:
    sys.exit('Das Paket "docker" fehlt: python -m pip install docker')

IMAGE = 'asciidoctor-pandoc'
MOUNT = '/documents'

# The bundled Noto Serif of asciidoctor-pdf has no IPA glyphs: a transcription
# like [ˈmɒɟɒr ˈpeːtɛr] comes out as empty boxes, and Asciidoctor does not warn
# about it. DejaVu covers IPA Extensions, spacing modifiers and tone letters
# completely, so it is installed into the image and hooked up as a fallback font.
# Measured: the shipped `default-with-font-fallbacks` theme is not enough — it
# renders ˈ ː ə but still drops ɒ ɟ ɛ ʃ ɡ.
FALLBACK_LABEL = 'summarize-video.fallback-font'
FALLBACK_VALUE = 'dejavu'
THEME_DIR = '/usr/local/share/asciidoctor-pdf'
THEME_PATH = f'{THEME_DIR}/fallback-theme.yml'

# Only glyphs the primary font lacks come from DejaVu, so the page keeps its
# usual look and the phonetics ride along.
FALLBACK_THEME = '''extends: default
font:
  catalog:
    merge: true
    DejaVu Serif:
      normal: /usr/share/fonts/dejavu/DejaVuSerif.ttf
      bold: /usr/share/fonts/dejavu/DejaVuSerif-Bold.ttf
      italic: /usr/share/fonts/dejavu/DejaVuSerif-Italic.ttf
      bold_italic: /usr/share/fonts/dejavu/DejaVuSerif-BoldItalic.ttf
    DejaVu Sans Mono:
      normal: /usr/share/fonts/dejavu/DejaVuSansMono.ttf
      bold: /usr/share/fonts/dejavu/DejaVuSansMono-Bold.ttf
      italic: /usr/share/fonts/dejavu/DejaVuSansMono-Oblique.ttf
      bold_italic: /usr/share/fonts/dejavu/DejaVuSansMono-BoldOblique.ttf
  fallbacks:
    - DejaVu Serif
    - DejaVu Sans Mono
'''

# The build runs without a context (the Dockerfile is piped in), so the theme is
# written by the shell. The classic builder has no heredoc, hence printf '%b'
# with escaped newlines.
_THEME_LITERAL = FALLBACK_THEME.replace('\n', '\\n')

# Same image the user's convert_adoc.cmd builds: Asciidoctor plus pandoc, so the
# docx and markdown targets keep working from the same tag.
DOCKERFILE = f'''FROM asciidoctor/docker-asciidoctor
RUN apk add --no-cache pandoc font-dejavu
RUN mkdir -p {THEME_DIR} && printf '%b' '{_THEME_LITERAL}' > {THEME_PATH}
LABEL {FALLBACK_LABEL}="{FALLBACK_VALUE}"
WORKDIR /documents
CMD ["sh"]
'''.encode('utf-8')

# Asciidoctor prefixes every diagnostic with its own name and a level.
DIAGNOSTIC = re.compile(r'^(?:asciidoctor|asciidoctor-pdf):\s*(WARNING|ERROR|FAILED)[:\s]',
                        re.IGNORECASE)
FATAL_LEVELS = ('ERROR', 'FAILED')


def ensure_image(client) -> None:
    """Build the conversion image, or rebuild one that predates the fallback font."""
    try:
        image = client.images.get(IMAGE)
        if (image.labels or {}).get(FALLBACK_LABEL) == FALLBACK_VALUE:
            return
        # An older image still converts, but silently swallows IPA glyphs.
        print(f'Image {IMAGE} kennt die Fallback-Schrift noch nicht und wird '
              'ergaenzt — das dauert einmalig etwa eine Minute.')
    except ImageNotFound:
        print(f'Image {IMAGE} fehlt und wird gebaut — das dauert beim ersten Mal '
              'einige Minuten.')
    try:
        client.images.build(fileobj=io.BytesIO(DOCKERFILE), tag=IMAGE, rm=True)
    except BuildError as error:
        sys.exit(f'Build gescheitert: {error}')
    print(f'Image {IMAGE} gebaut.')


def theme_argument(source: Path, explicit: str | None) -> list[str]:
    """PDF theme: an explicit one, else a <basename>.yml, else the fallback theme."""
    if explicit:
        return ['--theme', explicit]
    sidecar = source.with_suffix('.yml')
    if sidecar.is_file():
        print(f'Theme gefunden: {sidecar.name} — Lautschrift und andere Zeichen '
              'ausserhalb von Latin/Griechisch/Kyrillisch koennen damit als leere '
              'Kaestchen erscheinen.')
        return ['--theme', sidecar.name]
    return ['--theme', THEME_PATH]


def build_command(source: Path, target: Path, theme: list[str]) -> list[str]:
    """The asciidoctor-pdf invocation, mirroring the user's convert_adoc.cmd."""
    return [
        'asciidoctor-pdf', *theme,
        '-r', 'asciidoctor-mathematical',
        '-r', 'asciidoctor-diagram',
        '-a', 'allow-uri-read',
        '-a', 'stem',
        '-a', 'mathematical-format=svg',
        '-o', target.name,
        source.name,
    ]


def convert(client, source: Path, target: Path, theme: list[str]) -> str:
    """Run the conversion in a throwaway container and return its output."""
    # The whole directory is mounted so relative image:: targets resolve exactly
    # as they will for the user; the container writes the PDF straight into it.
    binds = {str(source.parent): {'bind': MOUNT, 'mode': 'rw'}}
    try:
        output = client.containers.run(
            IMAGE, command=build_command(source, target, theme),
            volumes=binds, working_dir=MOUNT, remove=True,
            stdout=True, stderr=True)
    except ContainerError as error:
        text = (error.stderr or b'').decode('utf-8', 'replace')
        report(text)
        sys.exit(f'\nAsciidoctor ist mit Exitcode {error.exit_status} abgebrochen.')
    except DockerException as error:
        sys.exit(f'Docker konnte den Container nicht starten: {error}\n'
                 'Laeuft Docker Desktop?')
    return output.decode('utf-8', 'replace')


def diagnostics(output: str) -> list[tuple[str, str]]:
    """Extract (level, line) for every Asciidoctor warning or error."""
    found = []
    for line in output.splitlines():
        match = DIAGNOSTIC.match(line.strip())
        if match:
            found.append((match.group(1).upper(), line.strip()))
    return found


def report(output: str) -> list[tuple[str, str]]:
    """Print the diagnostics and hand them back to the caller."""
    found = diagnostics(output)
    for level, line in found:
        marker = 'FEHLER ' if level in FATAL_LEVELS else 'HINWEIS'
        print(f'  {marker}: {line}')
    return found


def page_count(pdf: Path) -> int | None:
    """Pages in the produced PDF, if a reader is installed."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return None
    try:
        return len(PdfReader(str(pdf)).pages)
    except Exception:
        return None


def main() -> None:
    """Convert the document and fail if Asciidoctor reported an error."""
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('adoc')
    ap.add_argument('--out', help='Ziel-PDF; Vorgabe ist <adoc> mit Endung .pdf')
    ap.add_argument('--theme', help='PDF-Theme (YAML); Vorgabe ist <adoc>.yml, '
                                    'falls vorhanden')
    ap.add_argument('--verbose', action='store_true',
                    help='vollstaendige Containerausgabe zeigen')
    args = ap.parse_args()

    source = Path(args.adoc).resolve()
    if not source.is_file():
        sys.exit(f'Keine Datei: {source}')
    target = Path(args.out).resolve() if args.out else source.with_suffix('.pdf')
    if target.parent != source.parent:
        sys.exit('Ziel und Quelle muessen im selben Ordner liegen — nur dieser '
                 'wird in den Container gehaengt.')

    try:
        client = docker.from_env()
        client.ping()
    except DockerException as error:
        sys.exit(f'Docker antwortet nicht ({error}). Laeuft Docker Desktop?')

    ensure_image(client)
    output = convert(client, source, target, theme_argument(source, args.theme))

    if args.verbose and output.strip():
        print('--- Containerausgabe ---')
        print(output.rstrip())
        print('------------------------')

    print(f'{source.name} -> {target.name}')
    found = report(output)

    if not target.is_file():
        sys.exit('Asciidoctor meldete keinen Fehler, aber es gibt kein PDF.')
    pages = page_count(target)
    print(f'  {target.stat().st_size / 1024:.0f} KB'
          + (f', {pages} Seiten' if pages else '')
          + f', {sum(1 for lvl, _ in found if lvl not in FATAL_LEVELS)} Hinweise')

    if any(level in FATAL_LEVELS for level, _ in found):
        sys.exit(1)
    print('OK')


if __name__ == '__main__':
    main()
