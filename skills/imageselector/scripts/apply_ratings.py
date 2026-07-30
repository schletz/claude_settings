"""Set star ratings on catalog image ids (only images without a rating).

Usage: python apply_ratings.py --set 4:<id>,<id>,... [--set 3:<id>,...] [--catalog PATH] [--dry-run]
Requires Lightroom to be closed (except with --dry-run). Creates one timestamped
catalog backup before writing. Existing ratings are never overwritten.
"""

import argparse
import sys
from pathlib import Path

import lrcat

VALID_STARS = range(1, 6)


def parse_set(spec: str) -> tuple[int, list[int]]:
    """Parse '<stars>:<id>,<id>,...' into (stars, ids)."""
    stars, _, ids = spec.partition(":")
    if not stars.isdigit() or int(stars) not in VALID_STARS or not ids:
        raise argparse.ArgumentTypeError(f"expected <1-5>:<id>,<id>,... but got '{spec}'")
    return int(stars), [int(i) for i in ids.split(",")]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", dest="sets", type=parse_set, action="append", required=True,
                    metavar="STARS:IDS")
    ap.add_argument("--catalog", type=Path, default=lrcat.DEFAULT_CATALOG)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    wanted: dict[int, int] = {}
    for stars, ids in args.sets:
        for id_local in ids:
            if wanted.setdefault(id_local, stars) != stars:
                sys.exit(f"ABORTED: id {id_local} is assigned to two different star counts")

    if args.dry_run:
        conn = lrcat.open_readonly(args.catalog)
        backup = None
    else:
        try:
            conn, backup = lrcat.open_for_write(args.catalog)
        except lrcat.CatalogBusyError as e:
            sys.exit(f"ABORTED: {e}")

    updated: dict[int, list[int]] = {}
    skipped = []
    for id_local, stars in wanted.items():
        row = conn.execute("select rating from Adobe_images where id_local=?", (id_local,)).fetchone()
        if row is None or (row[0] or 0) > 0:
            skipped.append(id_local)  # unknown id or existing (manual) rating: never overwrite
            continue
        if not args.dry_run:
            conn.execute("update Adobe_images set rating=? where id_local=?", (stars, id_local))
        updated.setdefault(stars, []).append(id_local)
    if not args.dry_run:
        conn.commit()
        print("integrity:", conn.execute("pragma integrity_check").fetchone()[0])
        print("backup:", backup)
    conn.close()
    verb = "would set" if args.dry_run else "set"
    for stars in sorted(updated, reverse=True):
        print(f"{verb} {stars} stars: {len(updated[stars])} {updated[stars]}")
    print(f"skipped (unknown id or already rated): {len(skipped)} {skipped}")
