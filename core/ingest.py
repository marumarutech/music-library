from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yt_dlp

from core.audio import normalize_loudness, trim_silence_edges
from core.paths import DEFAULT_LIBRARY


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


def list_tracks(library_dir: Path = DEFAULT_LIBRARY) -> list[dict]:
    if not library_dir.is_dir():
        return []

    tracks: list[dict] = []
    for path in sorted(library_dir.glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = path.stat()
        tracks.append(
            {
                "name": path.stem,
                "filename": path.name,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified": stat.st_mtime,
            }
        )
    return tracks
