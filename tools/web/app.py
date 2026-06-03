#!/usr/bin/env python3
"""Local web UI for ingesting YouTube audio into the music library."""

from __future__ import annotations

import sys
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import uvicorn
import yt_dlp
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.ingest import FFmpegNotFoundError, download_audio, list_tracks, resolve_deno_path
from core.paths import DEFAULT_LIBRARY

STATIC_DIR = Path(__file__).resolve().parent / "static"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class Job:
    status: JobStatus = JobStatus.PENDING
    message: str = ""
    titles: list[str] = field(default_factory=list)


jobs: dict[str, Job] = {}
jobs_lock = threading.Lock()

app = FastAPI(title="music-library", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class DownloadRequest(BaseModel):
    url: str = Field(min_length=1)
    quality: str = "192"
    playlist: bool = False
    trim_silence: bool = True
    normalize_loudness: bool = True


class DownloadResponse(BaseModel):
    job_id: str


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str
    titles: list[str]


def _set_job_message(job_id: str, message: str) -> None:
    with jobs_lock:
        job = jobs.get(job_id)
        if job is not None:
            job.message = message


def run_download(
    job_id: str,
    url: str,
    quality: str,
    playlist: bool,
    trim_silence: bool,
    normalize_loudness: bool,
) -> None:
    with jobs_lock:
        job = jobs[job_id]
        job.status = JobStatus.RUNNING
        job.message = "ダウンロード中…"

    try:
        result = download_audio(
            url,
            DEFAULT_LIBRARY,
            quality,
            playlist,
            trim_silence=trim_silence,
            normalize_loudness_enabled=normalize_loudness,
            on_progress=lambda msg: _set_job_message(job_id, msg),
        )
        with jobs_lock:
            job = jobs[job_id]
            job.status = JobStatus.DONE
            job.titles = result.titles
            job.message = f"{len(result.titles)} 件完了"
    except yt_dlp.utils.DownloadError as exc:
        with jobs_lock:
            job = jobs[job_id]
            job.status = JobStatus.ERROR
            job.message = str(exc)
    except Exception as exc:
        with jobs_lock:
            job = jobs[job_id]
            job.status = JobStatus.ERROR
            job.message = str(exc)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    try:
        from core.ingest import ensure_ffmpeg

        ensure_ffmpeg()
        ffmpeg_ok = True
        ffmpeg_message = ""
    except FFmpegNotFoundError as exc:
        ffmpeg_ok = False
        ffmpeg_message = str(exc)

    return {
        "ffmpeg_ok": ffmpeg_ok,
        "ffmpeg_message": ffmpeg_message,
        "deno_ok": resolve_deno_path() is not None,
        "deno_path": resolve_deno_path() or "",
        "library": str(DEFAULT_LIBRARY.resolve()),
    }


@app.get("/api/tracks")
def tracks() -> dict:
    return {"tracks": list_tracks(DEFAULT_LIBRARY)}


@app.post("/api/download", response_model=DownloadResponse)
def start_download(body: DownloadRequest) -> DownloadResponse:
    job_id = uuid.uuid4().hex[:12]
    with jobs_lock:
        jobs[job_id] = Job()

    thread = threading.Thread(
        target=run_download,
        args=(job_id, body.url.strip(), body.quality, body.playlist, body.trim_silence, body.normalize_loudness),
        daemon=True,
    )
    thread.start()
    return DownloadResponse(job_id=job_id)


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    with jobs_lock:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")

        return JobResponse(
            job_id=job_id,
            status=job.status,
            message=job.message,
            titles=job.titles,
        )


def main() -> None:
    print(f"music-library: http://127.0.0.1:8765")
    print(f"library: {DEFAULT_LIBRARY.resolve()}")
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")


if __name__ == "__main__":
    main()
