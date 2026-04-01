"""Canonical output path helpers for Crash Data Refiner."""
from __future__ import annotations

from pathlib import Path


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


def rejected_review_output_path(output_path: Path) -> Path:
    """Return the path for crashes explicitly excluded during coordinate review."""
    base_name = output_path.stem
    if base_name.lower().endswith("_refined"):
        base_name = base_name[:-8]
    return output_path.with_name(f"{base_name}_Rejected Coordinate Review{output_path.suffix}")


def coordinate_review_output_path(output_path: Path) -> Path:
    """Return the path for rows that still need manual coordinate review."""
    base_name = output_path.stem
    if base_name.lower().endswith("_refined"):
        base_name = base_name[:-8]
    return output_path.with_name(f"{base_name}_Coordinate Recovery Review{output_path.suffix}")


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
