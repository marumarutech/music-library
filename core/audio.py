from __future__ import annotations

import subprocess
from pathlib import Path


class AudioProcessError(RuntimeError):
    pass


# -14 LUFS: common target for streaming / music libraries
DEFAULT_TARGET_LUFS = -14.0


def _apply_ffmpeg_audio_filter(
    path: Path,
    af: str,
    *,
    bitrate_kbps: str,
    tmp_suffix: str,
    error_message: str,
) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"ファイルが見つかりません: {path}")

    tmp = path.with_name(f"{path.stem}.{tmp_suffix}.tmp.mp3")
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(path),
                "-af",
                af,
                "-codec:a",
                "libmp3lame",
                "-b:a",
                f"{bitrate_kbps}k",
                str(tmp),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise AudioProcessError(result.stderr.strip() or error_message)
        tmp.replace(path)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise


def trim_silence_edges(
    path: Path,
    *,
    bitrate_kbps: str = "192",
    threshold_db: int = -50,
    min_silence_sec: float = 0.1,
) -> None:
    """Trim leading and trailing silence from an MP3 file in place."""
    threshold = f"{threshold_db}dB"
    duration = str(min_silence_sec)
    af = (
        f"silenceremove=start_periods=1:start_silence={duration}:start_threshold={threshold},"
        "areverse,"
        f"silenceremove=start_periods=1:start_silence={duration}:start_threshold={threshold},"
        "areverse"
    )
    _apply_ffmpeg_audio_filter(
        path,
        af,
        bitrate_kbps=bitrate_kbps,
        tmp_suffix="_trim",
        error_message="ffmpeg の無音トリムに失敗しました",
    )


def normalize_loudness(
    path: Path,
    *,
    bitrate_kbps: str = "192",
    target_lufs: float = DEFAULT_TARGET_LUFS,
) -> None:
    """Normalize perceived loudness using FFmpeg loudnorm (single-pass)."""
    af = f"loudnorm=I={target_lufs}:TP=-1:LRA=11"
    _apply_ffmpeg_audio_filter(
        path,
        af,
        bitrate_kbps=bitrate_kbps,
        tmp_suffix="_norm",
        error_message="ffmpeg の音量正規化に失敗しました",
    )
