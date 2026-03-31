from __future__ import annotations

from datetime import datetime, timezone

from crash_data_refiner.webapp import RUNS, RUNS_LOCK, RunState, app
from crash_data_refiner.services import coordinate_review_output_path, refined_output_path
from crash_data_refiner.spreadsheets import write_spreadsheet


def test_run_review_queue_endpoint_groups_review_rows(tmp_path: Path) -> None:
    run_id = "reviewtest123"
    output_dir = tmp_path / run_id
    output_dir.mkdir(parents=True)
    data_name = "crashes.csv"
    review_path = coordinate_review_output_path(refined_output_path(output_dir, data_name))
    write_spreadsheet(
        str(review_path),
        [
            {
                "coordinate_recovery_group": "SR2|OAK|TESTVILLE|EXAMPLE",
                "coordinate_recovery_group_size": 2,
                "coordinate_recovery_status": "review_required",
                "coordinate_recovery_confidence": "medium",
                "coordinate_recovery_method": "intersection_match",
                "coordinate_recovery_match_count": 3,
                "coordinate_recovery_candidate_count": 2,
                "coordinate_recovery_note": "Needs review.",
                "suggested_latitude": 40.1,
                "suggested_longitude": -86.1,
                "project_relevance_bucket": "primary",
                "project_relevance_score": 84,
                "project_relevance_reason": "Route/intersection pattern matches rows that already fall inside the KMZ.",
                "project_relevance_details": "Decision rule: score 84 meets the primary-review threshold of 45.\nRoute + cross street: SR2 at OAK appears in 2 inside-boundary and 0 outside-boundary known-coordinate crash(es) (100% inside).",
                "roadway_number": "SR2",
                "intersecting_road": "Oak",
                "city": "Testville",
                "county": "Example",
                "crash_id": "10",
            },
            {
                "coordinate_recovery_group": "SR2|OAK|TESTVILLE|EXAMPLE",
                "coordinate_recovery_group_size": 2,
                "coordinate_recovery_status": "review_required",
                "coordinate_recovery_confidence": "medium",
                "coordinate_recovery_method": "intersection_match",
                "coordinate_recovery_match_count": 3,
                "coordinate_recovery_candidate_count": 2,
                "suggested_latitude": 40.1,
                "suggested_longitude": -86.1,
                "project_relevance_bucket": "primary",
                "project_relevance_score": 84,
                "project_relevance_reason": "Route/intersection pattern matches rows that already fall inside the KMZ.",
                "project_relevance_details": "Decision rule: score 84 meets the primary-review threshold of 45.\nRoute + cross street: SR2 at OAK appears in 2 inside-boundary and 0 outside-boundary known-coordinate crash(es) (100% inside).",
                "roadway_number": "SR2",
                "intersecting_road": "Oak",
                "city": "Testville",
                "county": "Example",
                "crash_id": "11",
            },
            {
                "coordinate_recovery_group": "US24|PINE|ELSEWHERE|EXAMPLE",
                "coordinate_recovery_group_size": 1,
                "coordinate_recovery_status": "review_required",
                "coordinate_recovery_confidence": "medium",
                "coordinate_recovery_method": "intersection_match",
                "coordinate_recovery_match_count": 2,
                "coordinate_recovery_candidate_count": 2,
                "coordinate_recovery_note": "Needs review.",
                "suggested_latitude": 41.1,
                "suggested_longitude": -87.1,
                "project_relevance_bucket": "secondary",
                "project_relevance_score": -22,
                "project_relevance_reason": "Route appears only outside the KMZ in rows with coordinates.",
                "project_relevance_details": "Decision rule: score -22 stays below the primary-review threshold of 45.\nRoute only: US24 appears in 0 inside-boundary and 6 outside-boundary known-coordinate crash(es) (0% inside).",
                "roadway_number": "US24",
                "intersecting_road": "Pine",
                "city": "Elsewhere",
                "county": "Example",
                "crash_id": "12",
            },
        ],
    )

    state = RunState(run_id=run_id, created_at=datetime.now(timezone.utc), output_dir=output_dir)
    state.inputs = {"dataFile": data_name}
    with RUNS_LOCK:
        RUNS[run_id] = state

    try:
        with app.test_client() as client:
            response = client.get(f"/api/run/{run_id}/review-queue")
        assert response.status_code == 200
        data = response.get_json()
        assert data["groupCount"] == 2
        assert data["primaryGroupCount"] == 1
        assert data["secondaryGroupCount"] == 1
        assert data["groups"][0]["groupSize"] == 2
        assert data["groups"][0]["title"] == "SR2"
        assert data["groups"][0]["reviewBucket"] == "primary"
        assert data["groups"][0]["reviewScore"] == 84
        assert data["groups"][0]["reviewDetails"][0] == "Decision rule: score 84 meets the primary-review threshold of 45."
        assert data["groups"][1]["groupKey"] == "US24|PINE|ELSEWHERE|EXAMPLE"
        assert data["groups"][1]["reviewBucket"] == "secondary"
        assert data["groups"][1]["reviewDetails"][0] == "Decision rule: score -22 stays below the primary-review threshold of 45."
    finally:
        with RUNS_LOCK:
            RUNS.pop(run_id, None)
