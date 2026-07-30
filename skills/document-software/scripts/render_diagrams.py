"""Render the PlantUML blocks of a Markdown reference as SVG for human readers.

Usage: python render_diagrams.py <reference.md> <out_dir> [--png-dir DIR] [--server URL]

Every ```plantuml block must start with "@startuml <name>". For each block the script inserts
the shared style of assets/plantuml-style.iuml and writes <out_dir>/<name>.svg, rendered by a
Kroki server. With --png-dir it also writes <name>.png there, to look at the layout (an agent
can view PNG but not SVG); keep that folder out of the project, e.g. in a scratchpad.

The diagram text is sent to the server: https://kroki.io by default. For code that must not
leave the machine, run a local server (docker run -d -p 8000:8000 yuzutech/kroki) and pass
--server http://localhost:8000.
"""
import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

STYLE = Path(__file__).resolve().parent.parent / "assets" / "plantuml-style.iuml"
BLOCK = re.compile(r"```plantuml\n(@startuml[^\n]*)\n(.*?)```", re.S)
TIMEOUT_S = 60


def render(source: str, server: str, fmt: str) -> bytes:
    """Diagram of a PlantUML source in ``fmt`` (svg, png) from a Kroki server."""
    request = urllib.request.Request(f"{server.rstrip('/')}/plantuml/{fmt}", data=source.encode("utf-8"),
                                     headers={"Content-Type": "text/plain", "User-Agent": "render_diagrams"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
        return response.read()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("reference", type=Path, help="Markdown file with plantuml blocks")
    parser.add_argument("out_dir", type=Path, help="folder for the .svg files, e.g. docs")
    parser.add_argument("--png-dir", type=Path, help="also write PNGs here to check the layout")
    parser.add_argument("--server", default="https://kroki.io", help="Kroki server (default: %(default)s)")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    text = args.reference.read_text(encoding="utf-8")
    style = STYLE.read_text(encoding="utf-8")
    targets = [(args.out_dir, "svg")] + ([(args.png_dir, "png")] if args.png_dir else [])
    for folder, _ in targets:
        folder.mkdir(parents=True, exist_ok=True)
    failed = 0
    for start, body in BLOCK.findall(text):
        words = start.split()
        name = words[1] if len(words) > 1 else ""
        if not re.fullmatch(r"[\w-]+", name):
            print(f"skipped a block without '@startuml <name>': {start}")
            failed += 1
            continue
        source = f"{start}\n{style}{body}"
        try:
            for folder, fmt in targets:
                (folder / f"{name}.{fmt}").write_bytes(render(source, args.server, fmt))
        except urllib.error.HTTPError as error:
            print(f"{name}: HTTP {error.code} {error.read().decode('utf-8', 'replace')[:200]}")
            failed += 1
            continue
        print(f"{name}: {', '.join(str(folder / f'{name}.{fmt}') for folder, fmt in targets)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
