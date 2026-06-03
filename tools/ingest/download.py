#!/usr/bin/env python3
"""Download YouTube audio as MP3 into the music library (personal use)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yt_dlp

# Allow running as script: python tools/ingest/download.py
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.ingest import download_audio, ensure_ffmpeg
from core.paths import DEFAULT_LIBRARY


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="YouTube 動画の URL から音声だけを MP3 でダウンロードします（個人利用向け）。",
    )
    parser.add_argument("url", help="YouTube 動画の URL")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_LIBRARY,
        help=f"保存先ディレクトリ (default: {DEFAULT_LIBRARY})",
    )
    parser.add_argument(
        "-q",
        "--quality",
        default="192",
        help="MP3 ビットレート kbps (default: 192)",
    )
    parser.add_argument(
        "--playlist",
        action="store_true",
        help="プレイリスト URL の場合、全曲をダウンロードする",
    )
    parser.add_argument(
        "--no-trim-silence",
        action="store_true",
        help="先頭・末尾の無音トリムをスキップする",
    )
    parser.add_argument(
        "--no-normalize-loudness",
        action="store_true",
        help="音量正規化をスキップする",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        ensure_ffmpeg()
        result = download_audio(
            args.url,
            args.output,
            args.quality,
            args.playlist,
            trim_silence=not args.no_trim_silence,
            normalize_loudness_enabled=not args.no_normalize_loudness,
        )
        print(f"\n{len(result.titles)} 件ダウンロードしました:")
        for title in result.titles:
            print(f"  - {title}")
        print(f"保存先: {result.output_dir.resolve()}")
        return 0
    except yt_dlp.utils.DownloadError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
