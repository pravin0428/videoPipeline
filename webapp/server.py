#!/usr/bin/env python3
"""
Video Engine — Web frontend
===========================
A thin FastAPI wrapper around video_engine.main.run_pipeline().

Flow:
  1. User pastes a structured project JSON in the browser.
  2. POST /api/generate  -> validates, writes project.json to a job dir,
     runs the pipeline in a background thread, returns a job_id.
  3. Browser polls GET /api/status/{job_id} for stage/progress/logs.
  4. When done, the video is served at /api/video/{job_id}
     and downloaded from /api/download/{job_id}.

Run (from repo root, with the atlas venv that has the engine deps):
    atlas/venv/bin/python -m uvicorn webapp.server:app --port 8080
or simply:
    webapp/run.sh
"""
import asyncio
import io
import json
import os
import re
import sys
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

STATIC_DIR = Path(__file__).resolve().parent / "static"
JOBS_ROOT = ROOT / "video_engine" / "output" / "_web"
JOBS_ROOT.mkdir(parents=True, exist_ok=True)

# 7 pipeline stages, in order (see video_engine/main.py:run_pipeline)
STAGES = [
    "Load Project",
    "Continuity Fill",
    "Format Prompts",
    "Generate TTS",
    "Generate Videos",
    "Generate Subtitles",
    "Render Final Video",
]

app = FastAPI(title="Video Engine Frontend")


def _shot_enum_fields() -> dict[str, set]:
    """Map each enum-typed Shot field -> its set of valid string values.

    Built by introspecting the Shot dataclass so it stays in sync with models.py.
    """
    from enum import Enum
    from typing import get_type_hints
    from dataclasses import fields
    from video_engine.models import Shot

    hints = get_type_hints(Shot)
    out: dict[str, set] = {}
    for f in fields(Shot):
        t = hints.get(f.name, f.type)
        if isinstance(t, type) and issubclass(t, Enum):
            out[f.name] = {e.value for e in t}
    return out


def _sanitize(data: dict) -> list[str]:
    """Drop invalid enum values from shots so the engine's defaults apply.

    Returns human-readable warnings for anything that was corrected, instead of
    letting a single bad value fail the whole pipeline.
    """
    valid = _shot_enum_fields()
    warnings: list[str] = []
    for scene in data.get("scenes", []):
        if not isinstance(scene, dict):
            continue
        sid = scene.get("scene_id", "?")
        for shot in scene.get("shots", []):
            if not isinstance(shot, dict):
                continue
            shid = shot.get("shot_id", "?")
            for field_name, allowed in valid.items():
                if field_name in shot and shot[field_name] not in allowed:
                    warnings.append(
                        f"scene {sid} shot {shid}: '{shot[field_name]}' is not a valid "
                        f"{field_name} — using the default instead."
                    )
                    del shot[field_name]  # dropped -> dataclass default kicks in
    return warnings

# In-memory job store. Fine for a single-machine local tool.
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()
# The pipeline redirects stdout, so only run one at a time.
_run_lock = threading.Lock()


class GenerateRequest(BaseModel):
    project: str  # raw JSON text pasted by the user


class _JobWriter(io.TextIOBase):
    """Tees pipeline stdout into a job's log buffer and the real console."""

    def __init__(self, job_id: str, real):
        self.job_id = job_id
        self.real = real

    def write(self, s: str) -> int:
        if s:
            with _jobs_lock:
                job = _jobs.get(self.job_id)
                if job is not None:
                    job["logs"].append(s)
                    # Track progress from "Step N/7: <label>" lines.
                    m = re.search(r"Step\s+(\d+)/(\d+)", s)
                    if m:
                        job["stage_num"] = int(m.group(1))
                        job["total_stages"] = int(m.group(2))
        try:
            self.real.write(s)
        except Exception:
            pass
        return len(s)

    def flush(self):
        try:
            self.real.flush()
        except Exception:
            pass


def _find_output(job_dir: Path) -> Path | None:
    matches = list(job_dir.glob("*_documentary.mp4"))
    return matches[0] if matches else None


def _worker(job_id: str, project_path: str, job_dir: Path):
    from video_engine.main import run_pipeline

    # Serialize runs — run_pipeline redirects the process-wide stdout.
    with _run_lock:
        writer = _JobWriter(job_id, sys.stdout)
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = writer
        try:
            with _jobs_lock:
                _jobs[job_id]["status"] = "running"
            asyncio.run(run_pipeline(project_path))
            out = _find_output(job_dir)
            with _jobs_lock:
                if out and out.exists():
                    _jobs[job_id]["status"] = "done"
                    _jobs[job_id]["output"] = str(out)
                    _jobs[job_id]["stage_num"] = len(STAGES)
                else:
                    _jobs[job_id]["status"] = "error"
                    _jobs[job_id]["error"] = "Pipeline finished but no output video was produced."
        except Exception as e:  # surface any pipeline failure to the UI
            with _jobs_lock:
                _jobs[job_id]["status"] = "error"
                _jobs[job_id]["error"] = str(e)
        finally:
            sys.stdout, sys.stderr = old_out, old_err


@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/config")
def config():
    """Expose whether a Pexels key is configured, so the UI can warn."""
    from video_engine.main import _get_api_key
    return {"pexels_key": bool(_get_api_key())}


@app.post("/api/generate")
def generate(req: GenerateRequest):
    # Validate the pasted JSON before starting anything.
    try:
        data = json.loads(req.project)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Top-level JSON must be an object.")
    if "title" not in data or "scenes" not in data:
        raise HTTPException(status_code=400, detail="Project JSON must contain 'title' and 'scenes'.")

    # Correct invalid enum values instead of failing the whole run.
    warnings = _sanitize(data)

    job_id = uuid.uuid4().hex[:12]
    job_dir = JOBS_ROOT / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Force output into this job's directory regardless of what the user set.
    data["output_path"] = str(job_dir)
    project_path = job_dir / "project.json"
    project_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    seed_logs = [f"⚠ {w}\n" for w in warnings]
    with _jobs_lock:
        _jobs[job_id] = {
            "status": "queued",
            "logs": seed_logs,
            "stage_num": 0,
            "total_stages": len(STAGES),
            "output": None,
            "error": None,
            "title": data.get("title", "video"),
        }

    threading.Thread(
        target=_worker, args=(job_id, str(project_path), job_dir), daemon=True
    ).start()
    return {"job_id": job_id}


@app.get("/api/status/{job_id}")
def status(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Unknown job id.")
        stage_num = job["stage_num"]
        stage_label = STAGES[stage_num - 1] if 1 <= stage_num <= len(STAGES) else "Starting…"
        return {
            "status": job["status"],
            "stage_num": stage_num,
            "total_stages": len(STAGES),
            "stage_label": stage_label,
            "progress": round(100 * stage_num / len(STAGES)),
            "error": job["error"],
            "log": "".join(job["logs"])[-6000:],  # tail
            "has_video": job["status"] == "done",
        }


@app.get("/api/video/{job_id}")
def video(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job or not job.get("output"):
        raise HTTPException(status_code=404, detail="Video not ready.")
    return FileResponse(job["output"], media_type="video/mp4")


@app.get("/api/download/{job_id}")
def download(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job or not job.get("output"):
        raise HTTPException(status_code=404, detail="Video not ready.")
    filename = f"{job.get('title', 'video')}_documentary.mp4"
    return FileResponse(job["output"], media_type="video/mp4", filename=filename)
