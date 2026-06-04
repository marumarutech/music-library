from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yt_dlp

from core.audio import normalize_loudness, trim_silence_edges
from core.filenames import ensure_unique_stem
from core.metadata import MetadataError, read_tags, resolve_library_mp3, validate_filename_stem, write_tags
from core.paths import DEFAULT_LIBRARY, SYNCED_FOLDER


class FFmpegNotFoundError(RuntimeError):
    pass


@dataclass
class DownloadResult:
    titles: list[str]
    output_dir: Path


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise FFmpegNotFoundError(
            "ffmpeg が見つかりません。MP3 変換に必要です。"
            " https://ffmpeg.org/download.html からインストールし、PATH に追加してください。"
        )


def resolve_deno_path() -> str | None:
    if path := shutil.which("deno"):
        return path

    links = Path.home() / "AppData/Local/Microsoft/WinGet/Links/deno.exe"
    if links.is_file():
        return str(links)

    packages = Path.home() / "AppData/Local/Microsoft/WinGet/Packages"
    for candidate in packages.glob("DenoLand.Deno*/deno.exe"):
        if candidate.is_file():
            return str(candidate)

    return None


def _yt_dlp_youtube_opts() -> dict:
    opts: dict = {
        # Deno + JS challenge solver (first run may download scripts from GitHub / npm)
        "remote_components": ["ejs:github", "ejs:npm"],
    }
    deno_path = resolve_deno_path()
    if deno_path:
        opts["js_runtimes"] = {"deno": {"path": deno_path}}
    return opts


def _mp3_path(ydl: yt_dlp.YoutubeDL, info: dict) -> Path | None:
    filepath = info.get("filepath")
    if filepath:
        return Path(filepath).with_suffix(".mp3")
    return Path(ydl.prepare_filename(info)).with_suffix(".mp3")


def _collect_downloads(ydl: yt_dlp.YoutubeDL, info: dict) -> tuple[list[str], list[Path]]:
    entries = info.get("entries")
    if entries:
        titles: list[str] = []
        paths: list[Path] = []
        for entry in entries:
            if not entry:
                continue
            titles.append(entry.get("title") or "?")
            mp3 = _mp3_path(ydl, entry)
            if mp3 and mp3.is_file():
                paths.append(mp3)
        return titles, paths

    title = info.get("title") or info.get("webpage_url") or "?"
    mp3 = _mp3_path(ydl, info)
    paths = [mp3] if mp3 and mp3.is_file() else []
    return [title], paths


def download_audio(
    url: str,
    output_dir: Path = DEFAULT_LIBRARY,
    quality: str = "192",
    playlist: bool = False,
    trim_silence: bool = True,
    normalize_loudness_enabled: bool = True,
    on_progress: Callable[[str], None] | None = None,
) -> DownloadResult:
    ensure_ffmpeg()
    output_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(output_dir / "%(title)s.%(ext)s")

    ydl_opts: dict = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": not playlist,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality,
            }
        ],
        **_yt_dlp_youtube_opts(),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if info is None:
            raise RuntimeError("動画情報を取得できませんでした")

        titles, paths = _collect_downloads(ydl, info)

    if trim_silence and paths:
        if on_progress:
            on_progress("無音をトリミング中…")
        for path in paths:
            trim_silence_edges(path, bitrate_kbps=quality)

    if normalize_loudness_enabled and paths:
        if on_progress:
            on_progress("音量を正規化中…")
        for path in paths:
            normalize_loudness(path, bitrate_kbps=quality)

    return DownloadResult(titles=titles, output_dir=output_dir)


def _track_dict(path: Path, library_dir: Path) -> dict:
    stat = path.stat()
    title, artist, album = read_tags(path)
    rel = path.relative_to(library_dir.resolve())
    synced_dir = (library_dir / SYNCED_FOLDER).resolve()
    return {
        "path": rel.as_posix(),
        "name": path.stem,
        "filename": path.name,
        "title": title,
        "artist": artist,
        "album": album,
        "synced": path.parent.resolve() == synced_dir,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "modified": stat.st_mtime,
    }


def list_tracks(library_dir: Path = DEFAULT_LIBRARY) -> list[dict]:
    if not library_dir.is_dir():
        return []

    tracks: list[dict] = []
    for path in library_dir.glob("*.mp3"):
        tracks.append(_track_dict(path, library_dir))

    synced_dir = library_dir / SYNCED_FOLDER
    if synced_dir.is_dir():
        for path in synced_dir.glob("*.mp3"):
            tracks.append(_track_dict(path, library_dir))

    tracks.sort(key=lambda track: track["modified"], reverse=True)
    return tracks


def update_track(
    relative_path: str,
    *,
    new_stem: str,
    title: str,
    artist: str,
    album: str = "",
    library_dir: Path = DEFAULT_LIBRARY,
) -> dict:
    path = resolve_library_mp3(library_dir, relative_path)
    if not path.is_file():
        raise FileNotFoundError(f"ファイルが見つかりません: {relative_path}")

    requested_stem = validate_filename_stem(new_stem)
    title = title.strip()
    if not title:
        raise MetadataError("曲名を入力してください")
    artist = artist.strip()
    album = album.strip()

    new_path = path
    if requested_stem != path.stem:
        unique_stem = ensure_unique_stem(library_dir, requested_stem, exclude=path)
        new_path = path.with_name(f"{unique_stem}.mp3")
        path.rename(new_path)

    write_tags(new_path, title, artist, album)

    return _track_dict(new_path, library_dir)


def move_track(
    relative_path: str,
    *,
    to_synced: bool,
    library_dir: Path = DEFAULT_LIBRARY,
) -> dict:
    path = resolve_library_mp3(library_dir, relative_path)
    if not path.is_file():
        raise FileNotFoundError(f"ファイルが見つかりません: {relative_path}")

    synced_dir = library_dir / SYNCED_FOLDER
    synced_dir.mkdir(exist_ok=True)
    is_synced = path.parent.resolve() == synced_dir.resolve()

    if to_synced and is_synced:
        raise MetadataError("既に済みフォルダにあります")
    if not to_synced and not is_synced:
        raise MetadataError("既にライブラリにあります")

    dest = (synced_dir if to_synced else library_dir) / path.name
    if dest.exists():
        raise MetadataError(f"移動先に同じファイル名が既に存在します: {dest.name}")

    path.rename(dest)
    return _track_dict(dest, library_dir)
