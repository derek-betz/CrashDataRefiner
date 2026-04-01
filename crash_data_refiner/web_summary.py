"""Summary helpers for the Flask web surface."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .coordinate_recovery import CoordinateRecoveryReport
from .geo import BoundaryFilterReport
from .refiner import RefinementReport
from .run_contract import (
    RunOutputCounts,
    build_run_summary_contract,
    load_output_counts_from_refined_path,
    update_run_summary_contract,
)


def build_web_run_summary(
    *,
    run_duration: str,
    report: RefinementReport,
    boundary_report: BoundaryFilterReport,
    recovery_report: CoordinateRecoveryReport,
    output_counts: RunOutputCounts,
    requested_label_order: str,
    resolved_label_order: str,
    kmz_count: Optional[int],
) -> Dict[str, Any]:
    return build_run_summary_contract(
        report=report,
        boundary_report=boundary_report,
        recovery_report=recovery_report,
        output_counts=output_counts,
        requested_label_order=requested_label_order,
        resolved_label_order=resolved_label_order,
        run_duration=run_duration,
        kmz_count=kmz_count,
    ).as_dict()


def refresh_web_run_summary_for_relabel(
    existing_summary: Dict[str, Any] | None,
    *,
    refined_path: Path,
    requested_label_order: str,
    resolved_label_order: str,
    run_duration: str,
    kmz_count: int,
) -> Dict[str, Any]:
    output_counts = load_output_counts_from_refined_path(refined_path)
    return update_run_summary_contract(
        existing_summary,
        output_counts=output_counts,
        requested_label_order=requested_label_order,
        resolved_label_order=resolved_label_order,
        run_duration=run_duration,
        kmz_count=kmz_count,
    )
