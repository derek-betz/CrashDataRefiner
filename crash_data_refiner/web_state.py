"""Run-state models and registry helpers for the Flask web surface."""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


MAX_LOG_ENTRIES = 1500


@dataclass
class RunState:
    run_id: str
    created_at: datetime
    status: str = "queued"
    message: str = ""
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    output_dir: Optional[Path] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    log_entries: List[Dict[str, Any]] = field(default_factory=list)
    log_seq: int = 0
    last_log: str = ""
    lock: threading.Lock = field(default_factory=threading.Lock)

    def append_log(self, text: str, *, level: str = "info") -> None:
        if not text:
            return
        lines = [line for line in text.splitlines() if line.strip()]
        if not lines:
            return
        now = utcnow().isoformat()
        with self.lock:
            for line in lines:
                self.log_seq += 1
                entry = {
                    "seq": self.log_seq,
                    "ts": now,
                    "level": level,
                    "text": line,
                }
                self.log_entries.append(entry)
                self.last_log = line
            if len(self.log_entries) > MAX_LOG_ENTRIES:
                overflow = len(self.log_entries) - MAX_LOG_ENTRIES
                del self.log_entries[:overflow]

    def log_since(self, seq: int) -> List[Dict[str, Any]]:
        with self.lock:
            if seq <= 0:
                return list(self.log_entries)
            if self.log_entries and seq < self.log_entries[0]["seq"]:
                return list(self.log_entries)
            return [entry for entry in self.log_entries if entry["seq"] > seq]

    def snapshot(self) -> Dict[str, Any]:
        return {
            "id": self.run_id,
            "status": self.status,
            "message": self.message,
            "error": self.error,
            "createdAt": self.created_at.isoformat(),
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "finishedAt": self.finished_at.isoformat() if self.finished_at else None,
            "duration": format_duration(self.started_at, self.finished_at),
            "inputs": self.inputs,
            "outputs": self.outputs,
            "summary": self.summary,
            "logCount": self.log_seq,
            "lastLog": self.last_log,
        }


RUNS: Dict[str, RunState] = {}
RUNS_LOCK = threading.Lock()


def new_id() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def format_duration(start: Optional[datetime], end: Optional[datetime]) -> str:
    if not start or not end:
        return ""
    total_seconds = int((end - start).total_seconds())
    if total_seconds <= 0:
        return "0s"
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts: List[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if not hours:
        parts.append(f"{seconds}s")
    return " ".join(dict.fromkeys(parts))


def list_outputs(output_dir: Path) -> List[Dict[str, Any]]:
    if not output_dir.exists():
        return []
    items: List[Dict[str, Any]] = []
    for path in sorted(output_dir.iterdir()):
        if not path.is_file():
            continue
        items.append({
            "name": path.name,
            "size": path.stat().st_size,
        })
    return items


def create_state() -> RunState:
    run_id = new_id()
    state = RunState(run_id=run_id, created_at=utcnow())
    with RUNS_LOCK:
        RUNS[run_id] = state
    return state


def discard_state(run_id: str) -> None:
    with RUNS_LOCK:
        RUNS.pop(run_id, None)
