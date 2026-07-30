"""Create downscaled JPEGs from RAW files (ARW, DNG, ...).

Usage: python make_thumbnail.py <source> <target-dir> <width> [--workers N]

<source> is either a single RAW file or the clusters.json written by
list_clusters.py; in the latter case every frame is converted in parallel.
The height follows proportionally. Output: <target-dir>/<raw-stem>.jpg
Exits with status 1 if any file failed.
"""

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import rawpy
from PIL import Image


def make_thumbnail(raw_file: Path, target_dir: Path, width: int) -> Path:
    """Decode `raw_file` (half-size demosaic, camera white balance) and save a JPEG `width` px wide."""
    target_dir.mkdir(parents=True, exist_ok=True)
    with rawpy.imread(str(raw_file)) as raw:
        # half_size skips full demosaicing; plenty of resolution for a preview.
        rgb = raw.postprocess(half_size=True, use_camera_wb=True, output_bps=8)
    img = Image.fromarray(rgb)
    height = round(img.height * width / img.width)
    img = img.resize((width, height), Image.LANCZOS)
    out = target_dir / f"{raw_file.stem}.jpg"
    img.save(out, "JPEG", quality=88)
    return out


def raw_files_from_clusters(clusters_json: Path) -> list[Path]:
    """Return the absolute RAW paths of all frames listed in a list_clusters.py result."""
    data = json.loads(clusters_json.read_text(encoding="utf-8"))
    folder = Path(data["folder"])
    return [folder / frame["file"] for cluster in data["clusters"] for frame in cluster["frames"]]


def _convert(job: tuple[Path, Path, int]) -> tuple[Path, str | None]:
    """Worker entry point: returns the source file and an error message (None on success)."""
    raw_file, target_dir, width = job
    try:
        make_thumbnail(raw_file, target_dir, width)
        return raw_file, None
    except Exception as exc:  # report per file instead of aborting the whole batch
        return raw_file, f"{type(exc).__name__}: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="RAW file or clusters.json")
    parser.add_argument("target_dir", type=Path)
    parser.add_argument("width", type=int)
    parser.add_argument("--workers", type=int, default=6, help="parallel processes (default 6)")
    args = parser.parse_args()

    if args.source.suffix.lower() == ".json":
        files = raw_files_from_clusters(args.source)
    else:
        files = [args.source]

    jobs = [(f, args.target_dir, args.width) for f in files]
    failed = 0
    with ProcessPoolExecutor(max_workers=min(args.workers, len(jobs))) as pool:
        for raw_file, error in pool.map(_convert, jobs):
            if error:
                failed += 1
                print(f"FAILED {raw_file}: {error}", file=sys.stderr)
    print(f"{len(jobs) - failed}/{len(jobs)} thumbnails in {args.target_dir}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
