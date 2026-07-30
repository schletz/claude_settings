"""Fetch a video from a URL via yt-dlp in the best quality usable for voice-over.

The audio track is chosen explicitly instead of leaving it to yt-dlp's format
sort: YouTube serves auto-dubbed alternate audio for many videos, and a dubbed
track would silently replace the very voices this pipeline clones. The script
identifies the original-language track, skips dynamic-range-compressed (DRC)
variants, and reports what it picked.

Also prints the metadata the later steps need anyway: original language for
step 1, duration for the ``--duration`` arguments, chapters to find a
speech-free intro, and which human-made subtitles exist as a spelling aid for
proper names in step 9b.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# The YouTube extractor tags formats carrying the original audio with this
# language_preference; alternate dubs get -1, the default track 5.
ORIGINAL_LANG_PREF = 10
DEFAULT_LANG_PREF = 5

# Sidecar files yt-dlp may drop next to the media file.
SIDECAR_SUFFIXES = {
    '.json', '.part', '.ytdl', '.srt', '.vtt', '.ass', '.lrc',
    '.jpg', '.jpeg', '.png', '.webp', '.description',
}

# Clients the download rotates through, in order. An empty string leaves the
# choice to yt-dlp. The default client's media URLs are refused outright for
# some videos while web_embedded serves the identical format at full speed, so
# a retry that keeps the client is a retry that keeps the failure. Clients
# needing a GVS PO token (web, mweb, ios, tv_simply) are not listed: they
# expose no downloadable formats without one.
DEFAULT_PLAYER_CLIENTS = ('', 'web_embedded')

# yt-dlp enables deno only by default and has deprecated extraction without a
# runtime. Without one the n challenge stays unsolved, and a client such as
# web_embedded then reports no downloadable formats at all — so the client
# rotation above only helps once a runtime exists. Searching PATH keeps the
# documented invocation working without extra arguments.
JS_RUNTIMES = ('deno', 'node', 'bun')


@dataclass(frozen=True)
class FetchOptions:
    """Everything the download needs beyond the URL and the probed metadata."""

    outdir: Path
    common: list[str]
    max_res: int | None
    want_subs: bool
    chunk_size: str
    attempts: int
    player_clients: tuple[str, ...]
    audio_only: bool = False


def ytdlp(*args: str) -> list[str]:
    """Build a yt-dlp command line on the current interpreter."""
    return [sys.executable, '-m', 'yt_dlp', *args]


def find_js_runtime() -> str | None:
    """Return a ``runtime:path`` spec for the first JS runtime found on PATH."""
    for name in JS_RUNTIMES:
        path = shutil.which(name)
        if path:
            # The path goes after the colon; a bare name makes yt-dlp search
            # PATH itself, which fails wherever the launcher is not a plain exe.
            return f'{name}:{path}'
    return None


def probe(url: str, common: list[str]) -> dict:
    """Return yt-dlp's metadata for a single video, without downloading."""
    proc = subprocess.run(
        ytdlp('-J', '--no-warnings', '--no-playlist', *common, url),
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        check=False)
    if proc.returncode != 0:
        sys.exit(f'yt-dlp konnte die URL nicht lesen:\n{proc.stderr.strip()}')
    meta = json.loads(proc.stdout)
    if meta.get('_type') == 'playlist':
        # Search results and playlist-only URLs arrive as a container even with
        # --no-playlist; a single entry is unambiguous, more than one is not.
        entries = [e for e in meta.get('entries') or [] if e]
        if len(entries) != 1:
            sys.exit(f'Die URL liefert {len(entries)} Videos. '
                     'Gib die URL eines einzelnen Videos an.')
        meta = entries[0]
    return meta


def audio_formats(meta: dict) -> list[dict]:
    """Audio-only formats, newest yt-dlp reports video-less streams as vcodec 'none'."""
    return [f for f in meta.get('formats') or []
            if f.get('acodec') not in (None, 'none') and f.get('vcodec') in (None, 'none')]


def is_drc(fmt: dict) -> bool:
    """DRC tracks are loudness-compressed by YouTube — bad reference material."""
    return ('drc' in (fmt.get('format_id') or '').lower()
            or 'DRC' in (fmt.get('format_note') or ''))


def original_language(auds: list[dict]) -> str | None:
    """Language code of the track the video was actually recorded in, if marked."""
    for pref in (ORIGINAL_LANG_PREF, DEFAULT_LANG_PREF):
        for fmt in auds:
            if fmt.get('language_preference') == pref and fmt.get('language'):
                return fmt['language']
    return None


def bitrate(fmt: dict) -> float:
    """Audio bitrate in kbit/s, falling back to the total stream rate."""
    return fmt.get('abr') or fmt.get('tbr') or 0.0


def is_surround(fmt: dict) -> bool:
    """True for more than two channels; assumes stereo when unreported."""
    return (fmt.get('audio_channels') or 2) > 2


def audio_rank(fmt: dict) -> tuple:
    """Sort key for audio quality as this pipeline defines it.

    Stereo beats surround before bitrate is even considered: the whole chain
    assumes at most two channels. ``prepare_audio.py`` downmixes with ``-ac 1``,
    which folds music and effects from the surround channels into the speech,
    and its ``left``/``right`` variants pan to FL/FR — on a 5.1 mix the dialogue
    sits in the centre channel, so those variants would come out nearly mute.
    A 388 kbit/s 5.1 track is therefore worse here than a 129 kbit/s stereo one.
    """
    return (not is_surround(fmt), bitrate(fmt), fmt.get('asr') or 0)


def language_hint(meta: dict, chosen: dict | None) -> str | None:
    """Best guess at the spoken language, for subtitles and for step 1.

    Single-track videos often carry no language on the format at all, so the
    video-level field stands in. Deliberately separate from the strict marking
    used to choose the audio track.
    """
    return (chosen or {}).get('language') or meta.get('language')


def pick_audio(auds: list[dict], orig: str | None,
               forced_id: str | None) -> tuple[dict | None, str | None]:
    """Best non-DRC audio format in the original language, plus a blocking reason.

    Refuses to guess when several languages are offered but none is marked as
    the original — picking a dub there would poison every later step, and the
    mistake stays invisible until the finished track speaks the wrong voices.
    The reason is returned rather than raised so the caller can print the full
    format report first.
    """
    if forced_id:
        match = next((f for f in auds if f.get('format_id') == forced_id), None)
        if match is None:
            return None, (f'Kein Audioformat mit der ID {forced_id}. '
                          'Liste mit: python -m yt_dlp -F <url>')
        return match, None

    langs = {f['language'] for f in auds if f.get('language')}
    if orig is None and len(langs) > 1:
        return None, (f'Mehrere Tonsprachen ({", ".join(sorted(langs))}), aber keine '
                      'als Original markiert. Hier wird nicht geraten: Formate mit '
                      '"python -m yt_dlp -F <url>" ansehen und die richtige Spur '
                      'mit --audio-id festnageln.')

    pool = [f for f in auds if orig is None or f.get('language') in (None, orig)]
    clean = [f for f in pool if not is_drc(f)]
    return max(clean or pool, key=audio_rank, default=None), None


def report(meta: dict, auds: list[dict], orig: str | None, chosen: dict | None) -> None:
    """Print everything the following steps need, in one block."""
    dur = meta.get('duration') or 0
    print(f'Titel      : {meta.get("title")}')
    print(f'ID         : {meta.get("id")}    Kanal: {meta.get("uploader")}')
    print(f'Dauer      : {dur} s  ({dur // 60:d}:{dur % 60:02d})')

    langs = sorted({f['language'] for f in auds if f.get('language')})
    hint = language_hint(meta, chosen)
    print(f'Tonspuren  : {len(auds)}'
          + (f'  Sprachen: {", ".join(langs)}' if langs else '')
          + (f'  Original: {orig}' if orig
             else f'  Original: nicht markiert, Videosprache: {hint or "unbekannt"}'))
    if len(langs) > 1:
        print('  ACHTUNG: mehrere Sprachen vorhanden — YouTube-Dubs. '
              'Es wird die Originalspur geladen.')
    if any(is_drc(f) for f in auds):
        print('  DRC-Varianten vorhanden und uebersprungen (loudness-komprimiert).')
    if any(is_surround(f) for f in auds):
        print('  Surround-Spuren vorhanden und zugunsten von Stereo uebersprungen.')

    if chosen:
        print(f'Gewaehlt   : {chosen.get("format_id")}  {chosen.get("ext")}  '
              f'{chosen.get("acodec")}  {bitrate(chosen):.0f} kbit/s  '
              f'{chosen.get("audio_channels") or "?"} Kanal/Kanaele  '
              f'{chosen.get("asr") or "?"} Hz  lang={chosen.get("language")}')
        if is_surround(chosen):
            print('  WARNUNG: nur Surround verfuegbar. probe_audio.py und die '
                  'left/right-Varianten von prepare_audio.py rechnen mit FL/FR, '
                  'der Dialog liegt aber im Center. Vorher mit ffmpeg auf Stereo '
                  'bringen oder den Center herausziehen.')
    else:
        print('Gewaehlt   : keine reine Tonspur gefunden, faellt auf "b" zurueck')

    subs = sorted((meta.get('subtitles') or {}).keys())
    autos = sorted((meta.get('automatic_captions') or {}).keys())
    print(f'Untertitel : von Hand: {", ".join(subs) or "keine"}'
          f'  |  automatisch: {len(autos)} Sprachen')

    chapters = meta.get('chapters') or []
    if chapters:
        print(f'Kapitel    : {len(chapters)}')
        for ch in chapters[:6]:
            print(f'  {ch.get("start_time", 0):8.1f}s  {ch.get("title")}')
        if len(chapters) > 6:
            print(f'  ... {len(chapters) - 6} weitere')


def find_media(outdir: Path, vid: str) -> Path | None:
    """Locate the downloaded media file; the extension depends on the merge."""
    hits = [p for p in outdir.iterdir()
            if p.is_file() and p.name.startswith(f'{vid}.')
            and p.suffix.lower() not in SIDECAR_SUFFIXES]
    return max(hits, key=lambda p: p.stat().st_size, default=None)


def ffprobe_duration(path: Path) -> float | None:
    """Container runtime in seconds, or None if ffprobe cannot read the file."""
    proc = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'csv=p=0', str(path)],
        capture_output=True, text=True, check=False)
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return None


def subtitle_args(meta: dict, orig: str | None) -> list[str]:
    """Options for fetching human-made subtitles in the original language.

    Auto-captions are deliberately excluded: they are ASR output and would carry
    the same error class as our own transcription, giving false confidence.
    """
    available = sorted((meta.get('subtitles') or {}).keys())
    pick = [lang for lang in available
            if orig and (lang == orig or lang.startswith(f'{orig}-'))]
    if not pick:
        print('Keine von Hand erstellten Untertitel in der Originalsprache — '
              'automatische werden absichtlich nicht geladen.')
        return []
    print(f'Untertitel von Hand werden mitgeladen: {", ".join(pick)}')
    return ['--write-subs', '--no-write-auto-subs',
            '--sub-langs', ','.join(pick), '--convert-subs', 'srt']


def download(url: str, meta: dict, chosen: dict | None, opts: FetchOptions) -> Path:
    """Download the chosen audio track, with the video alongside it unless asked not to.

    ``audio_only`` exists for consumers that never look at the picture — a podcast
    version is the case at hand. It saves the bulk of the transfer: measured on one
    ten-minute video, 119 MB against 4 MB. The audio format is the same one either
    way, so nothing downstream of the download changes.
    """
    res = f'[height<={opts.max_res}]' if opts.max_res else ''
    audio_id = chosen.get('format_id') if chosen else None
    if opts.audio_only:
        # No merge: the audio stream is written in its own container, so the
        # extension follows the codec (.m4a, .webm) instead of being .mkv.
        selector = f'{audio_id}/ba/b' if audio_id else 'ba/b'
    else:
        # Fall back to the sorted best audio if the pinned id is unavailable.
        selector = (f'bv*{res}+{audio_id}/bv*{res}+ba/b{res}/b' if audio_id
                    else f'bv*{res}+ba/b{res}/b')

    # --newline plus a coarse delta keeps the log readable: the default carriage
    # returns produce hundreds of progress lines that drown the final report.
    #
    # --http-chunk-size splits the byte range into separate requests, and
    # --continue keeps whatever a failed attempt already wrote, so the retry
    # loop below resumes instead of starting over.
    cmd = ['--no-playlist', '-f', selector,
           *([] if opts.audio_only else ['--merge-output-format', 'mkv']),
           '-o', '%(id)s.%(ext)s', '-P', str(opts.outdir), '--write-info-json',
           '-N', '4', '--retries', '10', '--fragment-retries', '10',
           '--http-chunk-size', opts.chunk_size, '--continue',
           '--newline', '--progress-delta', '5']
    if opts.want_subs:
        cmd += subtitle_args(meta, language_hint(meta, chosen))

    print(f'\nFormatselektor: {selector}\n')
    # "unable to download video data: HTTP Error 403: Forbidden" before a byte
    # moves is a property of the player client, not of the connection. The
    # metadata probe still succeeds, and so does a --test run that stops after
    # 10 KB, which makes the failure look sporadic; measured on one video the
    # default client answered 403 on roughly thirty consecutive attempts while
    # web_embedded fetched the same format at 10 MB/s. Rotating the client
    # therefore comes first. A fresh process also matters on its own, because
    # only it gets a fresh media URL — yt-dlp's --retries runs after the
    # extractor has already given up.
    for attempt in range(1, opts.attempts + 1):
        client = opts.player_clients[(attempt - 1) % len(opts.player_clients)]
        extra = (['--extractor-args', f'youtube:player_client={client}']
                 if client else [])
        if subprocess.run(ytdlp(*cmd, *extra, *opts.common, url),
                          check=False).returncode == 0:
            print(f'\nGeladen mit Player-Client: {client or "yt-dlp-Vorgabe"}')
            break
        if attempt < opts.attempts:
            nxt = opts.player_clients[attempt % len(opts.player_clients)]
            print(f'\nVersuch {attempt} von {opts.attempts} gescheitert, neuer '
                  f'Anlauf mit frischer URL und Player-Client '
                  f'{nxt or "yt-dlp-Vorgabe"}.\n')
    else:
        sys.exit(f'Der Download ist nach {opts.attempts} Versuchen gescheitert. '
                 f'Probierte Player-Clients: '
                 f'{", ".join(c or "Vorgabe" for c in opts.player_clients)}. '
                 f'Weitere mit --player-client vorgeben.')

    path = find_media(opts.outdir, meta['id'])
    if path is None:
        sys.exit(f'Download gemeldet, aber keine Mediendatei zu {meta["id"]} gefunden.')
    return path


def verify(path: Path, expected: float | None) -> None:
    """Compare the container duration against the metadata to catch truncation."""
    print(f'\nDatei      : {path}')
    print(f'Groesse    : {path.stat().st_size / 1e6:.1f} MB')
    actual = ffprobe_duration(path)
    if actual is None:
        print('WARNUNG: ffprobe konnte die Datei nicht lesen.')
        return
    print(f'Laufzeit   : {actual:.1f} s')
    if expected and abs(actual - expected) > 2.0:
        print(f'WARNUNG: erwartet waren {expected} s — Abweichung '
              f'{abs(actual - expected):.1f} s. Download vermutlich unvollstaendig.')


def main() -> None:
    """Probe the URL, report what the later steps need, then download."""
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('url')
    ap.add_argument('--outdir', default='.', help='Zielordner der Mediendatei')
    ap.add_argument('--probe-only', action='store_true',
                    help='nur Metadaten und Formatwahl melden, nichts laden')
    ap.add_argument('--max-res', type=int,
                    help='Bildhoehe begrenzen; die Tonspur bleibt unberuehrt')
    ap.add_argument('--audio-only', action='store_true',
                    help='nur die Tonspur laden, kein Bild — fuer den Skill podcast')
    ap.add_argument('--audio-id',
                    help='Audioformat-ID festnageln, wenn die Automatik abbricht')
    ap.add_argument('--subs', action='store_true',
                    help='von Hand erstellte Untertitel der Originalsprache mitladen')
    ap.add_argument('--cookies-from-browser',
                    help='Browser fuer Cookies, z. B. firefox — bei Bot-Pruefung '
                         'noetig. Chromium-Browser ab Version 127 (Chrome, Edge) '
                         'verschluesseln app-gebunden und scheitern hier')
    ap.add_argument('--player-client',
                    help='Player-Client fuer den Download festnageln, z. B. '
                         f'web_embedded; ohne Angabe rotieren '
                         f'{", ".join(c or "Vorgabe" for c in DEFAULT_PLAYER_CLIENTS)}')
    ap.add_argument('--js-runtime',
                    help='JS-Laufzeit festnageln, z. B. node:C:/nodejs/node.exe; '
                         f'ohne Angabe wird auf PATH gesucht ({", ".join(JS_RUNTIMES)})')
    ap.add_argument('--remote-components', default='ejs:github',
                    help='Bezugsquelle des Challenge-Solvers; wirkt nur zusammen '
                         'mit --js-runtime. Leer setzen, um ihn abzuschalten')
    ap.add_argument('--chunk-size', default='5M',
                    help='Groesse der einzelnen HTTP-Bereichsanfragen')
    ap.add_argument('--attempts', type=int, default=6,
                    help='Anlaeufe bei 403 von YouTube; wechselt den Player-Client')
    args = ap.parse_args()

    common: list[str] = []
    if args.cookies_from_browser:
        common += ['--cookies-from-browser', args.cookies_from_browser]
    # The solver script is JavaScript, so it is only reachable once a runtime
    # exists. It brings back formats the deprecated runtime-less extraction
    # leaves out, and without it the client rotation in download() has nothing
    # to rotate to. It is not by itself a remedy for a 403 on the media URL.
    js_runtime = args.js_runtime or find_js_runtime()
    if js_runtime:
        common += ['--js-runtimes', js_runtime]
        if args.remote_components:
            common += ['--remote-components', args.remote_components]
        print(f'JS-Laufzeit: {js_runtime}')
    else:
        print('WARNUNG: keine JS-Laufzeit gefunden (' + ', '.join(JS_RUNTIMES)
              + '). Formate koennen fehlen; mit --js-runtime vorgeben.')

    meta = probe(args.url, common)
    auds = audio_formats(meta)
    orig = original_language(auds)
    chosen, problem = pick_audio(auds, orig, args.audio_id)
    report(meta, auds, orig, chosen)

    if problem:
        sys.exit(f'\n{problem}')
    if args.probe_only:
        return

    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    # The probe deliberately keeps yt-dlp's default client: it is the one that
    # lists every alternate audio track, and picking the original among them is
    # what the probe is for. A pinned client only governs the download.
    clients = ((args.player_client,) if args.player_client
               else DEFAULT_PLAYER_CLIENTS)
    opts = FetchOptions(outdir=outdir, common=common,
                        max_res=args.max_res, want_subs=args.subs,
                        chunk_size=args.chunk_size, attempts=args.attempts,
                        player_clients=clients, audio_only=args.audio_only)
    path = download(args.url, meta, chosen, opts)
    verify(path, meta.get('duration'))

    hint = language_hint(meta, chosen)
    if hint:
        print(f'\nGesprochene Sprache laut Metadaten: {hint} — Vorgabe fuer Schritt 1, '
              'aber vom Nutzer bestaetigen lassen.')


if __name__ == '__main__':
    main()
