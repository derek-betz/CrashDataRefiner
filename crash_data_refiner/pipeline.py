"""Shared refinement and relabel orchestration helpers."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from .coordinate_recovery import (
    CoordinateReviewDecision,
    CoordinateRecoveryReport,
    load_coordinate_review_decisions,
    recover_missing_coordinates,
)
from .geo import BoundaryFilterReport, load_kmz_polygon
from .kmz_report import write_kmz_report
from .labeling import order_and_number_rows, resolve_label_order
from .output_paths import (
    coordinate_review_output_path,
    invalid_output_path,
    kmz_output_path,
    refined_output_path,
    rejected_review_output_path,
)
from .normalize import guess_lat_lon_columns
from .refiner import CrashDataRefiner, RefinementReport
from .spreadsheets import read_spreadsheet, read_spreadsheet_headers, write_spreadsheet


@dataclass
class RefinementResult:
    """Collects all outputs produced by :func:`run_refinement_pipeline`."""

    refined_rows: List[Dict[str, Any]]
    invalid_rows: List[Dict[str, Any]]
    rejected_review_rows: List[Dict[str, Any]]
    coordinate_review_rows: List[Dict[str, Any]]
    refinement_report: RefinementReport
    boundary_report: BoundaryFilterReport
    recovery_report: CoordinateRecoveryReport
    output_path: Path
    invalid_path: Path
    rejected_review_path: Path
    coordinate_review_path: Path
    kmz_path: Path
    kmz_count: int
    requested_label_order: str
    resolved_label_order: str
    log: List[str] = field(default_factory=list)


@dataclass
class RelabelResult:
    """Collect the outputs produced by relabeling an existing refined output."""

    refined_path: Path
    kmz_path: Path
    kmz_count: int
    removed_outputs: List[Path]
    requested_label_order: str
    resolved_label_order: str


def build_output_headers(rows: List[Dict[str, Any]]) -> List[str]:
    """Return a sorted list of header names for *rows*, with ``kmz_label`` first."""
    header_set: set[str] = set()
    for row in rows:
        header_set.update(row.keys())
    headers = sorted(header_set)
    if "kmz_label" in headers:
        headers.remove("kmz_label")
        headers.insert(0, "kmz_label")
    return headers


def _count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    data = read_spreadsheet(str(path))
    return len(data.rows)


def _validate_pipeline_outputs(
    *,
    refined_path: Path,
    invalid_path: Path,
    coordinate_review_path: Path,
    rejected_review_path: Path,
    expected_refined_rows: int,
    expected_invalid_rows: int,
    expected_coordinate_review_rows: int,
    expected_rejected_review_rows: int,
    kmz_count: int,
) -> None:
    actual_refined_rows = _count_rows(refined_path)
    actual_invalid_rows = _count_rows(invalid_path)
    actual_coordinate_review_rows = _count_rows(coordinate_review_path)
    actual_rejected_review_rows = _count_rows(rejected_review_path)

    if actual_refined_rows != expected_refined_rows:
        raise ValueError(
            f"Refined output row count mismatch: expected {expected_refined_rows}, found {actual_refined_rows}."
        )
    if actual_invalid_rows != expected_invalid_rows:
        raise ValueError(
            f"Invalid output row count mismatch: expected {expected_invalid_rows}, found {actual_invalid_rows}."
        )
    if actual_coordinate_review_rows != expected_coordinate_review_rows:
        raise ValueError(
            "Coordinate review output row count mismatch: "
            f"expected {expected_coordinate_review_rows}, found {actual_coordinate_review_rows}."
        )
    if actual_rejected_review_rows != expected_rejected_review_rows:
        raise ValueError(
            "Rejected review output row count mismatch: "
            f"expected {expected_rejected_review_rows}, found {actual_rejected_review_rows}."
        )
    if kmz_count != expected_refined_rows:
        raise ValueError(
            f"KMZ placemark count mismatch: expected {expected_refined_rows}, found {kmz_count}."
        )


def run_refinement_pipeline(
    *,
    data_path: Path,
    kmz_path: Path,
    run_dir: Path,
    lat_column: str,
    lon_column: str,
    label_order: str = "auto",
    coordinate_review_path: Path | None = None,
    review_decisions: Mapping[str, CoordinateReviewDecision] | None = None,
) -> RefinementResult:
    """Execute the full crash-data refinement pipeline."""
    log: List[str] = []

    boundary = load_kmz_polygon(str(kmz_path))
    log.append("Loaded KMZ boundary polygon.")

    data = read_spreadsheet(str(data_path))
    log.append(f"Loaded {len(data.rows)} crash rows.")

    resolved_review_decisions: Dict[str, CoordinateReviewDecision] = dict(review_decisions or {})
    if coordinate_review_path is not None:
        review_data = read_spreadsheet(str(coordinate_review_path))
        resolved_review_decisions.update(load_coordinate_review_decisions(review_data.rows))
        log.append(
            f"Loaded {len(resolved_review_decisions)} approved coordinate decision group(s) "
            f"from {coordinate_review_path.name}."
        )
    elif resolved_review_decisions:
        log.append(f"Loaded {len(resolved_review_decisions)} browser review decision(s).")

    prepared_rows, coordinate_review_rows, recovery_report = recover_missing_coordinates(
        data.rows,
        latitude_column=lat_column,
        longitude_column=lon_column,
        boundary=boundary,
        review_decisions=resolved_review_decisions,
    )
    if recovery_report.missing_rows:
        auto_recovered = max(recovery_report.recovered_rows - recovery_report.approved_rows, 0)
        log.append(
            f"Coordinate recovery evaluated {recovery_report.missing_rows} missing-coordinate rows: "
            f"{auto_recovered} auto-recovered, "
            f"{recovery_report.approved_rows} review-approved, "
            f"{recovery_report.rejected_rows} review-rejected, "
            f"{recovery_report.review_rows} queued for review "
            f"({recovery_report.primary_review_rows} primary, "
            f"{recovery_report.secondary_review_rows} secondary)."
        )
    if recovery_report.approved_rows:
        log.append(f"Applied {recovery_report.approved_rows} row(s) from approved coordinate review decisions.")
    if recovery_report.rejected_rows:
        log.append(f"Excluded {recovery_report.rejected_rows} row(s) from the project during coordinate review.")

    refiner = CrashDataRefiner()
    refined_rows, report, boundary_report, invalid_rows = refiner.refine_rows_with_boundary(
        prepared_rows,
        boundary=boundary,
        latitude_column=lat_column,
        longitude_column=lon_column,
    )
    rejected_review_rows = [
        row for row in invalid_rows
        if str(row.get("coordinate_recovery_status") or "") == "review_rejected"
    ]
    invalid_rows = [
        row for row in invalid_rows
        if str(row.get("coordinate_recovery_status") or "") != "review_rejected"
    ]
    requested_label_order = (label_order or "auto").strip().lower() or "auto"
    resolved_label_order = resolve_label_order(
        refined_rows,
        lat_column=lat_column,
        lon_column=lon_column,
        label_order=requested_label_order,
    )
    refined_rows = order_and_number_rows(
        refined_rows,
        lat_column=lat_column,
        lon_column=lon_column,
        label_order=resolved_label_order,
    )
    order_note = (
        "automatic spread detection"
        if requested_label_order == "auto"
        else "explicit user selection"
    )
    log.append(f"KMZ labels ordered {resolved_label_order.replace('_', ' ')} using {order_note}.")
    log.append(
        f"Boundary filter complete: {boundary_report.included_rows} included, "
        f"{boundary_report.excluded_rows} excluded, "
        f"{boundary_report.invalid_rows} invalid."
    )

    out_path = refined_output_path(run_dir, data_path.name)
    run_dir.mkdir(parents=True, exist_ok=True)
    output_headers = build_output_headers(refined_rows)
    write_spreadsheet(str(out_path), refined_rows, headers=output_headers)
    log.append(f"Refined output saved: {out_path.name}")

    inv_path = invalid_output_path(out_path)
    write_spreadsheet(str(inv_path), invalid_rows)
    log.append(f"Invalid coordinate output saved: {inv_path.name}")

    rejected_path = rejected_review_output_path(out_path)
    write_spreadsheet(str(rejected_path), rejected_review_rows)
    log.append(f"Excluded crash review output saved: {rejected_path.name}")

    review_path = coordinate_review_output_path(out_path)
    write_spreadsheet(str(review_path), coordinate_review_rows)
    log.append(f"Coordinate review output saved: {review_path.name}")

    kmz_out = kmz_output_path(out_path)
    kmz_count = write_kmz_report(
        str(kmz_out),
        rows=refined_rows,
        latitude_column=lat_column,
        longitude_column=lon_column,
        label_order=resolved_label_order,
    )
    log.append(f"KMZ report generated: {kmz_out.name} ({kmz_count} placemarks)")

    _validate_pipeline_outputs(
        refined_path=out_path,
        invalid_path=inv_path,
        coordinate_review_path=review_path,
        rejected_review_path=rejected_path,
        expected_refined_rows=len(refined_rows),
        expected_invalid_rows=len(invalid_rows),
        expected_coordinate_review_rows=len(coordinate_review_rows),
        expected_rejected_review_rows=len(rejected_review_rows),
        kmz_count=kmz_count,
    )
    log.append("Output invariants validated against the written files.")

    return RefinementResult(
        refined_rows=refined_rows,
        invalid_rows=invalid_rows,
        rejected_review_rows=rejected_review_rows,
        coordinate_review_rows=coordinate_review_rows,
        refinement_report=report,
        boundary_report=boundary_report,
        recovery_report=recovery_report,
        output_path=out_path,
        invalid_path=inv_path,
        rejected_review_path=rejected_path,
        coordinate_review_path=review_path,
        kmz_path=kmz_out,
        kmz_count=kmz_count,
        requested_label_order=requested_label_order,
        resolved_label_order=resolved_label_order,
        log=log,
    )


def relabel_refined_outputs(
    *,
    refined_path: Path,
    kmz_path: Path,
    lat_column: str,
    lon_column: str,
    label_order: str = "auto",
    remove_output_paths: List[Path] | None = None,
) -> RelabelResult:
    """Rewrite the refined output and KMZ with a new label direction."""
    data = read_spreadsheet(str(refined_path))
    requested_label_order = (label_order or "auto").strip().lower() or "auto"
    resolved_label_order = resolve_label_order(
        data.rows,
        lat_column=lat_column,
        lon_column=lon_column,
        label_order=requested_label_order,
    )
    relabeled_rows = order_and_number_rows(
        data.rows,
        lat_column=lat_column,
        lon_column=lon_column,
        label_order=resolved_label_order,
    )
    headers = build_output_headers(relabeled_rows)
    write_spreadsheet(str(refined_path), relabeled_rows, headers=headers)
    kmz_count = write_kmz_report(
        str(kmz_path),
        rows=relabeled_rows,
        latitude_column=lat_column,
        longitude_column=lon_column,
        label_order=resolved_label_order,
    )

    actual_refined_rows = _count_rows(refined_path)
    if actual_refined_rows != len(relabeled_rows):
        raise ValueError(
            f"Relabeled refined output row count mismatch: expected {len(relabeled_rows)}, found {actual_refined_rows}."
        )
    if kmz_count != len(relabeled_rows):
        raise ValueError(
            f"Relabeled KMZ placemark count mismatch: expected {len(relabeled_rows)}, found {kmz_count}."
        )

    removed_outputs: List[Path] = []
    for path in remove_output_paths or []:
        if path.exists():
            path.unlink()
            removed_outputs.append(path)

    return RelabelResult(
        refined_path=refined_path,
        kmz_path=kmz_path,
        kmz_count=kmz_count,
        removed_outputs=removed_outputs,
        requested_label_order=requested_label_order,
        resolved_label_order=resolved_label_order,
    )


def load_headers_and_guess_columns(
    data_path: str,
) -> Tuple[List[str], Optional[str], Optional[str]]:
    """Read headers from *data_path* and return ``(headers, lat_guess, lon_guess)``."""
    headers = read_spreadsheet_headers(data_path)
    lat_guess, lon_guess = guess_lat_lon_columns(headers)
    return headers, lat_guess, lon_guess
__all__ = [
    "RefinementResult",
    "RelabelResult",
    "build_output_headers",
    "coordinate_review_output_path",
    "invalid_output_path",
    "kmz_output_path",
    "load_headers_and_guess_columns",
    "refined_output_path",
    "rejected_review_output_path",
    "relabel_refined_outputs",
    "run_refinement_pipeline",
]
