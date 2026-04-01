from __future__ import annotations

from crash_data_refiner.coordinate_recovery import (
    CoordinateReviewDecision,
    build_coordinate_review_queue,
    build_coordinate_review_wizard_steps,
    load_coordinate_review_decisions,
    recover_missing_coordinates,
)
from crash_data_refiner.geo import PolygonBoundary


def test_recover_missing_coordinates_autofills_safe_matches_and_groups_review_rows() -> None:
    rows = [
        {
            "Crash ID": "1",
            "Latitude": "40.0000",
            "Longitude": "-86.0000",
            "Roadway Number": "SR1",
            "Intersecting Road": "Main",
            "City": "Testville",
            "County": "Example",
        },
        {
            "Crash ID": "2",
            "Latitude": "",
            "Longitude": "",
            "Roadway Number": "SR1",
            "Intersecting Road": "Main",
            "City": "Testville",
            "County": "Example",
        },
        {
            "Crash ID": "10",
            "Latitude": "40.1000",
            "Longitude": "-86.1000",
            "Roadway Number": "SR2",
            "Intersecting Road": "Oak",
            "City": "Testville",
            "County": "Example",
        },
        {
            "Crash ID": "11",
            "Latitude": "40.1001",
            "Longitude": "-86.1000",
            "Roadway Number": "SR2",
            "Intersecting Road": "Oak",
            "City": "Testville",
            "County": "Example",
        },
        {
            "Crash ID": "12",
            "Latitude": "40.2000",
            "Longitude": "-86.2000",
            "Roadway Number": "SR2",
            "Intersecting Road": "Oak",
            "City": "Testville",
            "County": "Example",
        },
        {
            "Crash ID": "20",
            "Latitude": "",
            "Longitude": "",
            "Roadway Number": "SR2",
            "Intersecting Road": "Oak",
            "City": "Testville",
            "County": "Example",
        },
        {
            "Crash ID": "21",
            "Latitude": "",
            "Longitude": "",
            "Roadway Number": "SR2",
            "Intersecting Road": "Oak",
            "City": "Testville",
            "County": "Example",
        },
    ]

    output_rows, review_rows, report = recover_missing_coordinates(
        rows,
        latitude_column="Latitude",
        longitude_column="Longitude",
    )

    assert report.missing_rows == 3
    assert report.recovered_rows == 1
    assert report.approved_rows == 0
    assert report.review_rows == 2
    assert report.suggested_rows == 2
    assert report.recovered_by_method == {"intersection_match": 1}

    auto_recovered = next(row for row in output_rows if row["crash_id"] == "2")
    assert auto_recovered["coordinate_source"] == "recovered"
    assert auto_recovered["coordinate_recovery_status"] == "auto_recovered"
    assert auto_recovered["coordinate_recovery_method"] == "intersection_match"
    assert float(auto_recovered["latitude"]) == 40.0
    assert float(auto_recovered["longitude"]) == -86.0

    grouped_review_rows = [row for row in review_rows if row["crash_id"] in {"20", "21"}]
    assert len(grouped_review_rows) == 2
    assert {row["coordinate_recovery_status"] for row in grouped_review_rows} == {"review_required"}
    assert {row["coordinate_recovery_confidence"] for row in grouped_review_rows} == {"medium"}
    assert {row["coordinate_recovery_group_size"] for row in grouped_review_rows} == {2}
    assert grouped_review_rows[0]["coordinate_recovery_group"] == grouped_review_rows[1]["coordinate_recovery_group"]
    assert grouped_review_rows[0]["suggested_latitude"] is not None
    assert grouped_review_rows[0]["suggested_longitude"] is not None


def test_recover_missing_coordinates_ignores_origin_evidence_coordinates() -> None:
    rows = [
        {
            "Crash ID": "1",
            "Latitude": "0.0",
            "Longitude": "0.0",
            "Roadway Number": "US41",
            "Intersecting Road": "Maplewood",
            "City": "Highland",
            "County": "Lake",
        },
        {
            "Crash ID": "2",
            "Latitude": "0.0",
            "Longitude": "0.0",
            "Roadway Number": "US41",
            "Intersecting Road": "Maplewood",
            "City": "Highland",
            "County": "Lake",
        },
        {
            "Crash ID": "3",
            "Latitude": "41.55916",
            "Longitude": "-87.47128",
            "Roadway Number": "US41",
            "Intersecting Road": "Maplewood",
            "City": "Highland",
            "County": "Lake",
        },
        {
            "Crash ID": "4",
            "Latitude": "",
            "Longitude": "",
            "Roadway Number": "US41",
            "Intersecting Road": "Maplewood",
            "City": "Highland",
            "County": "Lake",
        },
    ]

    output_rows, review_rows, report = recover_missing_coordinates(
        rows,
        latitude_column="Latitude",
        longitude_column="Longitude",
        boundary=PolygonBoundary(
            outer=[
                (-87.48, 41.55),
                (-87.46, 41.55),
                (-87.46, 41.57),
                (-87.48, 41.57),
                (-87.48, 41.55),
            ]
        ),
    )

    recovered_row = next(row for row in output_rows if row["crash_id"] == "4")
    assert report.recovered_rows == 1
    assert report.review_rows == 0
    assert recovered_row["coordinate_source"] == "recovered"
    assert recovered_row["latitude"] == 41.55916
    assert recovered_row["longitude"] == -87.47128


def test_load_coordinate_review_decisions_uses_approved_or_suggested_coordinates() -> None:
    decisions = load_coordinate_review_decisions(
        [
            {
                "coordinate_recovery_group": "SR2|OAK|TESTVILLE|EXAMPLE",
                "approve_for_group": "yes",
                "suggested_latitude": "40.1000",
                "suggested_longitude": "-86.1000",
                "review_notes": "Approved as grouped fix.",
            },
            {
                "coordinate_recovery_group": "SR3|MAIN|TESTVILLE|EXAMPLE",
                "approved_latitude": "40.2000",
                "approved_longitude": "-86.2000",
            },
        ]
    )

    assert decisions["SR2|OAK|TESTVILLE|EXAMPLE"].latitude == 40.1
    assert decisions["SR2|OAK|TESTVILLE|EXAMPLE"].longitude == -86.1
    assert decisions["SR2|OAK|TESTVILLE|EXAMPLE"].note == "Approved as grouped fix."
    assert decisions["SR3|MAIN|TESTVILLE|EXAMPLE"].latitude == 40.2
    assert decisions["SR3|MAIN|TESTVILLE|EXAMPLE"].longitude == -86.2


def test_recover_missing_coordinates_scores_project_relevance_from_boundary_profile() -> None:
    boundary = PolygonBoundary(
        outer=[
            (-1.0, 0.0),
            (1.0, 0.0),
            (1.0, 2.0),
            (-1.0, 2.0),
            (-1.0, 0.0),
        ]
    )
    rows = []

    for index in range(6):
        rows.append(
            {
                "Crash ID": f"I{index}",
                "Latitude": "1.0000",
                "Longitude": "0.0000",
                "Roadway Number": "SR1",
                "Intersecting Road": "Main",
                "City": "Testville",
                "County": "Example",
            }
        )
    for index in range(4):
        rows.append(
            {
                "Crash ID": f"J{index}",
                "Latitude": "1.0010",
                "Longitude": "0.0000",
                "Roadway Number": "SR1",
                "Intersecting Road": "Main",
                "City": "Testville",
                "County": "Example",
            }
        )
    for index in range(3):
        rows.append(
            {
                "Crash ID": f"O{index}",
                "Latitude": "5.0000",
                "Longitude": "0.0000",
                "Roadway Number": "US24",
                "Intersecting Road": "Pine",
                "City": "Elsewhere",
                "County": "Example",
            }
        )
    for index in range(3):
        rows.append(
            {
                "Crash ID": f"P{index}",
                "Latitude": "5.0010",
                "Longitude": "0.0000",
                "Roadway Number": "US24",
                "Intersecting Road": "Pine",
                "City": "Elsewhere",
                "County": "Example",
            }
        )

    rows.extend(
        [
            {
                "Crash ID": "M1",
                "Latitude": "",
                "Longitude": "",
                "Roadway Number": "SR1",
                "Intersecting Road": "Main",
                "City": "Testville",
                "County": "Example",
            },
            {
                "Crash ID": "M2",
                "Latitude": "",
                "Longitude": "",
                "Roadway Number": "US24",
                "Intersecting Road": "Pine",
                "City": "Elsewhere",
                "County": "Example",
            },
        ]
    )

    _output_rows, review_rows, report = recover_missing_coordinates(
        rows,
        latitude_column="Latitude",
        longitude_column="Longitude",
        boundary=boundary,
    )

    assert report.review_rows == 2
    assert report.primary_review_rows == 1
    assert report.secondary_review_rows == 1

    likely_row = next(row for row in review_rows if row["crash_id"] == "M1")
    unlikely_row = next(row for row in review_rows if row["crash_id"] == "M2")

    assert likely_row["coordinate_recovery_confidence"] == "medium"
    assert likely_row["project_relevance_bucket"] == "primary"
    assert likely_row["project_relevance_score"] >= 45
    assert "inside the KMZ" in likely_row["project_relevance_reason"]
    assert "Decision rule:" in likely_row["project_relevance_details"]
    assert "Route + cross street: SR1 at MAIN appears in 10 inside-boundary and 0 outside-boundary known-coordinate crash(es) (100% inside)." in likely_row["project_relevance_details"]

    assert unlikely_row["coordinate_recovery_confidence"] == "medium"
    assert unlikely_row["project_relevance_bucket"] == "secondary"
    assert unlikely_row["project_relevance_score"] < 45
    assert "outside the KMZ" in unlikely_row["project_relevance_reason"]
    assert "Route + cross street: US24 at PINE appears in 0 inside-boundary and 6 outside-boundary known-coordinate crash(es) (0% inside)." in unlikely_row["project_relevance_details"]


def test_build_coordinate_review_queue_groups_rows_for_browser_review() -> None:
    queue = build_coordinate_review_queue(
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
                "suggested_latitude": "40.1000",
                "suggested_longitude": "-86.1000",
                "project_relevance_bucket": "primary",
                "project_relevance_score": 82,
                "project_relevance_reason": "Route/intersection pattern matches rows that already fall inside the KMZ.",
                "project_relevance_details": "Decision rule: score 82 meets the primary-review threshold of 45.\nRoute + cross street: SR2 at OAK appears in 2 inside-boundary and 0 outside-boundary known-coordinate crash(es) (100% inside).",
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
                "suggested_latitude": "40.1000",
                "suggested_longitude": "-86.1000",
                "project_relevance_bucket": "primary",
                "project_relevance_score": 82,
                "project_relevance_reason": "Route/intersection pattern matches rows that already fall inside the KMZ.",
                "project_relevance_details": "Decision rule: score 82 meets the primary-review threshold of 45.\nRoute + cross street: SR2 at OAK appears in 2 inside-boundary and 0 outside-boundary known-coordinate crash(es) (100% inside).",
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
                "suggested_latitude": "41.1000",
                "suggested_longitude": "-87.1000",
                "project_relevance_bucket": "secondary",
                "project_relevance_score": -30,
                "project_relevance_reason": "Route appears only outside the KMZ in rows with coordinates.",
                "project_relevance_details": "Decision rule: score -30 stays below the primary-review threshold of 45.\nRoute only: US24 appears in 0 inside-boundary and 6 outside-boundary known-coordinate crash(es) (0% inside).",
                "roadway_number": "US24",
                "intersecting_road": "Pine",
                "city": "Elsewhere",
                "county": "Example",
                "crash_id": "12",
            },
        ]
    )

    assert len(queue) == 2
    assert queue[0]["groupKey"] == "SR2|OAK|TESTVILLE|EXAMPLE"
    assert queue[0]["groupSize"] == 2
    assert queue[0]["hasSuggestion"] is True
    assert queue[0]["title"] == "SR2"
    assert "OAK" in queue[0]["detail"]
    assert queue[0]["sampleIds"] == ["10", "11"]
    assert queue[0]["reviewBucket"] == "primary"
    assert queue[0]["reviewScore"] == 82
    assert "inside the KMZ" in queue[0]["reviewReason"]
    assert queue[0]["reviewDetails"][0] == "Decision rule: score 82 meets the primary-review threshold of 45."
    assert "Route + cross street: SR2 at OAK appears in 2 inside-boundary and 0 outside-boundary known-coordinate crash(es) (100% inside)." in queue[0]["reviewDetails"]
    assert queue[1]["groupKey"] == "US24|PINE|ELSEWHERE|EXAMPLE"
    assert queue[1]["reviewBucket"] == "secondary"
    assert queue[1]["reviewScore"] == -30
    assert queue[1]["reviewDetails"][0] == "Decision rule: score -30 stays below the primary-review threshold of 45."


def test_build_coordinate_review_wizard_steps_orders_rows_and_exposes_narrative() -> None:
    steps = build_coordinate_review_wizard_steps(
        [
            {
                "coordinate_recovery_group": "SR2|OAK|TESTVILLE|EXAMPLE",
                "coordinate_recovery_row_key": "10__row4",
                "coordinate_recovery_source_row": 4,
                "coordinate_recovery_group_size": 2,
                "coordinate_recovery_status": "review_required",
                "coordinate_recovery_confidence": "medium",
                "coordinate_recovery_method": "intersection_match",
                "coordinate_recovery_match_count": 3,
                "coordinate_recovery_candidate_count": 2,
                "coordinate_recovery_note": "Needs review.",
                "suggested_latitude": "40.1000",
                "suggested_longitude": "-86.1000",
                "suggested_inside_boundary": "yes",
                "project_relevance_bucket": "primary",
                "project_relevance_score": 82,
                "project_relevance_reason": "Route/intersection pattern matches rows that already fall inside the KMZ.",
                "project_relevance_details": "Decision rule: score 82 meets the primary-review threshold of 45.",
                "roadway_number": "SR2",
                "intersecting_road": "Oak",
                "city": "Testville",
                "county": "Example",
                "crash_id": "10",
                "crash_date": "2025-01-15",
                "crash_time": "13:45",
                "narrative": "Driver left roadway and struck curb.",
            },
            {
                "coordinate_recovery_group": "US24|PINE|ELSEWHERE|EXAMPLE",
                "coordinate_recovery_row_key": "12__row9",
                "coordinate_recovery_source_row": 9,
                "coordinate_recovery_group_size": 1,
                "coordinate_recovery_status": "no_match",
                "coordinate_recovery_confidence": "none",
                "coordinate_recovery_method": "",
                "coordinate_recovery_match_count": 0,
                "coordinate_recovery_candidate_count": 0,
                "coordinate_recovery_note": "No same-project coordinate match found.",
                "project_relevance_bucket": "secondary",
                "project_relevance_score": -22,
                "project_relevance_reason": "Route appears only outside the KMZ in rows with coordinates.",
                "project_relevance_details": "Decision rule: score -22 stays below the primary-review threshold of 45.",
                "roadway_number": "US24",
                "intersecting_road": "Pine",
                "city": "Elsewhere",
                "county": "Example",
                "crash_id": "12",
                "description": "No narrative captured.",
            },
        ]
    )

    assert [step["rowKey"] for step in steps] == ["10__row4", "12__row9"]
    assert steps[0]["reviewBucket"] == "primary"
    assert steps[0]["title"] == "SR2"
    assert steps[0]["detail"] == "At OAK | TESTVILLE / EXAMPLE"
    assert steps[0]["hasNarrative"] is True
    assert steps[0]["narrative"] == "Driver left roadway and struck curb."
    assert steps[0]["suggestedInsideBoundary"] is True
    assert steps[0]["crashDate"] == "2025-01-15"
    assert steps[0]["crashTime"] == "13:45"
    assert steps[1]["reviewBucket"] == "secondary"
    assert steps[1]["hasSuggestion"] is False
    assert steps[1]["hasNarrative"] is True


def test_review_builders_hide_outside_boundary_origin_suggestions() -> None:
    rows = [
        {
            "coordinate_recovery_group": "US41|MAPLEWOOD|HIGHLAND|LAKE",
            "coordinate_recovery_row_key": "903514070__row1653",
            "coordinate_recovery_source_row": 1653,
            "coordinate_recovery_group_size": 3,
            "coordinate_recovery_status": "review_required",
            "coordinate_recovery_confidence": "medium",
            "coordinate_recovery_method": "intersection_match",
            "coordinate_recovery_match_count": 13,
            "coordinate_recovery_candidate_count": 8,
            "coordinate_recovery_note": "Top candidate is outside the KMZ boundary.",
            "suggested_latitude": "0.0",
            "suggested_longitude": "0.0",
            "suggested_inside_boundary": "no",
            "project_relevance_bucket": "primary",
            "project_relevance_score": 47,
            "project_relevance_reason": "Route/intersection pattern matches rows that already fall inside the KMZ.",
            "roadway_number": "US41",
            "intersecting_road": "Maplewood",
            "city": "Highland",
            "county": "Lake",
            "crash_id": "903514070",
        }
    ]

    queue = build_coordinate_review_queue(rows)
    steps = build_coordinate_review_wizard_steps(rows)

    assert queue[0]["hasSuggestion"] is False
    assert queue[0]["suggestedLatitude"] is None
    assert queue[0]["suggestedLongitude"] is None
    assert steps[0]["hasSuggestion"] is False
    assert steps[0]["suggestedLatitude"] is None
    assert steps[0]["suggestedLongitude"] is None
    assert steps[0]["suggestedInsideBoundary"] is None


def test_recover_missing_coordinates_applies_row_level_reject_decision() -> None:
    rows = [
        {
            "Crash ID": "1",
            "Latitude": "40.0000",
            "Longitude": "-86.0000",
            "Roadway Number": "SR2",
            "Intersecting Road": "Oak",
            "City": "Testville",
            "County": "Example",
        },
        {
            "Crash ID": "2",
            "Latitude": "40.0006",
            "Longitude": "-86.0000",
            "Roadway Number": "SR2",
            "Intersecting Road": "Oak",
            "City": "Testville",
            "County": "Example",
        },
        {
            "Crash ID": "3",
            "Latitude": "",
            "Longitude": "",
            "Roadway Number": "SR2",
            "Intersecting Road": "Oak",
            "City": "Testville",
            "County": "Example",
        },
    ]

    output_rows, review_rows, report = recover_missing_coordinates(
        rows,
        latitude_column="Latitude",
        longitude_column="Longitude",
        review_decisions={
            "3__row4": CoordinateReviewDecision(
                group_key="3__row4",
                action="reject",
                note="Outside the project after manual review.",
            )
        },
    )

    assert report.missing_rows == 1
    assert report.rejected_rows == 1
    assert report.approved_rows == 0
    assert report.review_rows == 0
    assert review_rows == []

    rejected_row = next(row for row in output_rows if row["crash_id"] == "3")
    assert rejected_row["coordinate_recovery_row_key"] == "3__row4"
    assert rejected_row["coordinate_source"] == "review_rejected"
    assert rejected_row["coordinate_recovery_status"] == "review_rejected"
    assert rejected_row["coordinate_recovery_confidence"] == "user_rejected"
    assert rejected_row["coordinate_recovery_note"] == "Outside the project after manual review."
