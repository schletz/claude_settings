"""Merge the result files of the round-1 agents and check that every cluster was reviewed.

Usage: python merge_candidates.py <clusters.json> <cand-dir> [--out merged.json]
<clusters.json> is the (filtered) output of list_clusters.py; <cand-dir> holds cand_*.json
files in the format described in references/runde1-anweisung.md. Prints all candidates sorted
by tier and lists clusters that no agent reported as reviewed.
"""

import argparse
import json
import sys
from pathlib import Path

TIER_ORDER = {"4": 0, "3": 1, "grenzfall": 2}


def load_json(path: Path):
    """Read JSON as UTF-8, falling back to cp1252 (some agents write the Windows default)."""
    raw = path.read_bytes()
    try:
        return json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return json.loads(raw.decode("cp1252"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("clusters", type=Path)
    ap.add_argument("cand_dir", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    expected = {c["cluster"] for c in load_json(args.clusters)["clusters"]}
    reviewed: set[int] = set()
    candidates: list[dict] = []
    for path in sorted(args.cand_dir.glob("cand_*.json")):
        data = load_json(path)
        if isinstance(data, list):  # legacy format without a reviewed list
            candidates += data
            reviewed |= {c["cluster"] for c in data}
        else:
            candidates += data["candidates"]
            reviewed |= set(data["reviewed"])

    candidates.sort(key=lambda c: (TIER_ORDER[str(c["tier"])], c["cluster"]))
    sys.stdout.reconfigure(encoding="utf-8")
    for c in candidates:
        star = "*" if c.get("key_moment") else " "
        name = c["file"] if len(c["file"]) <= 12 else c["file"][:26]
        print(f'{str(c["tier"])[:2]}{star} c{c["cluster"]:3d} {name} | '
              f'{c.get("who", "")} | {c["statement"]} | {c["note"]}')
    missing = sorted(expected - reviewed)
    print(f"\n{len(candidates)} candidates, {len(reviewed & expected)}/{len(expected)} clusters reviewed")
    if missing:
        print("NOT REVIEWED, look at these yourself or re-dispatch:", missing)
    if args.out:
        args.out.write_text(json.dumps(candidates, ensure_ascii=False, indent=1), encoding="utf-8")
