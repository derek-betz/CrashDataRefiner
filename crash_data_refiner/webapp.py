from __future__ import annotations

import json
import shutil
import threading
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, abort, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from .coordinate_recovery import (
    CoordinateReviewDecision,
    CoordinateRecoveryReport,
    build_coordinate_review_queue,
    build_coordinate_review_wizard_steps,
)
from .geo import BoundaryFilterReport, load_kmz_polygon, parse_coordinate
from .map_report import write_map_report
from .normalize import guess_lat_lon_columns, normalize_header
from .refiner import CrashDataRefiner, RefinementReport
from .services import (
    coordinate_review_output_path,
    pdf_output_path,
    refined_output_path,
    run_pdf_report,
    run_refinement_pipeline,
)
from .spreadsheets import read_spreadsheet, read_spreadsheet_headers

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
        now = _utcnow().isoformat()
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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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


def _build_preview_points(
    rows: List[Dict[str, Any]],
    *,
    lat_column: str,
    lon_column: str,
    boundary: Any,
) -> Tuple[List[Tuple[float, float]], int, int, int]:
    refiner = CrashDataRefiner()
    included_rows, _excluded_rows, _invalid_rows, report = refiner.filter_rows_by_boundary(
        rows,
        boundary=boundary,
        latitude_column=lat_column,
        longitude_column=lon_column,
    )
    lat_key = normalize_header(lat_column)
    lon_key = normalize_header(lon_column)
    points: List[Tuple[float, float]] = []
    for row in included_rows:
        lat = parse_coordinate(row.get(lat_key))
        lon = parse_coordinate(row.get(lon_key))
        if lat is not None and lon is not None:
            points.append((lat, lon))
    return points, report.included_rows, report.excluded_rows, report.invalid_rows


def _create_state() -> RunState:
    run_id = _new_id()
    state = RunState(run_id=run_id, created_at=_utcnow())
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


def _copy_input_file(source: Path, *, dest_dir: Path, label: str) -> Path:
    if not source.exists():
        raise ValueError(f"{label} was not found.")
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / source.name
    shutil.copy2(source, target)
    return target


def _resolve_coordinate_review_path(state: RunState) -> Optional[Path]:
    if not state.output_dir:
        return None
    data_name = str((state.inputs or {}).get("dataFile") or "").strip()
    if not data_name:
        return None
    output_path = refined_output_path(state.output_dir, data_name)
    review_path = coordinate_review_output_path(output_path)
    if review_path.exists():
        return review_path
    return None


def _load_review_queue_for_state(state: RunState) -> List[Dict[str, Any]]:
    review_path = _resolve_coordinate_review_path(state)
    if review_path is None:
        return []
    data = read_spreadsheet(str(review_path))
    return build_coordinate_review_queue(data.rows)


def _polygon_to_leaflet(polygon: Any) -> List[List[List[float]]]:
    outer = [[lat, lon] for lon, lat in polygon.outer]
    holes = [[[lat, lon] for lon, lat in ring] for ring in polygon.holes]
    if holes:
        return [outer, *holes]
    return [outer]


def _load_review_map_data_for_state(state: RunState) -> Optional[Dict[str, Any]]:
    if not state.output_dir:
        return None

    inputs = dict(state.inputs or {})
    data_name = str(inputs.get("dataFile") or "").strip()
    kmz_name = str(inputs.get("kmzFile") or "").strip()
    lat_column = str(inputs.get("latColumn") or "").strip()
    lon_column = str(inputs.get("lonColumn") or "").strip()
    if not data_name or not kmz_name or not lat_column or not lon_column:
        return None

    input_dir = state.output_dir / "inputs"
    kmz_path = input_dir / kmz_name
    refined_path = refined_output_path(state.output_dir, data_name)
    if not kmz_path.exists() or not refined_path.exists():
        return None

    boundary = load_kmz_polygon(str(kmz_path))
    refined_data = read_spreadsheet(str(refined_path))
    lat_key = normalize_header(lat_column)
    lon_key = normalize_header(lon_column)
    points: List[List[float]] = []
    for row in refined_data.rows:
        lat = parse_coordinate(row.get(lat_key))
        lon = parse_coordinate(row.get(lon_key))
        if lat is None or lon is None:
            continue
        points.append([lat, lon])

    return {
        "polygon": _polygon_to_leaflet(boundary),
        "points": points,
        "pointCount": len(points),
    }


def _load_review_wizard_for_state(state: RunState) -> Dict[str, Any]:
    review_path = _resolve_coordinate_review_path(state)
    if review_path is None:
        return {
            "primarySteps": [],
            "secondarySteps": [],
            "mapData": None,
        }

    data = read_spreadsheet(str(review_path))
    steps = build_coordinate_review_wizard_steps(data.rows)
    primary_steps = [
        step for step in steps
        if str(step.get("reviewBucket") or "primary") != "secondary"
    ]
    secondary_steps = [
        step for step in steps
        if str(step.get("reviewBucket") or "primary") == "secondary"
    ]
    return {
        "primarySteps": primary_steps,
        "secondarySteps": secondary_steps,
        "mapData": _load_review_map_data_for_state(state),
    }


def _parse_review_decisions_payload(text: str) -> Dict[str, CoordinateReviewDecision]:
    if not text.strip():
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Review decisions must be valid JSON.") from exc

    if not isinstance(payload, list):
        raise ValueError("Review decisions must be a JSON array.")

    decisions: Dict[str, CoordinateReviewDecision] = {}
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Review decision #{index} must be an object.")
        group_key = str(item.get("rowKey") or item.get("groupKey") or "").strip()
        action = str(item.get("action") or "apply").strip().lower()
        latitude = parse_coordinate(item.get("latitude"))
        longitude = parse_coordinate(item.get("longitude"))
        note = str(item.get("note") or "").strip()
        if not group_key:
            raise ValueError(
                f"Review decision #{index} must include rowKey or groupKey."
            )
        if action not in {"apply", "reject"}:
            raise ValueError(f"Review decision #{index} action must be 'apply' or 'reject'.")
        if action == "apply" and (latitude is None or longitude is None):
            raise ValueError(
                f"Review decision #{index} must include latitude and longitude for applied placements."
            )
        existing = decisions.get(group_key)
        if existing and (
            existing.action != action
            or (
                action == "apply"
                and (
                    existing.latitude is None
                    or existing.longitude is None
                    or latitude is None
                    or longitude is None
                    or abs(existing.latitude - latitude) > 1e-6
                    or abs(existing.longitude - longitude) > 1e-6
                )
            )
        ):
            raise ValueError(f"Review group '{group_key}' contains conflicting browser decisions.")
        decisions[group_key] = CoordinateReviewDecision(
            group_key=group_key,
            latitude=latitude,
            longitude=longitude,
            action=action,
            note=note or (
                "Rejected in browser review wizard."
                if action == "reject"
                else "Applied from browser review wizard."
            ),
        )
    return decisions


def _build_summary(
    *,
    state: RunState,
    report: RefinementReport,
    boundary_report: BoundaryFilterReport,
    recovery_report: CoordinateRecoveryReport,
    kmz_count: Optional[int],
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
    if recovery_report.missing_rows:
        auto_recovered = max(recovery_report.recovered_rows - recovery_report.approved_rows, 0)
        metrics.extend(
            [
                {
                    "label": "Recovered Coords",
                    "value": str(recovery_report.recovered_rows),
                    "detail": "Auto-filled plus approved review decisions",
                },
                {
                    "label": "Review Needed",
                    "value": str(recovery_report.review_rows),
                    "detail": "Rows written to coordinate review output",
                },
                {
                    "label": "Rejected Review",
                    "value": str(recovery_report.rejected_rows),
                    "detail": "Rows kept out of the refined data by explicit review rejection",
                },
                {
                    "label": "Primary Review",
                    "value": str(recovery_report.primary_review_rows),
                    "detail": "Likely in-project review rows",
                },
                {
                    "label": "Secondary Bucket",
                    "value": str(recovery_report.secondary_review_rows),
                    "detail": "Lower-likelihood rows kept out of the main queue",
                },
            ]
        )
        if auto_recovered:
            metrics.append(
                {
                    "label": "Auto Recovered",
                    "value": str(auto_recovered),
                    "detail": "Rows filled without manual review",
                }
            )
        if recovery_report.approved_rows:
            metrics.append(
                {
                    "label": "Review Applied",
                    "value": str(recovery_report.approved_rows),
                    "detail": "Rows filled from approved workbook decisions",
                }
            )
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
    }


@app.route("/")
def index() -> Any:
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/api/settings")
def settings() -> Any:
    return jsonify({
        "defaults": {
            "generatePdf": False,
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
        lat_guess, lon_guess = guess_lat_lon_columns(headers)
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


@app.route("/api/preview-map", methods=["POST"])
def preview_map() -> Any:
    data_upload = request.files.get("data_file")
    kmz_upload = request.files.get("boundary_file")
    lat_column = request.form.get("lat_column", "").strip()
    lon_column = request.form.get("lon_column", "").strip()

    if data_upload is None or not data_upload.filename:
        return jsonify({"error": "Crash data file is required."}), 400
    if kmz_upload is None or not kmz_upload.filename:
        return jsonify({"error": "KMZ boundary file is required."}), 400

    data_ext = Path(data_upload.filename).suffix.lower()
    kmz_ext = Path(kmz_upload.filename).suffix.lower()
    if data_ext not in {".csv", ".xlsx", ".xlsm"}:
        return jsonify({"error": "Crash data must be CSV or Excel."}), 400
    if kmz_ext != ".kmz":
        return jsonify({"error": "KMZ boundary must be a .kmz file."}), 400

    PREVIEW_ROOT.mkdir(parents=True, exist_ok=True)
    data_file = tempfile.NamedTemporaryFile(delete=False, suffix=data_ext, dir=PREVIEW_ROOT)
    data_path = Path(data_file.name)
    data_file.close()
    kmz_file = tempfile.NamedTemporaryFile(delete=False, suffix=kmz_ext, dir=PREVIEW_ROOT)
    kmz_path = Path(kmz_file.name)
    kmz_file.close()

    lat_guess = None
    lon_guess = None
    try:
        data_upload.save(data_path)
        kmz_upload.save(kmz_path)
        data = read_spreadsheet(str(data_path))
        if not lat_column or not lon_column:
            lat_guess, lon_guess = guess_lat_lon_columns(data.headers)
            if not lat_column and lat_guess:
                lat_column = lat_guess
            if not lon_column and lon_guess:
                lon_column = lon_guess
        if not lat_column or not lon_column:
            return jsonify({"error": "Latitude and longitude columns are required."}), 400

        boundary = load_kmz_polygon(str(kmz_path))
        points, included, excluded, invalid = _build_preview_points(
            data.rows,
            lat_column=lat_column,
            lon_column=lon_column,
            boundary=boundary,
        )
        preview_name = f"preview_map_{_new_id()}.html"
        preview_path = PREVIEW_ROOT / preview_name
        write_map_report(
            str(preview_path),
            polygon=boundary,
            points=points,
            included_count=included,
            excluded_count=excluded,
            invalid_count=invalid,
        )
    except Exception as exc:
        return jsonify({"error": f"Unable to build preview map: {exc}"}), 400
    finally:
        try:
            data_path.unlink(missing_ok=True)
        except Exception:
            pass
        try:
            kmz_path.unlink(missing_ok=True)
        except Exception:
            pass

    payload: Dict[str, Any] = {"previewUrl": f"/api/preview-map/{preview_name}"}
    if lat_guess:
        payload["latGuess"] = lat_guess
    if lon_guess:
        payload["lonGuess"] = lon_guess
    return jsonify(payload)


@app.route("/api/preview-map/<path:filename>")
def preview_map_view(filename: str) -> Any:
    target = (PREVIEW_ROOT / filename).resolve()
    if not target.exists() or PREVIEW_ROOT not in target.parents:
        abort(404, description="File not found.")
    return send_from_directory(PREVIEW_ROOT, target.name, as_attachment=False)


@app.route("/api/run", methods=["POST"])
def start_run() -> Any:
    data_upload = request.files.get("data_file")
    kmz_upload = request.files.get("boundary_file")
    lat_column = request.form.get("lat_column", "").strip()
    lon_column = request.form.get("lon_column", "").strip()
    label_order = request.form.get("label_order", "west_to_east").strip() or "west_to_east"

    if data_upload is None or not data_upload.filename:
        return jsonify({"error": "Crash data file is required."}), 400
    if kmz_upload is None or not kmz_upload.filename:
        return jsonify({"error": "KMZ boundary file is required."}), 400

    data_ext = Path(data_upload.filename).suffix.lower()
    kmz_ext = Path(kmz_upload.filename).suffix.lower()
    if data_ext not in {".csv", ".xlsx", ".xlsm"}:
        return jsonify({"error": "Crash data must be CSV or Excel."}), 400
    if kmz_ext != ".kmz":
        return jsonify({"error": "KMZ boundary must be a .kmz file."}), 400

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
    except Exception as exc:
        _discard_state(state.run_id)
        return jsonify({"error": str(exc)}), 400

    if not lat_column or not lon_column:
        try:
            headers = read_spreadsheet_headers(str(data_path))
        except Exception as exc:
            _discard_state(state.run_id)
            return jsonify({"error": f"Unable to read headers: {exc}"}), 400
        lat_guess, lon_guess = guess_lat_lon_columns(headers)
        if not lat_column and lat_guess:
            lat_column = lat_guess
        if not lon_column and lon_guess:
            lon_column = lon_guess

    if not lat_column or not lon_column:
        _discard_state(state.run_id)
        return jsonify({"error": "Latitude and longitude columns are required."}), 400

    state.inputs = {
        "runKind": "refine",
        "dataFile": data_path.name,
        "kmzFile": kmz_path.name,
        "latColumn": lat_column,
        "lonColumn": lon_column,
        "labelOrder": label_order,
    }

    thread = threading.Thread(
        target=_run_refinement_job,
        args=(
            state,
            data_path,
            kmz_path,
            run_dir,
            lat_column,
            lon_column,
            label_order,
        ),
        daemon=True,
    )
    thread.start()

    return jsonify({"runId": state.run_id})


@app.route("/api/apply-review", methods=["POST"])
def apply_coordinate_review() -> Any:
    source_run_id = request.form.get("source_run_id", "").strip()
    review_upload = request.files.get("coordinate_review_file")
    review_decisions_text = request.form.get("review_decisions", "").strip()
    lat_column = request.form.get("lat_column", "").strip()
    lon_column = request.form.get("lon_column", "").strip()
    label_order = request.form.get("label_order", "").strip()

    if not source_run_id:
        return jsonify({"error": "A previous run is required."}), 400
    if (review_upload is None or not review_upload.filename) and not review_decisions_text:
        return jsonify({"error": "Coordinate review file or browser review decisions are required."}), 400

    with RUNS_LOCK:
        source_state = RUNS.get(source_run_id)
    if not source_state or not source_state.output_dir:
        return jsonify({"error": "Previous run not found."}), 404

    source_inputs = dict(source_state.inputs or {})
    data_name = str(source_inputs.get("dataFile") or "").strip()
    kmz_name = str(source_inputs.get("kmzFile") or "").strip()
    lat_column = lat_column or str(source_inputs.get("latColumn") or "").strip()
    lon_column = lon_column or str(source_inputs.get("lonColumn") or "").strip()
    label_order = label_order or str(source_inputs.get("labelOrder") or "west_to_east").strip() or "west_to_east"

    if not data_name or not kmz_name:
        return jsonify({"error": "Previous run is missing the original crash data or KMZ input."}), 400
    if not lat_column or not lon_column:
        return jsonify({"error": "Latitude and longitude columns are required."}), 400

    review_decisions: Dict[str, CoordinateReviewDecision] = {}
    if review_decisions_text:
        try:
            review_decisions = _parse_review_decisions_payload(review_decisions_text)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    state = _create_state()
    try:
        run_dir = OUTPUT_ROOT / state.run_id
        input_dir = run_dir / "inputs"
        source_input_dir = source_state.output_dir / "inputs"
        data_path = _copy_input_file(
            source_input_dir / data_name,
            dest_dir=input_dir,
            label="Crash data file",
        )
        kmz_path = _copy_input_file(
            source_input_dir / kmz_name,
            dest_dir=input_dir,
            label="KMZ boundary",
        )
        review_path = None
        if review_upload is not None and review_upload.filename:
            review_path = _save_upload(
                review_upload,
                dest_dir=input_dir,
                allowed_exts=(".csv", ".xlsx", ".xlsm"),
                label="Coordinate review file",
            )
    except Exception as exc:
        _discard_state(state.run_id)
        return jsonify({"error": str(exc)}), 400

    state.inputs = {
        "runKind": "review",
        "sourceRun": source_run_id,
        "dataFile": data_path.name,
        "kmzFile": kmz_path.name,
        "latColumn": lat_column,
        "lonColumn": lon_column,
        "labelOrder": label_order,
    }
    if review_path is not None:
        state.inputs["coordinateReviewFile"] = review_path.name
    if review_decisions:
        state.inputs["browserReviewDecisionCount"] = len(review_decisions)

    thread = threading.Thread(
        target=_run_refinement_job,
        args=(
            state,
            data_path,
            kmz_path,
            run_dir,
            lat_column,
            lon_column,
            label_order,
            review_path,
            review_decisions,
        ),
        daemon=True,
    )
    thread.start()

    return jsonify({"runId": state.run_id})


@app.route("/api/report", methods=["POST"])
def start_report() -> Any:
    data_upload = request.files.get("data_file")
    pdf_upload = request.files.get("pdf_data_file")
    source_run_id = request.form.get("source_run_id", "").strip() or None
    lat_column = request.form.get("lat_column", "").strip()
    lon_column = request.form.get("lon_column", "").strip()

    source_state = None
    if source_run_id:
        with RUNS_LOCK:
            source_state = RUNS.get(source_run_id)
        if not source_state or not source_state.output_dir:
            return jsonify({"error": "Previous run not found."}), 404

    state = _create_state()
    try:
        output_dir = OUTPUT_ROOT / state.run_id
        if source_state and source_state.output_dir:
            output_dir = source_state.output_dir
            state.summary = dict(source_state.summary or {})
            state.inputs = dict(source_state.inputs or {})
            state.inputs["sourceRun"] = source_run_id
            state.inputs["runKind"] = "report"

        input_dir = output_dir / "inputs"
        pdf_path = None
        data_path = None
        source_name = ""

        if pdf_upload and pdf_upload.filename:
            pdf_path = _save_upload(
                pdf_upload,
                dest_dir=input_dir,
                allowed_exts=(".csv", ".xlsx", ".xlsm"),
                label="PDF data file",
            )
            source_name = pdf_path.name
            state.inputs["pdfDataFile"] = source_name
        elif source_state:
            data_name = (source_state.inputs or {}).get("dataFile")
            if not data_name:
                raise ValueError("Previous run is missing the crash data file reference.")
            source_name = data_name
            data_path = refined_output_path(output_dir, data_name)
            if not data_path.exists():
                raise ValueError("Refined output from the previous run was not found.")
        else:
            if data_upload is None or not data_upload.filename:
                raise ValueError("Crash data file is required.")
            data_ext = Path(data_upload.filename).suffix.lower()
            if data_ext not in {".csv", ".xlsx", ".xlsm"}:
                raise ValueError("Crash data must be CSV or Excel.")
            data_path = _save_upload(
                data_upload,
                dest_dir=input_dir,
                allowed_exts=(".csv", ".xlsx", ".xlsm"),
                label="Crash data file",
            )
            source_name = data_path.name
            state.inputs["dataFile"] = source_name

        state.inputs["runKind"] = "report"
        state.output_dir = output_dir
        source_path = pdf_path or data_path
        if source_path is None:
            raise ValueError("Report data source not available.")

        if not lat_column or not lon_column:
            headers = read_spreadsheet_headers(str(source_path))
            lat_guess, lon_guess = guess_lat_lon_columns(headers)
            if not lat_column and lat_guess:
                lat_column = lat_guess
            if not lon_column and lon_guess:
                lon_column = lon_guess

        if not lat_column or not lon_column:
            raise ValueError("Latitude and longitude columns are required.")

        state.inputs["latColumn"] = lat_column
        state.inputs["lonColumn"] = lon_column

        output_path = refined_output_path(output_dir, source_name)
        pdf_out_path = pdf_output_path(output_path)
    except Exception as exc:
        _discard_state(state.run_id)
        return jsonify({"error": str(exc)}), 400

    thread = threading.Thread(
        target=_run_report_job,
        args=(state, source_path, pdf_out_path, lat_column, lon_column),
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
    label_order: str,
    coordinate_review_path: Optional[Path] = None,
    review_decisions: Optional[Dict[str, CoordinateReviewDecision]] = None,
) -> None:
    state.status = "running"
    state.started_at = _utcnow()
    state.output_dir = run_dir
    if coordinate_review_path is not None:
        state.append_log(
            f"Applying reviewed coordinate decisions from {coordinate_review_path.name} to {data_path.name}"
        )
    elif review_decisions:
        state.append_log(
            f"Applying {len(review_decisions)} browser review decision(s) to {data_path.name}"
        )
    else:
        state.append_log(f"Starting refinement for {data_path.name}")
    try:
        result = run_refinement_pipeline(
            data_path=data_path,
            kmz_path=kmz_path,
            run_dir=run_dir,
            lat_column=lat_column,
            lon_column=lon_column,
            label_order=label_order,
            coordinate_review_path=coordinate_review_path,
            review_decisions=review_decisions,
        )
        for msg in result.log:
            state.append_log(msg)

        state.status = "success"
        state.message = (
            "Coordinate decisions applied."
            if coordinate_review_path is not None or review_decisions
            else "Refinement complete."
        )
        state.append_log(state.message)

        state.summary = _build_summary(
            state=state,
            report=result.refinement_report,
            boundary_report=result.boundary_report,
            recovery_report=result.recovery_report,
            kmz_count=result.kmz_count,
        )
    except Exception as exc:
        state.status = "error"
        state.error = str(exc)
        state.message = (
            "Applying coordinate decisions failed."
            if coordinate_review_path is not None or review_decisions
            else "Refinement failed."
        )
        state.append_log(f"Error: {exc}", level="error")
    finally:
        state.finished_at = _utcnow()
        if state.output_dir:
            state.outputs = _list_outputs(state.output_dir)


def _run_report_job(
    state: RunState,
    source_path: Path,
    pdf_out_path: Path,
    lat_column: str,
    lon_column: str,
) -> None:
    state.status = "running"
    state.started_at = _utcnow()
    state.message = "Preparing PDF report."
    state.append_log(f"Generating PDF report from {source_path.name}")

    def _report_progress(current: int, total: int) -> None:
        if total <= 0:
            state.message = "Preparing PDF report."
            return
        if current <= 0:
            state.message = f"Preparing PDF report ({total} page(s) queued)."
            return
        state.message = f"Generating PDF report ({current} of {total} pages rendered)."
        if total <= 5 or current == 1 or current == total or current % 10 == 0:
            state.append_log(f"Rendered PDF page {current} of {total}.")

    try:
        run_pdf_report(
            source_path=source_path,
            output_path=pdf_out_path,
            lat_column=lat_column,
            lon_column=lon_column,
            progress_callback=_report_progress,
        )
        state.status = "success"
        state.message = "PDF report generated."
        state.append_log(state.message)
    except Exception as exc:
        state.status = "error"
        state.error = str(exc)
        state.message = "PDF report failed."
        state.append_log(f"Error: {exc}", level="error")
    finally:
        state.finished_at = _utcnow()
        if state.output_dir:
            state.outputs = _list_outputs(state.output_dir)


@app.route("/api/run/<run_id>")
def run_status(run_id: str) -> Any:
    state = _get_state(run_id)
    return jsonify(state.snapshot())


@app.route("/api/run/<run_id>/review-queue")
def run_review_queue(run_id: str) -> Any:
    state = _get_state(run_id)
    groups = _load_review_queue_for_state(state)
    primary_groups = sum(1 for group in groups if str(group.get("reviewBucket") or "primary") != "secondary")
    secondary_groups = len(groups) - primary_groups
    return jsonify(
        {
            "runId": run_id,
            "groupCount": len(groups),
            "primaryGroupCount": primary_groups,
            "secondaryGroupCount": secondary_groups,
            "groups": groups,
        }
    )


@app.route("/api/run/<run_id>/review-wizard")
def run_review_wizard(run_id: str) -> Any:
    state = _get_state(run_id)
    payload = _load_review_wizard_for_state(state)
    primary_steps = payload["primarySteps"]
    secondary_steps = payload["secondarySteps"]
    return jsonify(
        {
            "runId": run_id,
            "primaryStepCount": len(primary_steps),
            "secondaryStepCount": len(secondary_steps),
            "primarySteps": primary_steps,
            "secondarySteps": secondary_steps,
            "mapData": payload["mapData"],
        }
    )


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
