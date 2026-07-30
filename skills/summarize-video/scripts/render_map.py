"""Render a topographic locator map for the places a video talks about.

The summary names towns, rivers and regions the reader has never heard of. A map
answers "where is that" in one glance, which no glossary entry does.

Tiles come from OpenTopoMap (relief, rivers and place names already drawn) or
plain OpenStreetMap; this script only picks the section, stitches the tiles and
draws the markers on top. Both sources require attribution, so it is burnt into
the image instead of being left to the caller.

Usage:
    python render_map.py --out ungarn-karte.png \\
        --bbox 45.7,16.1,48.6,22.9 \\
        --place "Paks:46.5726,18.8556" --place "Budapest:47.4979,19.0402" \\
        --label "Donau:47.15,18.80"

`--place` draws a marker plus its name, `--label` only the name — that is the
one for rivers, mountain ranges and regions, which the tiles already show.
"""

from __future__ import annotations

import argparse
import math
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit('Das Paket "Pillow" fehlt: python -m pip install Pillow')

TILE_SIZE = 256
# Both services ask for a real user agent and no bulk downloading; a dozen tiles
# per document is what this cap enforces.
USER_AGENT = 'summarize-video-skill/1.0 (private document illustration)'
MAX_TILES = 48

SOURCES = {
    'topo': {
        'url': 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
        'servers': ('a', 'b', 'c'),
        'max_zoom': 15,
        'credit': 'Karte: © OpenTopoMap (CC-BY-SA) — Daten: © OpenStreetMap-Mitwirkende, SRTM',
    },
    'osm': {
        'url': 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
        'servers': ('',),
        'max_zoom': 18,
        'credit': 'Karte und Daten: © OpenStreetMap-Mitwirkende',
    },
}


def lon_to_x(lon: float, zoom: int) -> float:
    """Longitude to fractional tile column in the Web Mercator grid."""
    return (lon + 180.0) / 360.0 * 2 ** zoom


def lat_to_y(lat: float, zoom: int) -> float:
    """Latitude to fractional tile row in the Web Mercator grid."""
    radians = math.radians(lat)
    return (1.0 - math.asinh(math.tan(radians)) / math.pi) / 2.0 * 2 ** zoom


def parse_point(raw: str) -> tuple[str, float, float]:
    """Split a `Name:lat,lon` argument, keeping colons inside the name."""
    name, _, coords = raw.rpartition(':')
    if not name:
        raise argparse.ArgumentTypeError(f'Erwartet "Name:lat,lon", bekommen: {raw}')
    try:
        lat, lon = (float(part) for part in coords.split(','))
    except ValueError:
        raise argparse.ArgumentTypeError(f'Koordinaten unlesbar in: {raw}') from None
    if not -85.0 <= lat <= 85.0 or not -180.0 <= lon <= 180.0:
        raise argparse.ArgumentTypeError(f'Koordinaten ausserhalb der Karte: {raw}')
    return name, lat, lon


def parse_bbox(raw: str) -> tuple[float, float, float, float]:
    """Read `south,west,north,east` and put the corners in a known order."""
    try:
        south, west, north, east = (float(part) for part in raw.split(','))
    except ValueError:
        raise argparse.ArgumentTypeError('Erwartet --bbox sued,west,nord,ost') from None
    return min(south, north), min(west, east), max(south, north), max(west, east)


def bbox_from_points(points: list[tuple[str, float, float]],
                     min_span: float) -> tuple[float, float, float, float]:
    """Frame all points, widened to `min_span` degrees so a single one still
    gets its surroundings instead of a street corner."""
    lats = [lat for _, lat, _ in points]
    lons = [lon for _, _, lon in points]
    south, north = min(lats), max(lats)
    west, east = min(lons), max(lons)
    # A quarter of the span as margin, so no marker sits on the edge.
    pad_lat = max((north - south) * 0.25, min_span / 2)
    pad_lon = max((east - west) * 0.25, min_span / 2)
    return (max(south - pad_lat, -85.0), max(west - pad_lon, -180.0),
            min(north + pad_lat, 85.0), min(east + pad_lon, 180.0))


def pick_zoom(bbox: tuple[float, float, float, float], width: int, height: int,
              max_zoom: int) -> int:
    """Largest zoom whose section still fits the requested pixel size."""
    south, west, north, east = bbox
    for zoom in range(max_zoom, -1, -1):
        span_x = (lon_to_x(east, zoom) - lon_to_x(west, zoom)) * TILE_SIZE
        span_y = (lat_to_y(south, zoom) - lat_to_y(north, zoom)) * TILE_SIZE
        if span_x <= width and span_y <= height:
            return zoom
    return 0


def fetch_tile(source: dict, zoom: int, x: int, y: int, cache: Path) -> Image.Image:
    """One tile, from the cache if it was fetched before."""
    cached = cache / f'{source["name"]}-{zoom}-{x}-{y}.png'
    if cached.is_file():
        return Image.open(cached).convert('RGB')

    server = source['servers'][(x + y) % len(source['servers'])]
    url = source['url'].format(s=server, z=zoom, x=x, y=y)
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read()
            break
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt == 2:
                sys.exit(f'Kachel {zoom}/{x}/{y} nicht ladbar ({error}). Ohne Netz '
                         'oder bei gesperrtem Kachelserver entfaellt die Karte.')
            time.sleep(1.5)
    cached.write_bytes(data)
    return Image.open(cached).convert('RGB')


def load_font(size: int) -> ImageFont.FreeTypeFont:
    """Segoe UI if Windows has it, else whatever Pillow can find."""
    for candidate in (r'C:\Windows\Fonts\segoeuib.ttf', r'C:\Windows\Fonts\arialbd.ttf'):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def stitch(source: dict, bbox: tuple[float, float, float, float], zoom: int,
           cache: Path) -> tuple[Image.Image, float, float]:
    """Build the map section and return it with its top-left pixel origin."""
    south, west, north, east = bbox
    left = lon_to_x(west, zoom) * TILE_SIZE
    right = lon_to_x(east, zoom) * TILE_SIZE
    top = lat_to_y(north, zoom) * TILE_SIZE
    bottom = lat_to_y(south, zoom) * TILE_SIZE

    first_x, last_x = int(left // TILE_SIZE), int(right // TILE_SIZE)
    first_y, last_y = int(top // TILE_SIZE), int(bottom // TILE_SIZE)
    count = (last_x - first_x + 1) * (last_y - first_y + 1)
    if count > MAX_TILES:
        sys.exit(f'{count} Kacheln waeren noetig, erlaubt sind {MAX_TILES}. '
                 'Kleineren Ausschnitt oder kleinere --width waehlen.')

    canvas = Image.new('RGB', ((last_x - first_x + 1) * TILE_SIZE,
                               (last_y - first_y + 1) * TILE_SIZE), 'white')
    for x in range(first_x, last_x + 1):
        for y in range(first_y, last_y + 1):
            canvas.paste(fetch_tile(source, zoom, x, y, cache),
                         ((x - first_x) * TILE_SIZE, (y - first_y) * TILE_SIZE))
    print(f'  {count} Kacheln, Zoom {zoom}')

    origin_x, origin_y = first_x * TILE_SIZE, first_y * TILE_SIZE
    section = canvas.crop((int(left - origin_x), int(top - origin_y),
                           int(right - origin_x), int(bottom - origin_y)))
    return section, left, top


def place_label(draw: ImageDraw.ImageDraw, text: str, anchor: tuple[float, float],
                font: ImageFont.FreeTypeFont, taken: list[tuple[float, ...]],
                size: tuple[int, int], marker: bool) -> None:
    """Draw a name next to its point, dodging labels that are already there.

    Candidates are tried right, left, below and above the anchor; the first one
    that stays inside the image and clear of earlier labels wins. Without this
    two nearby towns write on top of each other, which is invisible in the code
    and obvious in the PDF.
    """
    box = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = box[2] - box[0], box[3] - box[1]
    if marker:
        # Beside the dot, so the marker itself stays visible.
        gap = font.size * 0.6
        candidates = [
            (anchor[0] + gap, anchor[1] - text_h / 2),
            (anchor[0] - gap - text_w, anchor[1] - text_h / 2),
            (anchor[0] - text_w / 2, anchor[1] + gap),
            (anchor[0] - text_w / 2, anchor[1] - gap - text_h),
        ]
    else:
        # A river or region has no dot to avoid, so its name sits on the spot
        # given — offset to the side would point at the wrong place.
        gap = font.size * 1.2
        candidates = [
            (anchor[0] - text_w / 2, anchor[1] - text_h / 2),
            (anchor[0] - text_w / 2, anchor[1] + gap),
            (anchor[0] - text_w / 2, anchor[1] - gap - text_h),
            (anchor[0] + gap, anchor[1] - text_h / 2),
        ]
    for x, y in candidates:
        rect = (x - 2, y - 2, x + text_w + 2, y + text_h + 2)
        if rect[0] < 0 or rect[1] < 0 or rect[2] > size[0] or rect[3] > size[1]:
            continue
        if any(rect[0] < other[2] and rect[2] > other[0]
               and rect[1] < other[3] and rect[3] > other[1] for other in taken):
            continue
        taken.append(rect)
        break
    else:
        x, y = candidates[0]
        taken.append((x - 2, y - 2, x + text_w + 2, y + text_h + 2))

    # The halo is what keeps the name readable over contour lines and forest.
    draw.text((x - box[0], y - box[1]), text, font=font, fill=(20, 20, 20),
              stroke_width=max(2, font.size // 7), stroke_fill=(255, 255, 255))


def draw_overlay(image: Image.Image, places: list, labels: list, zoom: int,
                 left: float, top: float, credit: str) -> None:
    """Markers, names and the attribution strip."""
    draw = ImageDraw.Draw(image, 'RGBA')
    font = load_font(max(15, image.width // 46))
    radius = max(6, image.width // 150)
    taken: list[tuple[float, ...]] = []

    for name, lat, lon in places:
        x = lon_to_x(lon, zoom) * TILE_SIZE - left
        y = lat_to_y(lat, zoom) * TILE_SIZE - top
        draw.ellipse((x - radius, y - radius, x + radius, y + radius),
                     fill=(196, 30, 58), outline=(255, 255, 255),
                     width=max(2, radius // 3))
        place_label(draw, name, (x, y), font, taken, image.size, marker=True)

    for name, lat, lon in labels:
        x = lon_to_x(lon, zoom) * TILE_SIZE - left
        y = lat_to_y(lat, zoom) * TILE_SIZE - top
        place_label(draw, name, (x, y), font, taken, image.size, marker=False)

    credit_font = load_font(max(11, image.width // 100))
    box = draw.textbbox((0, 0), credit, font=credit_font)
    bar = box[3] - box[1] + 10
    draw.rectangle((0, image.height - bar, image.width, image.height),
                   fill=(255, 255, 255, 205))
    draw.text((6, image.height - bar + 4 - box[1]), credit, font=credit_font,
              fill=(60, 60, 60))


def main() -> None:
    """Assemble the map and report what to paste into the document."""
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', required=True, help='Ziel-PNG')
    ap.add_argument('--place', action='append', default=[], type=parse_point,
                    metavar='NAME:LAT,LON', help='Ort mit Marker; mehrfach erlaubt')
    ap.add_argument('--label', action='append', default=[], type=parse_point,
                    metavar='NAME:LAT,LON', help='nur Beschriftung, ohne Marker — '
                                                 'fuer Fluesse und Regionen')
    ap.add_argument('--bbox', type=parse_bbox, metavar='SUED,WEST,NORD,OST',
                    help='Ausschnitt; Vorgabe umschliesst alle Punkte')
    ap.add_argument('--tiles', choices=sorted(SOURCES), default='topo',
                    help='topo (Relief, Vorgabe) oder osm')
    ap.add_argument('--width', type=int, default=1600, help='Bildbreite in Pixel')
    ap.add_argument('--height', type=int, default=1200, help='Bildhoehe in Pixel')
    ap.add_argument('--min-span', type=float, default=0.6,
                    help='kleinste Ausdehnung in Grad, wenn --bbox fehlt')
    ap.add_argument('--cache', help='Kachelcache; Vorgabe liegt im Temp-Ordner')
    args = ap.parse_args()

    points = args.place + args.label
    if not points:
        sys.exit('Ohne --place oder --label gibt es nichts zu zeigen.')

    source = dict(SOURCES[args.tiles], name=args.tiles)
    bbox = args.bbox or bbox_from_points(points, args.min_span)
    zoom = pick_zoom(bbox, args.width, args.height, source['max_zoom'])

    cache = Path(args.cache) if args.cache else Path(tempfile.gettempdir()) / 'sv-tiles'
    cache.mkdir(parents=True, exist_ok=True)

    image, left, top = stitch(source, bbox, zoom, cache)
    draw_overlay(image, args.place, args.label, zoom, left, top, source['credit'])

    target = Path(args.out).resolve()
    image.save(target, 'PNG', optimize=True)
    print(f'{target.name}: {image.width}x{image.height} px, '
          f'{target.stat().st_size / 1024:.0f} KB')
    print('Einbinden mit:')
    print(f'  image::{target.name}[Karte, width=880]')
    print(f'  Bildunterschrift muss die Quelle nennen: {source["credit"]}')


if __name__ == '__main__':
    main()
