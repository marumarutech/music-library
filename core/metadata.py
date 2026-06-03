from __future__ import annotations

import re
from pathlib import Path

from mutagen.id3 import ID3, ID3NoHeaderError, TALB, TIT2, TPE1
from mutagen.mp3 import MP3

INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

class MetadataError(ValueError):
    pass


def read_tags(path: Path) -> tuple[str, str, str]:
    """Return (title, artist, album). Title falls back to the file stem when untagged."""
    title = path.stem
    artist = ""
    album = ""

    try:
        audio = MP3(path, ID3=ID3)
    except Exception:
        return title, artist, album

    if not audio.tags:
        return title, artist, album

    if tit2 := audio.tags.get("TIT2"):
        if tit2.text:
            title = str(tit2.text[0])
    if tpe1 := audio.tags.get("TPE1"):
        if tpe1.text:
            artist = str(tpe1.text[0])
    if talb := audio.tags.get("TALB"):
        if talb.text:
            album = str(talb.text[0])

    return title, artist, album


def write_tags(path: Path, title: str, artist: str, album: str = "") -> None:
    try:
        audio = MP3(path, ID3=ID3)
    except ID3NoHeaderError:
        audio = MP3(path)
        audio.add_tags()

    if audio.tags is None:
        audio.add_tags()

    audio.tags["TIT2"] = TIT2(encoding=3, text=title)
    if artist:
        audio.tags["TPE1"] = TPE1(encoding=3, text=artist)
    elif "TPE1" in audio.tags:
        del audio.tags["TPE1"]

    if album:
        audio.tags["TALB"] = TALB(encoding=3, text=album)
    elif "TALB" in audio.tags:
        del audio.tags["TALB"]

    audio.save()


def validate_filename_stem(stem: str) -> str:
    stem = stem.strip().rstrip(".")
    if not stem:
        raise MetadataError("ファイル名を入力してください")
    if INVALID_FILENAME_CHARS.search(stem):
        raise MetadataError('ファイル名に使えない文字が含まれています（\\ / : * ? " < > | など）')
    return stem


def resolve_library_mp3(library_dir: Path, relative_path: str) -> Path:
    rel = Path(*Path(relative_path.replace("\\", "/")).parts)
    if rel.is_absolute() or ".." in rel.parts or rel.name == "":
        raise MetadataError("無効なファイルパスです")
    if rel.suffix.lower() != ".mp3":
        raise MetadataError("無効なファイル名です")

    library_resolved = library_dir.resolve()
    path = (library_dir / rel).resolve()

    if not path.is_relative_to(library_resolved):
        raise MetadataError("無効なファイルパスです")

    return path
