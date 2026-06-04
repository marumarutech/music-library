from __future__ import annotations

import re
import uuid
from pathlib import Path

from core.metadata import INVALID_FILENAME_CHARS
from core.paths import SYNCED_FOLDER

_WINDOWS_RESERVED = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }
)


def sanitize_stem(text: str, *, max_length: int = 180) -> str:
    """Make a safe filename stem for Windows."""
    stem = text.strip().rstrip(".")
    stem = INVALID_FILENAME_CHARS.sub("_", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    if stem.upper() in _WINDOWS_RESERVED:
        stem = f"_{stem}"
    if not stem:
        stem = "untitled"
    if len(stem) > max_length:
        stem = stem[:max_length].rstrip()
    return stem or "untitled"


def stem_taken(library_dir: Path, stem: str, *, exclude: Path | None = None) -> bool:
    for folder in (library_dir, library_dir / SYNCED_FOLDER):
        if not folder.is_dir():
            continue
        candidate = (folder / f"{stem}.mp3").resolve()
        if not candidate.is_file():
            continue
        if exclude is not None and candidate == exclude.resolve():
            continue
        return True
    return False


def ensure_unique_stem(
    library_dir: Path,
    base_stem: str,
    *,
    exclude: Path | None = None,
) -> str:
    """Return base_stem, or base_stem_<8-char id> when library/済み already has that name."""
    stem = sanitize_stem(base_stem)
    if not stem_taken(library_dir, stem, exclude=exclude):
        return stem

    for _ in range(100):
        candidate = sanitize_stem(f"{stem}_{uuid.uuid4().hex[:8]}")
        if not stem_taken(library_dir, candidate, exclude=exclude):
            return candidate

    raise RuntimeError("一意なファイル名を割り当てられませんでした")
