"""Shared application-service layer for CrashDataRefiner.

This module provides the high-level workflow steps used by the web app, API,
and any other entry surface.  Each function encapsulates a single stage of the
pipeline so that surfaces can compose them without reimplementing the logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .geo import BoundaryFilterReport, PolygonBoundary, load_kmz_polygon
from .kmz_report import write_kmz_report
from .normalize import guess_lat_lon_columns, normalize_header
from .pdf_report import generate_pdf_report
from .refiner import CrashDataRefiner, RefinementReport
from .spreadsheets import read_spreadsheet, read_spreadsheet_headers, write_spreadsheet


# ---------------------------------------------------------------------------
# Input / output path helpers
# ---------------------------------------------------------------------------


def refined_output_path(run_dir: Path, input_name: str) -> Path:
    """Return the canonical output path for refined crash data."""
    input_file = Path(input_name)
    suffix = input_file.suffix or ".csv"
    return run_dir / f"{input_file.stem}_refined{suffix}"


def invalid_output_path(output_path: Path) -> Path:
    """Return the path for rows with invalid/missing coordinates."""
    return output_path.with_name(
        f"Crashes Without Valid Lat-Long Data{output_path.suffix}"
    )


def kmz_output_path(output_path: Path) -> Path:
    """Return the KMZ crash-data output path derived from *output_path*."""
    base_name = output_path.stem
    if base_name.lower().endswith("_refined"):
        base_name = base_name[:-8]
    return output_path.with_name(f"{base_name}_Crash Data.kmz")


def pdf_output_path(output_path: Path) -> Path:
    """Return the PDF full-report output path derived from *output_path*."""
    base_name = output_path.stem
    if base_name.lower().endswith("_refined"):
        base_name = base_name[:-8]
    return output_path.with_name(f"{base_name}_Crash Data Full Report.pdf")


def summary_output_path(output_path: Path) -> Path:
    """Return the PDF summary-report output path derived from *output_path*."""
    base_name = output_path.stem
    if base_name.lower().endswith("_refined"):
        base_name = base_name[:-8]
    return output_path.with_name(f"{base_name}_Crash Data Summary Report.pdf")


# ---------------------------------------------------------------------------
# Column ordering / numbering helpers
# ---------------------------------------------------------------------------


def order_and_number_rows(
    rows: List[Dict[str, Any]],
    *,
    lat_column: str,
    lon_column: str,
    label_order: str,
) -> List[Dict[str, Any]]:
    """Sort *rows* by geographic order and assign sequential ``kmz_label`` values."""
    from .geo import parse_coordinate

    lat_key = normalize_header(lat_column)
    lon_key = normalize_header(lon_column)
    indexed: List[Tuple[Any, Dict[str, Any]]] = []
    for idx, row in enumerate(rows):
        lat = parse_coordinate(row.get(lat_key))
        lon = parse_coordinate(row.get(lon_key))
        if label_order == "south_to_north":
            lat_value = lat if lat is not None else float("inf")
            lon_value = lon if lon is not None else float("inf")
            key: Any = (lat_value, lon_value, idx)
        elif label_order == "west_to_east":
            lon_value = lon if lon is not None else float("inf")
            lat_value = lat if lat is not None else float("inf")
            key = (lon_value, lat_value, idx)
        else:
            key = (idx,)
        indexed.append((key, row))

    indexed.sort(key=lambda item: item[0])
    ordered = [item[1] for item in indexed]
    for number, row in enumerate(ordered, start=1):
        row["kmz_label"] = number
    return ordered


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


# ---------------------------------------------------------------------------
# Pipeline result dataclass
# ---------------------------------------------------------------------------


@dataclass
class RefinementResult:
    """Collects all outputs produced by :func:`run_refinement_pipeline`."""

    refined_rows: List[Dict[str, Any]]
    invalid_rows: List[Dict[str, Any]]
    refinement_report: RefinementReport
    boundary_report: BoundaryFilterReport
    output_path: Path
    invalid_path: Path
    kmz_path: Path
    kmz_count: int
    log: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


def run_refinement_pipeline(
    *,
    data_path: Path,
    kmz_path: Path,
    run_dir: Path,
    lat_column: str,
    lon_column: str,
    label_order: str = "west_to_east",
) -> RefinementResult:
    """Execute the full crash-data refinement pipeline.

    Steps:
    1. Load KMZ boundary polygon.
    2. Read crash spreadsheet.
    3. Filter rows by boundary and refine the included rows.
    4. Order rows and assign KMZ labels.
    5. Write refined CSV/XLSX output.
    6. Write invalid-coordinate output.
    7. Write KMZ crash report.

    Returns a :class:`RefinementResult` with all intermediate artefacts.
    """
    log: List[str] = []

    boundary = load_kmz_polygon(str(kmz_path))
    log.append("Loaded KMZ boundary polygon.")

    data = read_spreadsheet(str(data_path))
    log.append(f"Loaded {len(data.rows)} crash rows.")

    refiner = CrashDataRefiner()
    refined_rows, report, boundary_report, invalid_rows = refiner.refine_rows_with_boundary(
        data.rows,
        boundary=boundary,
        latitude_column=lat_column,
        longitude_column=lon_column,
    )
    refined_rows = order_and_number_rows(
        refined_rows,
        lat_column=lat_column,
        lon_column=lon_column,
        label_order=label_order,
    )
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

    kmz_out = kmz_output_path(out_path)
    kmz_count = write_kmz_report(
        str(kmz_out),
        rows=refined_rows,
        latitude_column=lat_column,
        longitude_column=lon_column,
        label_order=label_order,
    )
    log.append(f"KMZ report generated: {kmz_out.name} ({kmz_count} placemarks)")

    return RefinementResult(
        refined_rows=refined_rows,
        invalid_rows=invalid_rows,
        refinement_report=report,
        boundary_report=boundary_report,
        output_path=out_path,
        invalid_path=inv_path,
        kmz_path=kmz_out,
        kmz_count=kmz_count,
        log=log,
    )


# ---------------------------------------------------------------------------
# Header inspection
# ---------------------------------------------------------------------------


def load_headers_and_guess_columns(
    data_path: str,
) -> Tuple[List[str], Optional[str], Optional[str]]:
    """Read headers from *data_path* and return ``(headers, lat_guess, lon_guess)``."""
    headers = read_spreadsheet_headers(data_path)
    lat_guess, lon_guess = guess_lat_lon_columns(headers)
    return headers, lat_guess, lon_guess


# ---------------------------------------------------------------------------
# PDF report
# ---------------------------------------------------------------------------


def run_pdf_report(
    *,
    source_path: Path,
    output_path: Path,
    lat_column: str,
    lon_column: str,
) -> None:
    """Generate a PDF full report from *source_path* and write to *output_path*."""
    data = read_spreadsheet(str(source_path))
    generate_pdf_report(
        str(output_path),
        rows=data.rows,
        latitude_column=lat_column,
        longitude_column=lon_column,
    )
