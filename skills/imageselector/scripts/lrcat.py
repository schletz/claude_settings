"""Shared helpers for reading and safely writing a Lightroom Classic catalog (.lrcat)."""

import shutil
import sqlite3
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

DEFAULT_CATALOG = Path(r"D:\Fotos\Lightroom_Catalog\Lightroom_Catalog-v13-3.lrcat")

# Videos live in the catalog too but are not part of the photo selection.
VIDEO_EXTENSIONS = {"mp4", "mov", "mts", "m2ts", "avi", "mxf"}

# Lightroom keeps these next to the catalog while it is open.
_LOCK_SUFFIXES = (".lock", "-wal", "-shm")


class CatalogBusyError(RuntimeError):
    """Raised when the catalog must not be written because Lightroom may hold it."""


def _lightroom_running() -> bool:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Lightroom.exe"],
                         capture_output=True, text=True).stdout
    return "Lightroom.exe" in out


def _lock_files(catalog: Path) -> list[Path]:
    candidates = (catalog.with_name(catalog.name + s) for s in _LOCK_SUFFIXES)
    return [p for p in candidates if p.exists()]


def _blocking_files(catalog: Path) -> list[Path]:
    """Files that make a write unsafe: Lightroom's .lock or a -wal holding uncommitted pages.

    An empty -wal and the -shm also appear after plain read-only access and are harmless;
    a non-empty -wal would be missing from a backup of the main file alone.
    """
    return [p for p in _lock_files(catalog)
            if p.suffix == ".lock" or (p.name.endswith("-wal") and p.stat().st_size > 0)]


def open_readonly(catalog: Path) -> sqlite3.Connection:
    """Open the catalog for reading, working on a temp copy if Lightroom has it open."""
    if not _lock_files(catalog):
        return sqlite3.connect(f"file:{catalog.as_posix()}?mode=ro", uri=True)
    # A live WAL database is only consistent together with its -wal/-shm files.
    tmp = Path(tempfile.mkdtemp(prefix="lrcat-"))
    for suffix in ("", "-wal", "-shm"):
        src = catalog.with_name(catalog.name + suffix)
        if src.exists():
            shutil.copy2(src, tmp / src.name)
    return sqlite3.connect(str(tmp / catalog.name))


def open_for_write(catalog: Path) -> tuple[sqlite3.Connection, Path]:
    """Verify Lightroom is closed, back up the catalog and return a writable connection.

    Returns the connection and the path of the backup.
    Raises CatalogBusyError if Lightroom is running or lock files exist.
    """
    if _lightroom_running():
        raise CatalogBusyError("Lightroom.exe is running - close Lightroom first.")
    locks = _blocking_files(catalog)
    if locks:
        raise CatalogBusyError("Lock files present: " + ", ".join(p.name for p in locks))
    backup = catalog.with_name(f"{catalog.name}.bak-imageselector-{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(catalog, backup)
    return sqlite3.connect(str(catalog)), backup


def folder_images(conn: sqlite3.Connection, folder: Path) -> list[dict]:
    """Return all catalog images whose folder equals `folder`, sorted by capture time."""
    wanted = folder.as_posix().rstrip("/").lower()
    rows = conn.execute("""
        select i.id_local, i.rating, i.captureTime, f.baseName, f.extension,
               r.absolutePath || fo.pathFromRoot
        from Adobe_images i
        join AgLibraryFile f on i.rootFile = f.id_local
        join AgLibraryFolder fo on f.folder = fo.id_local
        join AgLibraryRootFolder r on fo.rootFolder = r.id_local
        where i.captureTime is not null
        order by i.captureTime, f.baseName""").fetchall()
    images = []
    for id_local, rating, capture, base, ext, path in rows:
        if path.replace("\\", "/").rstrip("/").lower() != wanted:
            continue
        if ext.lower() in VIDEO_EXTENSIONS:
            continue
        images.append({"id": id_local, "file": f"{base}.{ext}", "captureTime": capture,
                       "rating": int(rating or 0)})
    return images
