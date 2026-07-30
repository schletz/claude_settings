"""Build labelled contact sheets (max. 6 frames each) for clusters from list_clusters.py.

Usage: python make_contact_sheets.py <clusters.json> <thumbnail-dir> <out-dir> [--first N] [--last M] [--pack]
Expects <thumbnail-dir>/<stem>.jpg for every frame (see make_thumbnail.py).

Default: one sheet per cluster and chunk of 6 frames, <out-dir>/sheet_cNN_P.jpg, each tile
labelled with the last five characters of the file stem (e.g. 08812).

--pack: consecutive small clusters share a sheet (clusters are never split across sheets unless
they hold more than 6 frames), <out-dir>/sheet_pNNN.jpg, tiles labelled "cNN 08812" (cluster
number and file number). <out-dir>/sheets.json maps every sheet to its clusters.
"""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

TILE_WIDTH = 800
FRAMES_PER_SHEET = 6
COLUMNS = 3


def build_sheet(stems: list[str], thumb_dir: Path, labels: list[str] | None = None) -> Image.Image:
    """Tile the thumbnails of `stems` into one image, labelling each tile.

    The tile size follows the first frame; frames with another orientation are fitted into it
    (letterboxed) instead of being distorted.
    """
    font = ImageFont.truetype("arial.ttf", 44)
    labels = labels or [stem[-5:] for stem in stems]
    cols = min(COLUMNS, len(stems))
    rows = (len(stems) + cols - 1) // cols
    first = Image.open(thumb_dir / f"{stems[0]}.jpg")
    tile_h = round(first.height * TILE_WIDTH / first.width)
    sheet = Image.new("RGB", (cols * TILE_WIDTH, rows * tile_h))
    for k, (stem, label) in enumerate(zip(stems, labels)):
        img = Image.open(thumb_dir / f"{stem}.jpg")
        img.thumbnail((TILE_WIDTH, tile_h), Image.LANCZOS)
        tile = Image.new("RGB", (TILE_WIDTH, tile_h))
        tile.paste(img, ((TILE_WIDTH - img.width) // 2, (tile_h - img.height) // 2))
        draw = ImageDraw.Draw(tile)
        draw.rectangle((0, 0, 30 + 26 * len(label), 60), fill="black")
        draw.text((6, 4), label, fill="yellow", font=font)
        sheet.paste(tile, ((k % cols) * TILE_WIDTH, (k // cols) * tile_h))
    return sheet


def pack_clusters(clusters: list[dict]) -> list[list[tuple[int, str]]]:
    """Group frames of consecutive clusters into sheets of at most FRAMES_PER_SHEET frames."""
    sheets: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    for c in clusters:
        frames = [(c["cluster"], Path(f["file"]).stem) for f in c["frames"]]
        if len(frames) > FRAMES_PER_SHEET:  # large cluster: own sheets
            if current:
                sheets.append(current)
                current = []
            sheets += [frames[i:i + FRAMES_PER_SHEET] for i in range(0, len(frames), FRAMES_PER_SHEET)]
            continue
        if len(current) + len(frames) > FRAMES_PER_SHEET:
            sheets.append(current)
            current = []
        current += frames
    if current:
        sheets.append(current)
    return sheets


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("clusters", type=Path)
    ap.add_argument("thumbs", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--first", type=int, default=1)
    ap.add_argument("--last", type=int, default=10**9)
    ap.add_argument("--pack", action="store_true")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    clusters = [c for c in json.load(open(args.clusters, encoding="utf-8"))["clusters"]
                if args.first <= c["cluster"] <= args.last]
    if args.pack:
        manifest = {}
        for n, frames in enumerate(pack_clusters(clusters)):
            name = f"sheet_p{n:03d}.jpg"
            stems = [stem for _, stem in frames]
            labels = [f"c{cl} {stem[-5:]}" for cl, stem in frames]
            build_sheet(stems, args.thumbs, labels).save(args.out / name, quality=85)
            manifest[name] = sorted({cl for cl, _ in frames})
        (args.out / "sheets.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    else:
        for c in clusters:
            stems = [Path(f["file"]).stem for f in c["frames"]]
            for part, i in enumerate(range(0, len(stems), FRAMES_PER_SHEET)):
                sheet = build_sheet(stems[i:i + FRAMES_PER_SHEET], args.thumbs)
                sheet.save(args.out / f"sheet_c{c['cluster']:02d}_{part}.jpg", quality=85)
