"""Shared run-summary contract used by the web UI and API surfaces."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .coordinate_recovery import CoordinateRecoveryReport
from .geo import BoundaryFilterReport
from .output_paths import (
    coordinate_review_output_path,
    invalid_output_path,
    rejected_review_output_path,
)
from .refiner import RefinementReport
from .spreadsheets import read_spreadsheet


@dataclass(frozen=True)
class RunMetric:
    label: str
    value: str
    detail: str


@dataclass(frozen=True)
class RunOutputCounts:
    refined_rows: int
    invalid_rows: int
    coordinate_review_rows: int
    rejected_review_rows: int


@dataclass(frozen=True)
class LabelOrderingContract:
    requested: str
    resolved: str


@dataclass(frozen=True)
class RunSummaryContract:
    metrics: List[RunMetric]
    output_counts: RunOutputCounts
    label_ordering: LabelOrderingContract

    def as_dict(self) -> Dict[str, Any]:
        return {
            "metrics": [asdict(metric) for metric in self.metrics],
            "outputCounts": {
                "refinedRows": self.output_counts.refined_rows,
                "invalidRows": self.output_counts.invalid_rows,
                "coordinateReviewRows": self.output_counts.coordinate_review_rows,
                "rejectedReviewRows": self.output_counts.rejected_review_rows,
            },
            "labelOrdering": asdict(self.label_ordering),
        }


def _count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    return len(read_spreadsheet(str(path)).rows)


def load_output_counts_from_refined_path(refined_path: Path) -> RunOutputCounts:
    """Read the written outputs for *refined_path* and return authoritative counts."""
    return RunOutputCounts(
        refined_rows=_count_rows(refined_path),
        invalid_rows=_count_rows(invalid_output_path(refined_path)),
        coordinate_review_rows=_count_rows(coordinate_review_output_path(refined_path)),
        rejected_review_rows=_count_rows(rejected_review_output_path(refined_path)),
    )


def build_run_summary_contract(
    *,
    report: RefinementReport,
    boundary_report: Optional[BoundaryFilterReport],
    recovery_report: Optional[CoordinateRecoveryReport],
    output_counts: RunOutputCounts,
    requested_label_order: str,
    resolved_label_order: str,
    run_duration: str = "",
    kmz_count: Optional[int] = None,
) -> RunSummaryContract:
    """Build the authoritative run-summary contract for UI and API consumers."""
    metrics: List[RunMetric] = []

    if boundary_report is not None:
        metrics.extend(
            [
                RunMetric("Rows Scanned", str(boundary_report.total_rows), "Raw crash rows processed"),
                RunMetric("Included", str(boundary_report.included_rows), "Inside boundary"),
                RunMetric("Excluded", str(boundary_report.excluded_rows), "Outside boundary"),
                RunMetric("Invalid", str(boundary_report.invalid_rows), "Missing coordinates"),
            ]
        )
    else:
        metrics.append(RunMetric("Rows Scanned", str(report.total_rows), "Raw crash rows processed"))

    metrics.append(RunMetric("Refined Rows", str(output_counts.refined_rows), "Rows written"))

    if recovery_report is not None and recovery_report.missing_rows:
        auto_recovered = max(recovery_report.recovered_rows - recovery_report.approved_rows, 0)
        metrics.extend(
            [
                RunMetric(
                    "Recovered Coords",
                    str(recovery_report.recovered_rows),
                    "Auto-filled plus approved review decisions",
                ),
                RunMetric(
                    "Review Needed",
                    str(output_counts.coordinate_review_rows),
                    "Rows written to coordinate review output",
                ),
                RunMetric(
                    "Excluded Review",
                    str(output_counts.rejected_review_rows),
                    "Rows kept out of the refined data by explicit project exclusion",
                ),
                RunMetric(
                    "Primary Review",
                    str(recovery_report.primary_review_rows),
                    "Likely in-project review rows",
                ),
                RunMetric(
                    "Secondary Bucket",
                    str(recovery_report.secondary_review_rows),
                    "Lower-likelihood rows kept out of the main queue",
                ),
            ]
        )
        if auto_recovered:
            metrics.append(RunMetric("Auto Recovered", str(auto_recovered), "Rows filled without manual review"))
        if recovery_report.approved_rows:
            metrics.append(
                RunMetric(
                    "Review Applied",
                    str(recovery_report.approved_rows),
                    "Rows filled from approved workbook decisions",
                )
            )

    if kmz_count is not None:
        metrics.append(RunMetric("KMZ Placemarks", str(kmz_count), "Crash map markers"))

    metrics.append(
        RunMetric(
            "Label Order",
            resolved_label_order.replace("_", " "),
            "Automatic spread-based selection" if requested_label_order == "auto" else "Explicit user-selected ordering",
        )
    )

    if run_duration:
        metrics.append(RunMetric("Run Duration", run_duration, "Pipeline runtime"))

    return RunSummaryContract(
        metrics=metrics,
        output_counts=output_counts,
        label_ordering=LabelOrderingContract(
            requested=requested_label_order,
            resolved=resolved_label_order,
        ),
    )


def update_run_summary_contract(
    existing_summary: Dict[str, Any] | None,
    *,
    output_counts: RunOutputCounts,
    requested_label_order: str,
    resolved_label_order: str,
    run_duration: str = "",
    kmz_count: Optional[int] = None,
) -> Dict[str, Any]:
    """Refresh an existing summary with authoritative output counts and label state."""
    summary = dict(existing_summary or {})
    metrics = [dict(metric) for metric in (summary.get("metrics") or [])]

    def upsert_metric(label: str, value: str, detail: str) -> None:
        for metric in metrics:
            if metric.get("label") == label:
                metric["value"] = value
                metric["detail"] = detail
                return
        metrics.append({"label": label, "value": value, "detail": detail})

    upsert_metric("Refined Rows", str(output_counts.refined_rows), "Rows written")
    upsert_metric("Review Needed", str(output_counts.coordinate_review_rows), "Rows written to coordinate review output")
    upsert_metric(
        "Excluded Review",
        str(output_counts.rejected_review_rows),
        "Rows kept out of the refined data by explicit project exclusion",
    )
    if kmz_count is not None:
        upsert_metric("KMZ Placemarks", str(kmz_count), "Crash map markers")
    upsert_metric(
        "Label Order",
        resolved_label_order.replace("_", " "),
        "Automatic spread-based selection" if requested_label_order == "auto" else "Explicit user-selected ordering",
    )
    if run_duration:
        upsert_metric("Run Duration", run_duration, "Pipeline runtime")

    summary["metrics"] = metrics
    summary["outputCounts"] = {
        "refinedRows": output_counts.refined_rows,
        "invalidRows": output_counts.invalid_rows,
        "coordinateReviewRows": output_counts.coordinate_review_rows,
        "rejectedReviewRows": output_counts.rejected_review_rows,
    }
    summary["labelOrdering"] = {
        "requested": requested_label_order,
        "resolved": resolved_label_order,
    }
    return summary


def build_refine_response_summary(
    *,
    report: RefinementReport,
    boundary_report: Optional[BoundaryFilterReport],
    invalid_rows: int,
    coordinate_review_rows: int,
    rejected_review_rows: int,
    recovery_report: Optional[CoordinateRecoveryReport],
    requested_label_order: str = "auto",
    resolved_label_order: str = "west_to_east",
) -> Dict[str, Any]:
    """Return a stable summary payload for the compatibility API surface."""
    contract = build_run_summary_contract(
        report=report,
        boundary_report=boundary_report,
        recovery_report=recovery_report,
        output_counts=RunOutputCounts(
            refined_rows=report.output_rows,
            invalid_rows=invalid_rows,
            coordinate_review_rows=coordinate_review_rows,
            rejected_review_rows=rejected_review_rows,
        ),
        requested_label_order=requested_label_order,
        resolved_label_order=resolved_label_order,
    )
    payload = contract.as_dict()
    payload.update(
        {
            "total_rows": report.total_rows,
            "kept_rows": report.kept_rows,
            "dropped_missing_required": report.dropped_missing_required,
            "dropped_duplicates": report.dropped_duplicates,
            "coerced_dates": report.coerced_dates,
            "coerced_numbers": report.coerced_numbers,
            "coerced_booleans": report.coerced_booleans,
        }
    )
    return payload
