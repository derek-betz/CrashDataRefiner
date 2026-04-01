"""File-input helpers for the Flask web surface."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Tuple

from werkzeug.utils import secure_filename


def save_upload(
    file_obj: Any,
    *,
    dest_dir: Path,
    allowed_exts: Tuple[str, ...],
    label: str,
) -> Path:
    if file_obj is None or not file_obj.filename:
        raise ValueError(f"{label} is required.")
    filename = secure_filename(file_obj.filename)
    ext = Path(filename).suffix.lower()
    if ext not in allowed_exts:
        raise ValueError(f"{label} must be one of: {', '.join(allowed_exts)}.")
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / filename
    file_obj.save(path)
    return path


def copy_input_file(source: Path, *, dest_dir: Path, label: str) -> Path:
    if not source.exists():
        raise ValueError(f"{label} was not found.")
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / source.name
    shutil.copy2(source, target)
    return target
