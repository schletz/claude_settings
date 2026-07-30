"""List burst clusters of a folder from the Lightroom catalog as JSON.

Usage: python list_clusters.py <photo-folder> [--gap 1.0] [--catalog PATH]
Consecutive frames with a capture-time gap below --gap seconds form one cluster
(single shots are clusters of size 1). Works while Lightroom is open (read-only).
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import lrcat


def cluster(images: list[dict], gap: float) -> list[list[dict]]:
    """Chain time-sorted images into clusters; a gap >= `gap` seconds starts a new one."""
    clusters: list[list[dict]] = []
    prev = None
    for img in images:
        t = datetime.fromisoformat(img["captureTime"])
        if prev is not None and (t - prev).total_seconds() < gap:
            clusters[-1].append(img)
        else:
            clusters.append([img])
        prev = t
    return clusters


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--gap", type=float, default=1.0)
    ap.add_argument("--catalog", type=Path, default=lrcat.DEFAULT_CATALOG)
    args = ap.parse_args()

    conn = lrcat.open_readonly(args.catalog)
    images = lrcat.folder_images(conn, args.folder)
    if not images:
        sys.exit(f"No catalog images found for folder {args.folder}")
    out = []
    for n, frames in enumerate(cluster(images, args.gap), 1):
        out.append({"cluster": n, "size": len(frames),
                    # A cluster with any star is already decided manually.
                    "hasRating": any(f["rating"] > 0 for f in frames),
                    "frames": frames})
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({"folder": str(args.folder), "clusters": out}, ensure_ascii=False, indent=1))
