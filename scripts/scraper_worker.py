"""Background worker API for launching scraper jobs from the web app."""

import json
import os
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from init_es_index import main as init_index
from wait_for_services import wait_es, wait_mongo

HOST = os.getenv("SCRAPER_WORKER_HOST", "0.0.0.0")
PORT = int(os.getenv("SCRAPER_WORKER_PORT", "8000"))
SCRAPER_CWD = os.getenv("SCRAPER_WORKER_SCRAPER_CWD", "/app/scraper")
JOB_DIR = Path(os.getenv("SCRAPER_WORKER_JOB_DIR", "/tmp/scraper_jobs"))

STATE_LOCK = threading.Lock()
STATE = {
    "running": False,
    "current_job": None,
    "last_job": None,
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_summary(path):
    file_path = Path(path)
    if not file_path.exists():
        return None

    try:
        content = file_path.read_text(encoding="utf-8")
        return json.loads(content)
    except Exception:
        return None


def start_job(mode):
    with STATE_LOCK:
        if STATE["running"]:
            return None

        JOB_DIR.mkdir(parents=True, exist_ok=True)
        job_id = str(uuid.uuid4())
        log_path = JOB_DIR / f"{job_id}.log"
        stats_path = JOB_DIR / f"{job_id}.json"

        job = {
            "job_id": job_id,
            "mode": mode,
            "status": "running",
            "started_at": now_iso(),
            "ended_at": "",
            "return_code": None,
            "error": "",
            "log_path": str(log_path),
            "stats_path": str(stats_path),
            "summary": None,
        }

        STATE["running"] = True
        STATE["current_job"] = job

    thread = threading.Thread(target=run_job, args=(job,), daemon=True)
    thread.start()
    return job


def run_job(job):
    command = [
        sys.executable,
        "-m",
        "scrapy",
        "crawl",
        "ouvrages",
        "-a",
        f"run_mode={job['mode']}",
        "-a",
        f"stats_path={job['stats_path']}",
    ]

    return_code = None
    error_message = ""

    try:
        with open(job["log_path"], "w", encoding="utf-8") as log_file:
            log_file.write(f"Started at: {job['started_at']}\n")
            log_file.write(f"Mode: {job['mode']}\n")
            log_file.write(f"Command: {' '.join(command)}\n\n")
            log_file.flush()

            process = subprocess.Popen(
                command,
                cwd=SCRAPER_CWD,
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )
            return_code = process.wait()
    except Exception as error:
        error_message = str(error)

    summary = load_summary(job["stats_path"])
    final_status = "success"
    if error_message:
        final_status = "error"
    elif return_code != 0:
        final_status = "failed"

    finished_job = {
        "job_id": job["job_id"],
        "mode": job["mode"],
        "status": final_status,
        "started_at": job["started_at"],
        "ended_at": now_iso(),
        "return_code": return_code,
        "error": error_message,
        "log_path": job["log_path"],
        "stats_path": job["stats_path"],
        "summary": summary,
    }

    with STATE_LOCK:
        STATE["running"] = False
        STATE["current_job"] = None
        STATE["last_job"] = finished_job


def get_status_snapshot():
    with STATE_LOCK:
        return {
            "running": STATE["running"],
            "current_job": STATE["current_job"],
            "last_job": STATE["last_job"],
        }


class WorkerHandler(BaseHTTPRequestHandler):
    def _write_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            snapshot = get_status_snapshot()
            self._write_json(200, {"status": "ok", "running": snapshot["running"]})
            return

        if self.path == "/jobs/status":
            self._write_json(200, get_status_snapshot())
            return

        self._write_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path == "/jobs/latest":
            self._start_job_with_mode("latest")
            return

        if self.path == "/jobs/backfill":
            self._start_job_with_mode("backfill")
            return

        self._write_json(404, {"error": "Not found"})

    def _start_job_with_mode(self, mode):
        job = start_job(mode)
        if job is None:
            self._write_json(
                409,
                {
                    "error": "A job is already running",
                    "status": get_status_snapshot(),
                },
            )
            return

        self._write_json(202, {"message": "Job started", "job": job})

    def log_message(self, format, *args):
        message = format % args
        print(f"[worker] {self.address_string()} {message}")


def main():
    print("==> Waiting for dependencies...")
    wait_mongo()
    wait_es()

    print("==> Initializing Elasticsearch index...")
    init_index()

    print(f"==> Scraper worker API listening on {HOST}:{PORT}")
    server = ThreadingHTTPServer((HOST, PORT), WorkerHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
