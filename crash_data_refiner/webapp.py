from __future__ import annotations

import threading
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, abort, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from .geo import BoundaryFilterReport, load_kmz_polygon, parse_coordinate
from .kmz_report import write_kmz_report
from .map_report import write_map_report
from .pdf_report import generate_pdf_report
from .refiner import CrashDataRefiner, RefinementReport, _normalize_header
from .spreadsheets import read_spreadsheet, read_spreadsheet_headers, write_spreadsheet

BASE_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = Path(__file__).resolve().parent / "web"
OUTPUT_ROOT = BASE_DIR / "outputs" / "web_runs"
PREVIEW_ROOT = OUTPUT_ROOT / "_preview"

MAX_UPLOAD_BYTES = 200 * 1024 * 1024
MAX_LOG_ENTRIES = 1500

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES


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
        now = datetime.utcnow().isoformat()
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
            "duration": _format_duration(self.started_at, self.finished_at),
            "inputs": self.inputs,
            "outputs": self.outputs,
            "summary": self.summary,
            "logCount": self.log_seq,
            "lastLog": self.last_log,
        }


RUNS: Dict[str, RunState] = {}
RUNS_LOCK = threading.Lock()


def _new_id() -> str:
    return uuid.uuid4().hex


def _format_duration(start: Optional[datetime], end: Optional[datetime]) -> str:
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


def _parse_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _list_outputs(output_dir: Path) -> List[Dict[str, Any]]:
    if not output_dir.exists():
        return []
    items = []
    for path in sorted(output_dir.iterdir()):
        if not path.is_file():
            continue
        items.append({
            "name": path.name,
            "size": path.stat().st_size,
        })
    return items


def _score_lat_header(header: str) -> int:
    norm = _normalize_header(header)
    if norm in {"lat", "latitude"}:
        return 100
    if "latitude" in norm:
        return 90
    if norm.startswith("lat_") or norm.endswith("_lat"):
        return 80
    if norm in {"y", "y_coord", "y_coordinate"}:
        return 70
    if "lat" in norm:
        return 50
    return 0


def _score_lon_header(header: str) -> int:
    norm = _normalize_header(header)
    if norm in {"lon", "long", "longitude"}:
        return 100
    if "longitude" in norm:
        return 90
    if norm.startswith(("lon_", "long_")) or norm.endswith(("_lon", "_long")):
        return 80
    if norm in {"x", "x_coord", "x_coordinate"}:
        return 70
    if "lon" in norm or "long" in norm:
        return 50
    return 0


def _guess_lat_lon(headers: List[str]) -> Tuple[Optional[str], Optional[str]]:
    scored_lat = [( _score_lat_header(h), h) for h in headers]
    lat_choice = max(scored_lat, default=(0, None))
    scored_lon = [( _score_lon_header(h), h) for h in headers]
    lon_choice = max(scored_lon, default=(0, None))
    lat = lat_choice[1] if lat_choice[0] > 0 else None
    lon = lon_choice[1] if lon_choice[0] > 0 else None
    return lat, lon


def _refined_output_path(run_dir: Path, input_name: str) -> Path:
    input_file = Path(input_name)
    suffix = input_file.suffix or ".csv"
    return run_dir / f"{input_file.stem}_refined{suffix}"


def _invalid_output_path(output_path: Path) -> Path:
    return output_path.with_name(f"Crashes Without Valid Lat-Long Data{output_path.suffix}")


def _kmz_output_path(output_path: Path) -> Path:
    base_name = output_path.stem
    if base_name.lower().endswith("_refined"):
        base_name = base_name[:-8]
    return output_path.with_name(f"{base_name}_Crash Data.kmz")


def _pdf_output_path(output_path: Path) -> Path:
    base_name = output_path.stem
    if base_name.lower().endswith("_refined"):
        base_name = base_name[:-8]
    return output_path.with_name(f"{base_name}_Crash Data Full Report.pdf")


def _create_state() -> RunState:
    run_id = _new_id()
    state = RunState(run_id=run_id, created_at=datetime.utcnow())
    with RUNS_LOCK:
        RUNS[run_id] = state
    return state


def _get_state(run_id: str) -> RunState:
    with RUNS_LOCK:
        state = RUNS.get(run_id)
    if not state:
        abort(404, description="Run not found.")
    return state


def _discard_state(run_id: str) -> None:
    with RUNS_LOCK:
        RUNS.pop(run_id, None)


def _save_upload(file_obj: Any, *, dest_dir: Path, allowed_exts: Tuple[str, ...], label: str) -> Path:
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


def _build_summary(
    *,
    state: RunState,
    report: RefinementReport,
    boundary_report: BoundaryFilterReport,
    kmz_count: Optional[int],
    map_report_name: str,
) -> Dict[str, Any]:
    metrics = [
        {
            "label": "Rows Scanned",
            "value": str(boundary_report.total_rows),
            "detail": "Raw crash rows processed",
        },
        {
            "label": "Included",
            "value": str(boundary_report.included_rows),
            "detail": "Inside boundary",
        },
        {
            "label": "Excluded",
            "value": str(boundary_report.excluded_rows),
            "detail": "Outside boundary",
        },
        {
            "label": "Invalid",
            "value": str(boundary_report.invalid_rows),
            "detail": "Missing coordinates",
        },
        {
            "label": "Refined Rows",
            "value": str(report.output_rows),
            "detail": "Rows written",
        },
    ]
    if kmz_count is not None:
        metrics.append({
            "label": "KMZ Placemarks",
            "value": str(kmz_count),
            "detail": "Crash map markers",
        })
    if state.started_at and state.finished_at:
        metrics.append({
            "label": "Run Duration",
            "value": _format_duration(state.started_at, state.finished_at),
            "detail": "Pipeline runtime",
        })
    return {
        "metrics": metrics,
        "mapReport": map_report_name,
    }


@app.route("/")
def index() -> Any:
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/api/settings")
def settings() -> Any:
    return jsonify({
        "defaults": {
            "generatePdf": True,
        }
    })


@app.route("/api/preview", methods=["POST"])
def preview_headers() -> Any:
    upload = request.files.get("data_file")
    if upload is None or not upload.filename:
        return jsonify({"error": "Crash data file is required."}), 400
    filename = secure_filename(upload.filename)
    ext = Path(filename).suffix.lower()
    if ext not in {".csv", ".xlsx", ".xlsm"}:
        return jsonify({"error": "Crash data must be CSV or Excel."}), 400

    PREVIEW_ROOT.mkdir(parents=True, exist_ok=True)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext, dir=PREVIEW_ROOT)
    temp_path = Path(temp_file.name)
    temp_file.close()
    try:
        upload.save(temp_path)
        headers = read_spreadsheet_headers(str(temp_path))
        lat_guess, lon_guess = _guess_lat_lon(headers)
        return jsonify({
            "headers": headers,
            "latGuess": lat_guess,
            "lonGuess": lon_guess,
        })
    except Exception as exc:
        return jsonify({"error": f"Unable to read headers: {exc}"}), 400
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass


@app.route("/api/run", methods=["POST"])
def start_run() -> Any:
    data_upload = request.files.get("data_file")
    kmz_upload = request.files.get("boundary_file")
    pdf_upload = request.files.get("pdf_data_file")
    lat_column = request.form.get("lat_column", "").strip()
    lon_column = request.form.get("lon_column", "").strip()
    generate_pdf = _parse_bool(request.form.get("generate_pdf"), True)

    if data_upload is None or not data_upload.filename:
        return jsonify({"error": "Crash data file is required."}), 400
    if kmz_upload is None or not kmz_upload.filename:
        return jsonify({"error": "KMZ boundary file is required."}), 400

    data_ext = Path(data_upload.filename).suffix.lower()
    kmz_ext = Path(kmz_upload.filename).suffix.lower()
    pdf_ext = Path(pdf_upload.filename).suffix.lower() if pdf_upload and pdf_upload.filename else ""

    if data_ext not in {".csv", ".xlsx", ".xlsm"}:
        return jsonify({"error": "Crash data must be CSV or Excel."}), 400
    if kmz_ext != ".kmz":
        return jsonify({"error": "KMZ boundary must be a .kmz file."}), 400
    if pdf_ext and pdf_ext not in {".csv", ".xlsx", ".xlsm"}:
        return jsonify({"error": "PDF data must be CSV or Excel."}), 400

    state = _create_state()
    try:
        run_dir = OUTPUT_ROOT / state.run_id
        input_dir = run_dir / "inputs"
        data_path = _save_upload(
            data_upload,
            dest_dir=input_dir,
            allowed_exts=(".csv", ".xlsx", ".xlsm"),
            label="Crash data file",
        )
        kmz_path = _save_upload(
            kmz_upload,
            dest_dir=input_dir,
            allowed_exts=(".kmz",),
            label="KMZ boundary",
        )
        pdf_path = None
        if pdf_upload and pdf_upload.filename:
            pdf_path = _save_upload(
                pdf_upload,
                dest_dir=input_dir,
                allowed_exts=(".csv", ".xlsx", ".xlsm"),
                label="PDF data file",
            )
    except Exception as exc:
        _discard_state(state.run_id)
        return jsonify({"error": str(exc)}), 400

    if not lat_column or not lon_column:
        try:
            headers = read_spreadsheet_headers(str(data_path))
        except Exception as exc:
            _discard_state(state.run_id)
            return jsonify({"error": f"Unable to read headers: {exc}"}), 400
        lat_guess, lon_guess = _guess_lat_lon(headers)
        if not lat_column and lat_guess:
            lat_column = lat_guess
        if not lon_column and lon_guess:
            lon_column = lon_guess

    if not lat_column or not lon_column:
        _discard_state(state.run_id)
        return jsonify({"error": "Latitude and longitude columns are required."}), 400

    state.inputs = {
        "dataFile": data_path.name,
        "kmzFile": kmz_path.name,
        "latColumn": lat_column,
        "lonColumn": lon_column,
        "generatePdf": generate_pdf,
        "pdfDataFile": pdf_path.name if pdf_path else None,
    }

    thread = threading.Thread(
        target=_run_refinement_job,
        args=(state, data_path, kmz_path, run_dir, lat_column, lon_column, generate_pdf, pdf_path),
        daemon=True,
    )
    thread.start()

    return jsonify({"runId": state.run_id})


def _run_refinement_job(
    state: RunState,
    data_path: Path,
    kmz_path: Path,
    run_dir: Path,
    lat_column: str,
    lon_column: str,
    generate_pdf: bool,
    pdf_path: Optional[Path],
) -> None:
    state.status = "running"
    state.started_at = datetime.utcnow()
    state.output_dir = run_dir
    state.append_log(f"Starting refinement for {data_path.name}")
    try:
        boundary = load_kmz_polygon(str(kmz_path))
        state.append_log("Loaded KMZ boundary polygon.")

        data = read_spreadsheet(str(data_path))
        state.append_log(f"Loaded {len(data.rows)} crash rows.")

        refiner = CrashDataRefiner()
        refined_rows, report, boundary_report, invalid_rows = refiner.refine_rows_with_boundary(
            data.rows,
            boundary=boundary,
            latitude_column=lat_column,
            longitude_column=lon_column,
        )
        state.append_log(
            "Boundary filter complete: "
            f"{boundary_report.included_rows} included, "
            f"{boundary_report.excluded_rows} excluded, "
            f"{boundary_report.invalid_rows} invalid."
        )

        output_path = _refined_output_path(run_dir, data_path.name)
        write_spreadsheet(str(output_path), refined_rows)
        state.append_log(f"Refined output saved: {output_path.name}")

        invalid_path = _invalid_output_path(output_path)
        write_spreadsheet(str(invalid_path), invalid_rows)
        state.append_log(f"Invalid coordinate output saved: {invalid_path.name}")

        lat_norm = _normalize_header(lat_column)
        lon_norm = _normalize_header(lon_column)
        points = []
        for row in refined_rows:
            lat = parse_coordinate(row.get(lat_norm))
            lon = parse_coordinate(row.get(lon_norm))
            if lat is not None and lon is not None:
                points.append((lat, lon))

        map_report_name = "Crash Data Refiner Map Report.html"
        map_report_path = run_dir / map_report_name
        write_map_report(
            str(map_report_path),
            polygon=boundary,
            points=points,
            included_count=boundary_report.included_rows,
            excluded_count=boundary_report.excluded_rows,
            invalid_count=boundary_report.invalid_rows,
        )
        state.append_log("Map report generated.")

        kmz_output_path = _kmz_output_path(output_path)
        kmz_count = write_kmz_report(
            str(kmz_output_path),
            rows=refined_rows,
            latitude_column=lat_column,
            longitude_column=lon_column,
        )
        state.append_log(f"KMZ report generated: {kmz_output_path.name} ({kmz_count} placemarks)")

        if generate_pdf:
            pdf_output_path = _pdf_output_path(output_path)
            if pdf_path:
                pdf_data = read_spreadsheet(str(pdf_path))
                pdf_rows = pdf_data.rows
                state.append_log(f"PDF uses alternate data file: {pdf_path.name}")
            else:
                pdf_rows = refined_rows
            generate_pdf_report(
                str(pdf_output_path),
                rows=pdf_rows,
                latitude_column=lat_column,
                longitude_column=lon_column,
            )
            state.append_log(f"PDF report generated: {pdf_output_path.name}")

        state.status = "success"
        state.message = "Refinement complete."
        state.append_log(state.message)

        state.summary = _build_summary(
            state=state,
            report=report,
            boundary_report=boundary_report,
            kmz_count=kmz_count,
            map_report_name=map_report_name,
        )
    except Exception as exc:
        state.status = "error"
        state.error = str(exc)
        state.message = "Refinement failed."
        state.append_log(f"Error: {exc}", level="error")
    finally:
        state.finished_at = datetime.utcnow()
        if state.output_dir:
            state.outputs = _list_outputs(state.output_dir)


@app.route("/api/run/<run_id>")
def run_status(run_id: str) -> Any:
    state = _get_state(run_id)
    return jsonify(state.snapshot())


@app.route("/api/run/<run_id>/log")
def run_log(run_id: str) -> Any:
    state = _get_state(run_id)
    since = request.args.get("since", "0")
    try:
        seq = int(since)
    except ValueError:
        seq = 0
    return jsonify({
        "entries": state.log_since(seq),
        "lastSeq": state.log_seq,
        "status": state.status,
        "message": state.message,
    })


@app.route("/api/run/<run_id>/download/<path:filename>")
def run_download(run_id: str, filename: str) -> Any:
    state = _get_state(run_id)
    if not state.output_dir:
        abort(404, description="Outputs unavailable.")
    target = (state.output_dir / filename).resolve()
    if not target.exists() or state.output_dir not in target.parents:
        abort(404, description="File not found.")
    return send_from_directory(state.output_dir, target.name, as_attachment=True)


@app.route("/api/run/<run_id>/view/<path:filename>")
def run_view(run_id: str, filename: str) -> Any:
    state = _get_state(run_id)
    if not state.output_dir:
        abort(404, description="Outputs unavailable.")
    target = (state.output_dir / filename).resolve()
    if not target.exists() or state.output_dir not in target.parents:
        abort(404, description="File not found.")
    return send_from_directory(state.output_dir, target.name, as_attachment=False)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Crash Data Refiner web app")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8081)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
