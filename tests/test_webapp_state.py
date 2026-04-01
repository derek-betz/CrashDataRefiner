from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from crash_data_refiner.coordinate_recovery import CoordinateRecoveryReport
from crash_data_refiner.geo import BoundaryFilterReport
from crash_data_refiner.refiner import RefinementReport
from crash_data_refiner.spreadsheets import write_spreadsheet
from crash_data_refiner.webapp import RUNS, RUNS_LOCK, RunState, _build_summary, _create_state, _snapshot_state


def test_create_state_uses_timezone_aware_utc_created_at() -> None:
    state = _create_state()
    try:
        assert state.created_at.tzinfo is not None
        assert state.created_at.utcoffset() == timedelta(0)
    finally:
        with RUNS_LOCK:
            RUNS.pop(state.run_id, None)


def test_run_state_log_and_snapshot_use_timezone_aware_iso_strings() -> None:
    started_at = datetime.now(timezone.utc)
    finished_at = started_at + timedelta(seconds=5)
    state = RunState(
        run_id="snapshot-test",
        created_at=started_at,
        started_at=started_at,
        finished_at=finished_at,
    )

    state.append_log("Generated test log entry.")
    snapshot = state.snapshot()

    log_timestamp = datetime.fromisoformat(state.log_entries[0]["ts"])
    created_timestamp = datetime.fromisoformat(snapshot["createdAt"])
    started_timestamp = datetime.fromisoformat(snapshot["startedAt"])
    finished_timestamp = datetime.fromisoformat(snapshot["finishedAt"])

    assert log_timestamp.tzinfo is not None
    assert log_timestamp.utcoffset() == timedelta(0)
    assert created_timestamp.tzinfo is not None
    assert started_timestamp.tzinfo is not None
    assert finished_timestamp.tzinfo is not None
    assert snapshot["duration"] == "5s"


def test_build_summary_uses_actual_output_counts_for_review_metrics() -> None:
    started_at = datetime.now(timezone.utc)
    finished_at = started_at + timedelta(seconds=7)
    state = RunState(
        run_id="summary-count-test",
        created_at=started_at,
        started_at=started_at,
        finished_at=finished_at,
    )

    summary = _build_summary(
        state=state,
        report=RefinementReport(
            total_rows=42,
            kept_rows=42,
            dropped_missing_required=0,
            dropped_duplicates=0,
            coerced_dates=0,
            coerced_numbers=0,
            coerced_booleans=0,
        ),
        boundary_report=BoundaryFilterReport(total_rows=100, included_rows=42, excluded_rows=55, invalid_rows=3),
        recovery_report=CoordinateRecoveryReport(
            missing_rows=20,
            recovered_rows=6,
            approved_rows=1,
            rejected_rows=0,
            review_rows=0,
            suggested_rows=2,
            primary_review_rows=0,
            secondary_review_rows=0,
            recovered_by_method={},
        ),
        coordinate_review_count=14,
        rejected_review_count=5,
        kmz_count=42,
        requested_label_order="auto",
        resolved_label_order="south_to_north",
    )

    metrics = {metric["label"]: metric for metric in summary["metrics"]}
    assert metrics["Review Needed"]["value"] == "14"
    assert metrics["Excluded Review"]["value"] == "5"
    assert summary["outputCounts"]["refinedRows"] == 42
    assert summary["outputCounts"]["coordinateReviewRows"] == 14
    assert summary["outputCounts"]["rejectedReviewRows"] == 5
    assert summary["labelOrdering"]["resolved"] == "south_to_north"


def test_snapshot_state_backfills_output_counts_from_written_outputs(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True)
    refined_path = run_dir / "crashes_refined.csv"
    write_spreadsheet(str(refined_path), [{"crash_id": "1"}])
    write_spreadsheet(str(run_dir / "Crashes Without Valid Lat-Long Data.csv"), [{"crash_id": "2"}])
    write_spreadsheet(str(run_dir / "crashes_Coordinate Recovery Review.csv"), [{"crash_id": "3"}, {"crash_id": "4"}])
    write_spreadsheet(str(run_dir / "crashes_Rejected Coordinate Review.csv"), [{"crash_id": "5"}])

    state = RunState(
        run_id="snapshot-counts",
        created_at=datetime.now(timezone.utc),
        output_dir=run_dir,
        inputs={"dataFile": "crashes.csv"},
        summary={"metrics": []},
    )

    snapshot = _snapshot_state(state)

    assert snapshot["summary"]["outputCounts"]["refinedRows"] == 1
    assert snapshot["summary"]["outputCounts"]["invalidRows"] == 1
    assert snapshot["summary"]["outputCounts"]["coordinateReviewRows"] == 2
    assert snapshot["summary"]["outputCounts"]["rejectedReviewRows"] == 1
