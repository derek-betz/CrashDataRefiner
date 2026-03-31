from __future__ import annotations

from datetime import datetime, timedelta, timezone

from crash_data_refiner.webapp import RUNS, RUNS_LOCK, RunState, _create_state


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
