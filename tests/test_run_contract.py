from __future__ import annotations

from pathlib import Path

from crash_data_refiner.run_contract import (
    RunOutputCounts,
    build_run_summary_contract,
    load_output_counts_from_refined_path,
    update_run_summary_contract,
)
from crash_data_refiner.coordinate_recovery import CoordinateRecoveryReport
from crash_data_refiner.geo import BoundaryFilterReport
from crash_data_refiner.output_paths import (
    coordinate_review_output_path,
    invalid_output_path,
    rejected_review_output_path,
)
from crash_data_refiner.refiner import RefinementReport
from crash_data_refiner.spreadsheets import write_spreadsheet


def test_load_output_counts_from_refined_path_reads_written_outputs(tmp_path: Path) -> None:
    refined_path = tmp_path / "crashes_refined.csv"
    write_spreadsheet(str(refined_path), [{"crash_id": "1"}, {"crash_id": "2"}])
    write_spreadsheet(str(invalid_output_path(refined_path)), [{"crash_id": "3"}])
    write_spreadsheet(str(coordinate_review_output_path(refined_path)), [{"crash_id": "4"}, {"crash_id": "5"}])
    write_spreadsheet(str(rejected_review_output_path(refined_path)), [{"crash_id": "6"}])

    counts = load_output_counts_from_refined_path(refined_path)

    assert counts == RunOutputCounts(
        refined_rows=2,
        invalid_rows=1,
        coordinate_review_rows=2,
        rejected_review_rows=1,
    )


def test_update_run_summary_contract_refreshes_output_counts_and_label_state() -> None:
    refreshed = update_run_summary_contract(
        {
            "metrics": [
                {"label": "Rows Scanned", "value": "100", "detail": "Raw crash rows processed"},
                {"label": "Refined Rows", "value": "12", "detail": "Rows written"},
            ]
        },
        output_counts=RunOutputCounts(
            refined_rows=14,
            invalid_rows=3,
            coordinate_review_rows=8,
            rejected_review_rows=2,
        ),
        requested_label_order="auto",
        resolved_label_order="south_to_north",
        run_duration="9s",
        kmz_count=14,
    )

    metrics = {metric["label"]: metric for metric in refreshed["metrics"]}
    assert metrics["Refined Rows"]["value"] == "14"
    assert metrics["Review Needed"]["value"] == "8"
    assert metrics["Excluded Review"]["value"] == "2"
    assert metrics["KMZ Placemarks"]["value"] == "14"
    assert refreshed["outputCounts"]["invalidRows"] == 3
    assert refreshed["labelOrdering"]["resolved"] == "south_to_north"


def test_build_run_summary_contract_includes_authoritative_output_counts() -> None:
    contract = build_run_summary_contract(
        report=RefinementReport(
            total_rows=25,
            kept_rows=20,
            dropped_missing_required=1,
            dropped_duplicates=2,
            coerced_dates=0,
            coerced_numbers=0,
            coerced_booleans=0,
        ),
        boundary_report=BoundaryFilterReport(
            total_rows=25,
            included_rows=14,
            excluded_rows=7,
            invalid_rows=4,
        ),
        recovery_report=CoordinateRecoveryReport(
            missing_rows=12,
            recovered_rows=4,
            approved_rows=1,
            rejected_rows=2,
            review_rows=0,
            suggested_rows=3,
            primary_review_rows=5,
            secondary_review_rows=2,
            recovered_by_method={},
        ),
        output_counts=RunOutputCounts(
            refined_rows=14,
            invalid_rows=2,
            coordinate_review_rows=6,
            rejected_review_rows=2,
        ),
        requested_label_order="auto",
        resolved_label_order="south_to_north",
        run_duration="14s",
        kmz_count=14,
    ).as_dict()

    assert contract["outputCounts"]["refinedRows"] == 14
    assert contract["outputCounts"]["coordinateReviewRows"] == 6
    assert contract["labelOrdering"]["requested"] == "auto"
    metrics = {metric["label"]: metric for metric in contract["metrics"]}
    assert metrics["Review Needed"]["value"] == "6"
    assert metrics["Excluded Review"]["value"] == "2"
