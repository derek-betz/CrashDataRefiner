from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from crash_data_refiner.coordinate_recovery import CoordinateReviewDecision, build_coordinate_review_wizard_steps
from crash_data_refiner.geo import is_usable_coordinate_pair
from crash_data_refiner.run_contract import load_output_counts_from_refined_path
from crash_data_refiner.services import (
    load_headers_and_guess_columns,
    pdf_output_path,
    relabel_refined_outputs,
    run_pdf_report,
    run_refinement_pipeline,
)
from crash_data_refiner.spreadsheets import read_spreadsheet

REFERENCE_ROOT = REPO_ROOT / "raw-crash-data-for-reference"
DEFAULT_DATASETS = ("20H00010H", "2100235", "2100238", "2101166")


@dataclass
class DatasetCheck:
    ok: bool
    seconds: float
    details: dict[str, Any]


def _discover_dataset_files(dataset_dir: Path) -> tuple[Path, Path]:
    data_files = sorted(p for p in dataset_dir.iterdir() if p.is_file() and p.suffix.lower() in {".csv", ".xlsx", ".xlsm"})
    kmz_files = sorted(p for p in dataset_dir.iterdir() if p.is_file() and p.suffix.lower() == ".kmz")
    if len(data_files) != 1 or len(kmz_files) != 1:
        raise RuntimeError(
            f"{dataset_dir.name}: expected exactly 1 crash data file and 1 KMZ, "
            f"found {len(data_files)} data and {len(kmz_files)} KMZ files."
        )
    return data_files[0], kmz_files[0]


def _run_check_refine(dataset_name: str, data_path: Path, kmz_path: Path, run_dir: Path) -> tuple[DatasetCheck, Any]:
    headers, lat_guess, lon_guess = load_headers_and_guess_columns(str(data_path))
    if not lat_guess or not lon_guess:
        raise RuntimeError(f"{dataset_name}: unable to infer latitude and longitude columns.")

    start = time.perf_counter()
    result = run_refinement_pipeline(
        data_path=data_path,
        kmz_path=kmz_path,
        run_dir=run_dir,
        lat_column=lat_guess,
        lon_column=lon_guess,
        label_order="auto",
    )
    seconds = round(time.perf_counter() - start, 2)
    counts = load_output_counts_from_refined_path(result.output_path)
    steps = build_coordinate_review_wizard_steps(result.coordinate_review_rows)
    primary_steps = [step for step in steps if str(step.get("reviewBucket") or "primary") != "secondary"]
    secondary_steps = [step for step in steps if str(step.get("reviewBucket") or "primary") == "secondary"]
    invalid_suggested_steps = [
        {
            "rowKey": str(step.get("rowKey") or ""),
            "crashId": str(step.get("crashId") or ""),
            "suggestedLatitude": step.get("suggestedLatitude"),
            "suggestedLongitude": step.get("suggestedLongitude"),
            "suggestedInsideBoundary": step.get("suggestedInsideBoundary"),
        }
        for step in steps
        if step.get("hasSuggestion")
        and (
            not is_usable_coordinate_pair(
                step.get("suggestedLatitude"),
                step.get("suggestedLongitude"),
            )
            or step.get("suggestedInsideBoundary") is not True
        )
    ]
    check = DatasetCheck(
        ok=not invalid_suggested_steps,
        seconds=seconds,
        details={
            "headerCount": len(headers),
            "latGuess": lat_guess,
            "lonGuess": lon_guess,
            "requestedLabelOrder": result.requested_label_order,
            "resolvedLabelOrder": result.resolved_label_order,
            "rowsScanned": result.boundary_report.total_rows,
            "included": result.boundary_report.included_rows,
            "excluded": result.boundary_report.excluded_rows,
            "invalid": result.boundary_report.invalid_rows,
            "refinedRows": counts.refined_rows,
            "coordinateReviewRows": counts.coordinate_review_rows,
            "rejectedReviewRows": counts.rejected_review_rows,
            "kmzPlacemarks": result.kmz_count,
            "missingCoordinateRows": result.recovery_report.missing_rows,
            "recoveredRows": result.recovery_report.recovered_rows,
            "primaryReviewRows": result.recovery_report.primary_review_rows,
            "secondaryReviewRows": result.recovery_report.secondary_review_rows,
            "primaryWizardSteps": len(primary_steps),
            "secondaryWizardSteps": len(secondary_steps),
            "invalidSuggestedSteps": invalid_suggested_steps,
            "outputDir": str(run_dir),
        },
    )
    return check, (result, lat_guess, lon_guess, steps, counts)


def _run_check_exclude_one(
    data_path: Path,
    kmz_path: Path,
    run_dir: Path,
    *,
    lat_column: str,
    lon_column: str,
    steps: list[dict[str, Any]],
) -> DatasetCheck:
    target = steps[0] if steps else None
    if target is None:
        return DatasetCheck(
            ok=True,
            seconds=0.0,
            details={"skipped": True, "reason": "No coordinate-review rows were generated for this dataset."},
        )

    start = time.perf_counter()
    result = run_refinement_pipeline(
        data_path=data_path,
        kmz_path=kmz_path,
        run_dir=run_dir,
        lat_column=lat_column,
        lon_column=lon_column,
        label_order="auto",
        review_decisions={
            target["rowKey"]: CoordinateReviewDecision(
                group_key=target["rowKey"],
                action="reject",
                note="Reference-dataset QC exclusion test.",
            )
        },
    )
    seconds = round(time.perf_counter() - start, 2)
    counts = load_output_counts_from_refined_path(result.output_path)
    rejected_rows = read_spreadsheet(str(result.rejected_review_path)).rows
    matched = any(
        str(row.get("coordinate_recovery_row_key") or "") == target["rowKey"]
        or str(row.get("crash_id") or "") == str(target.get("crashId") or "")
        for row in rejected_rows
    )
    return DatasetCheck(
        ok=matched and counts.rejected_review_rows >= 1,
        seconds=seconds,
        details={
            "targetRowKey": target["rowKey"],
            "targetCrashId": target.get("crashId"),
            "rejectedReviewRows": counts.rejected_review_rows,
            "remainingReviewRows": counts.coordinate_review_rows,
            "matchedRejectedOutput": matched,
            "outputDir": str(run_dir),
        },
    )


def _run_check_relabel(
    result: Any,
    *,
    lat_column: str,
    lon_column: str,
    expected_refined_rows: int,
) -> DatasetCheck:
    target_label_order = "south_to_north" if result.resolved_label_order == "west_to_east" else "west_to_east"
    start = time.perf_counter()
    relabel_result = relabel_refined_outputs(
        refined_path=result.output_path,
        kmz_path=result.kmz_path,
        lat_column=lat_column,
        lon_column=lon_column,
        label_order=target_label_order,
    )
    seconds = round(time.perf_counter() - start, 2)
    counts = load_output_counts_from_refined_path(result.output_path)
    return DatasetCheck(
        ok=relabel_result.resolved_label_order == target_label_order and counts.refined_rows == expected_refined_rows,
        seconds=seconds,
        details={
            "requestedLabelOrder": target_label_order,
            "resolvedLabelOrder": relabel_result.resolved_label_order,
            "refinedRowsAfterRelabel": counts.refined_rows,
        },
    )


def _run_check_pdf(result: Any, *, lat_column: str, lon_column: str) -> DatasetCheck:
    report_path = pdf_output_path(result.output_path)
    start = time.perf_counter()
    run_pdf_report(
        source_path=result.output_path,
        output_path=report_path,
        lat_column=lat_column,
        lon_column=lon_column,
    )
    seconds = round(time.perf_counter() - start, 2)
    return DatasetCheck(
        ok=report_path.exists() and report_path.stat().st_size > 0,
        seconds=seconds,
        details={
            "path": str(report_path),
            "bytes": report_path.stat().st_size if report_path.exists() else 0,
        },
    )


def run_reference_dataset_qc(dataset_names: tuple[str, ...] = DEFAULT_DATASETS) -> dict[str, Any]:
    output_root = REPO_ROOT / "outputs" / "dataset_qc" / datetime.now().strftime("%Y%m%d_%H%M%S")
    output_root.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "createdAt": datetime.now().isoformat(),
        "outputRoot": str(output_root),
        "datasets": [],
    }

    for dataset_name in dataset_names:
        dataset_dir = REFERENCE_ROOT / dataset_name
        dataset_summary: dict[str, Any] = {
            "dataset": dataset_name,
            "folder": str(dataset_dir),
            "status": "pending",
            "checks": {},
            "issues": [],
        }
        try:
            data_path, kmz_path = _discover_dataset_files(dataset_dir)
            dataset_summary["dataFiles"] = [data_path.name]
            dataset_summary["kmzFiles"] = [kmz_path.name]

            refine_dir = output_root / dataset_name / "base"
            refine_check, context = _run_check_refine(dataset_name, data_path, kmz_path, refine_dir)
            result, lat_guess, lon_guess, steps, counts = context
            dataset_summary["checks"]["refine"] = asdict(refine_check)
            if not refine_check.ok:
                dataset_summary["issues"].append(
                    "Review wizard surfaced at least one invalid or outside-boundary suggested placement."
                )

            exclude_check = _run_check_exclude_one(
                data_path,
                kmz_path,
                output_root / dataset_name / "exclude_one",
                lat_column=lat_guess,
                lon_column=lon_guess,
                steps=steps,
            )
            dataset_summary["checks"]["excludeOne"] = asdict(exclude_check)
            if not exclude_check.ok:
                dataset_summary["issues"].append("Row-level exclusion rerun did not produce the expected rejected-review output.")

            relabel_check = _run_check_relabel(
                result,
                lat_column=lat_guess,
                lon_column=lon_guess,
                expected_refined_rows=counts.refined_rows,
            )
            dataset_summary["checks"]["relabel"] = asdict(relabel_check)
            if not relabel_check.ok:
                dataset_summary["issues"].append("Relabeling did not preserve the refined row set or did not resolve to the requested direction.")

            pdf_check = _run_check_pdf(result, lat_column=lat_guess, lon_column=lon_guess)
            dataset_summary["checks"]["pdf"] = asdict(pdf_check)
            if not pdf_check.ok:
                dataset_summary["issues"].append("PDF generation did not produce a non-empty file.")

            dataset_summary["status"] = "ok" if not dataset_summary["issues"] else "warning"
        except Exception as exc:
            dataset_summary["status"] = "error"
            dataset_summary["issues"].append(f"{type(exc).__name__}: {exc}")
        summary["datasets"].append(dataset_summary)

    summary_path = output_root / "dataset_qc_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary["summaryPath"] = str(summary_path)
    return summary


def main() -> None:
    summary = run_reference_dataset_qc()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
