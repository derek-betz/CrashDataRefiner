from __future__ import annotations

import threading
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, abort, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from .coordinate_recovery import CoordinateReviewDecision, CoordinateRecoveryReport
from .geo import BoundaryFilterReport, load_kmz_polygon
from .map_report import write_map_report
from .normalize import guess_lat_lon_columns
from .refiner import RefinementReport
from .run_contract import RunOutputCounts, load_output_counts_from_refined_path
from .services import (
    pdf_output_path,
    refined_output_path,
    relabel_refined_outputs,
    run_pdf_report,
    run_refinement_pipeline,
    summary_output_path,
    kmz_output_path,
)
from .spreadsheets import read_spreadsheet_headers, read_spreadsheet_preview_points
from .web_files import copy_input_file as _copy_input_file, save_upload as _save_upload
from .web_review import (
    load_review_queue_for_state as _load_review_queue_for_state,
    load_review_wizard_for_state as _load_review_wizard_for_state,
    parse_review_decisions_payload as _parse_review_decisions_payload,
)
from .web_state import (
    RUNS,
    RUNS_LOCK,
    RunState,
    discard_state as _discard_state,
    format_duration as _format_duration,
    list_outputs as _list_outputs,
    new_id as _new_id,
    utcnow as _utcnow,
)
from .web_summary import build_web_run_summary, refresh_web_run_summary_for_relabel

BASE_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = Path(__file__).resolve().parent / "web"
OUTPUT_ROOT = BASE_DIR / "outputs" / "web_runs"
PREVIEW_ROOT = OUTPUT_ROOT / "_preview"

MAX_UPLOAD_BYTES = 200 * 1024 * 1024

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
def _create_state() -> RunState:
    state = RunState(run_id=_new_id(), created_at=_utcnow())
    with RUNS_LOCK:
        RUNS[state.run_id] = state
    return state


def _get_state(run_id: str) -> RunState:
    with RUNS_LOCK:
        state = RUNS.get(run_id)
    if not state:
        abort(404, description="Run not found.")
    return state


def _snapshot_state(state: RunState) -> Dict[str, Any]:
    snapshot = state.snapshot()
    summary = dict(snapshot.get("summary") or {})
    if "outputCounts" not in summary and state.output_dir:
        data_name = str((state.inputs or {}).get("dataFile") or "").strip()
        if data_name:
            refined_path = refined_output_path(state.output_dir, data_name)
            if refined_path.exists():
                counts = load_output_counts_from_refined_path(refined_path)
                summary["outputCounts"] = {
                    "refinedRows": counts.refined_rows,
                    "invalidRows": counts.invalid_rows,
                    "coordinateReviewRows": counts.coordinate_review_rows,
                    "rejectedReviewRows": counts.rejected_review_rows,
                }
                snapshot["summary"] = summary
    return snapshot


def _build_summary(
    *,
    state: RunState,
    report: RefinementReport,
    boundary_report: BoundaryFilterReport,
    recovery_report: CoordinateRecoveryReport,
    coordinate_review_count: int,
    rejected_review_count: int,
    kmz_count: Optional[int],
    requested_label_order: str,
    resolved_label_order: str,
) -> Dict[str, Any]:
    return build_web_run_summary(
        run_duration=_format_duration(state.started_at, state.finished_at),
        report=report,
        boundary_report=boundary_report,
        recovery_report=recovery_report,
        output_counts=RunOutputCounts(
            refined_rows=report.output_rows,
            invalid_rows=boundary_report.invalid_rows,
            coordinate_review_rows=coordinate_review_count,
            rejected_review_rows=rejected_review_count,
        ),
        requested_label_order=requested_label_order,
        resolved_label_order=resolved_label_order,
        kmz_count=kmz_count,
    )


def _update_summary_for_relabel(
    state: RunState,
    *,
    requested_label_order: str,
    resolved_label_order: str,
    kmz_count: int,
) -> None:
    data_name = str((state.inputs or {}).get("dataFile") or "").strip()
    if not state.output_dir or not data_name:
        raise ValueError("This run is missing the refined output reference.")
    refined_path = refined_output_path(state.output_dir, data_name)
    state.summary = refresh_web_run_summary_for_relabel(
        state.summary,
        refined_path=refined_path,
        requested_label_order=requested_label_order,
        resolved_label_order=resolved_label_order,
        run_duration=_format_duration(state.started_at, state.finished_at),
        kmz_count=kmz_count,
    )


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
    if kmz_upload is None or not kmz_upload.filename:
        return jsonify({"error": "KMZ boundary file is required."}), 400

    data_ext = Path(data_upload.filename).suffix.lower() if data_upload and data_upload.filename else ""
    kmz_ext = Path(kmz_upload.filename).suffix.lower()
    if data_upload and data_upload.filename and data_ext not in {".csv", ".xlsx", ".xlsm"}:
        return jsonify({"error": "Crash data must be CSV or Excel."}), 400
    if kmz_ext != ".kmz":
        return jsonify({"error": "KMZ boundary must be a .kmz file."}), 400

    PREVIEW_ROOT.mkdir(parents=True, exist_ok=True)
    data_path: Optional[Path] = None
    if data_upload and data_upload.filename:
        data_file = tempfile.NamedTemporaryFile(delete=False, suffix=data_ext, dir=PREVIEW_ROOT)
        data_path = Path(data_file.name)
        data_file.close()
    kmz_file = tempfile.NamedTemporaryFile(delete=False, suffix=kmz_ext, dir=PREVIEW_ROOT)
    kmz_path = Path(kmz_file.name)
    kmz_file.close()

    lat_guess = None
    lon_guess = None
    try:
        if data_upload and data_upload.filename and data_path is not None:
            data_upload.save(data_path)
        kmz_upload.save(kmz_path)
        boundary = load_kmz_polygon(str(kmz_path))
        points: List[Tuple[float, float]] = []
        included = 0
        excluded = 0
        invalid = 0
        if data_path is not None:
            if not lat_column or not lon_column:
                headers = read_spreadsheet_headers(str(data_path))
                lat_guess, lon_guess = guess_lat_lon_columns(headers)
                if not lat_column and lat_guess:
                    lat_column = lat_guess
                if not lon_column and lon_guess:
                    lon_column = lon_guess
            if lat_column and lon_column:
                points, included, excluded, invalid = read_spreadsheet_preview_points(
                    str(data_path),
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
        if data_path is not None:
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
    label_order = request.form.get("label_order", "auto").strip() or "auto"

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

    if label_order and label_order not in {"auto", "west_to_east", "south_to_north"}:
        return jsonify({"error": "Invalid label order."}), 400
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
    label_order = label_order or str(source_inputs.get("labelOrder") or "auto").strip() or "auto"

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
            coordinate_review_count=len(result.coordinate_review_rows),
            rejected_review_count=len(result.rejected_review_rows),
            kmz_count=result.kmz_count,
            requested_label_order=result.requested_label_order,
            resolved_label_order=result.resolved_label_order,
        )
        state.inputs["labelOrder"] = result.requested_label_order
        state.inputs["resolvedLabelOrder"] = result.resolved_label_order
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


def _run_relabel_job(
    state: RunState,
    *,
    refined_path: Path,
    kmz_path: Path,
    lat_column: str,
    lon_column: str,
    label_order: str,
    stale_output_paths: List[Path],
) -> None:
    state.status = "running"
    state.error = None
    state.started_at = _utcnow()
    state.message = "Regenerating KMZ labels."
    state.append_log(
        f"Regenerating KMZ labels using {(label_order or 'auto').replace('_', ' ')} ordering."
    )
    try:
        result = relabel_refined_outputs(
            refined_path=refined_path,
            kmz_path=kmz_path,
            lat_column=lat_column,
            lon_column=lon_column,
            label_order=label_order,
            remove_output_paths=stale_output_paths,
        )
        state.status = "success"
        state.message = "KMZ labels regenerated."
        state.inputs["labelOrder"] = result.requested_label_order
        state.inputs["resolvedLabelOrder"] = result.resolved_label_order
        state.append_log(
            f"Refined output relabeled {result.resolved_label_order.replace('_', ' ')}."
        )
        state.append_log(f"KMZ report regenerated: {result.kmz_path.name} ({result.kmz_count} placemarks)")
        for removed_path in result.removed_outputs:
            state.append_log(
                f"Removed stale output after relabeling: {removed_path.name}"
            )
        _update_summary_for_relabel(
            state,
            requested_label_order=result.requested_label_order,
            resolved_label_order=result.resolved_label_order,
            kmz_count=result.kmz_count,
        )
        state.append_log(state.message)
    except Exception as exc:
        state.status = "error"
        state.error = str(exc)
        state.message = "KMZ relabel failed."
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
    return jsonify(_snapshot_state(state))


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


@app.route("/api/run/<run_id>/relabel", methods=["POST"])
def relabel_run_outputs(run_id: str) -> Any:
    state = _get_state(run_id)
    if state.status == "running":
        return jsonify({"error": "This run is still in progress."}), 409
    if not state.output_dir:
        return jsonify({"error": "Outputs are unavailable for this run."}), 400

    inputs = dict(state.inputs or {})
    data_name = str(inputs.get("dataFile") or "").strip()
    lat_column = str(inputs.get("latColumn") or "").strip()
    lon_column = str(inputs.get("lonColumn") or "").strip()
    label_order = request.form.get("label_order", "").strip() or str(inputs.get("labelOrder") or "auto").strip() or "auto"
    if label_order not in {"auto", "west_to_east", "south_to_north"}:
        return jsonify({"error": "Invalid label order."}), 400
    if not data_name or not lat_column or not lon_column:
        return jsonify({"error": "This run is missing the data file or coordinate columns."}), 400

    refined_path = refined_output_path(state.output_dir, data_name)
    kmz_path = kmz_output_path(refined_path)
    if not refined_path.exists():
        return jsonify({"error": "Refined output for this run was not found."}), 404

    state.inputs["runKind"] = "relabel"
    stale_output_paths = [
        pdf_output_path(refined_path),
        summary_output_path(refined_path),
    ]
    thread = threading.Thread(
        target=_run_relabel_job,
        kwargs={
            "state": state,
            "refined_path": refined_path,
            "kmz_path": kmz_path,
            "lat_column": lat_column,
            "lon_column": lon_column,
            "label_order": label_order,
            "stale_output_paths": stale_output_paths,
        },
        daemon=True,
    )
    thread.start()
    return jsonify({"runId": state.run_id})


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
