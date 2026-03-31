from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import zipfile

from crash_data_refiner.services import coordinate_review_output_path, refined_output_path
from crash_data_refiner.spreadsheets import write_spreadsheet
from crash_data_refiner.webapp import (
    RUNS,
    RUNS_LOCK,
    RunState,
    _parse_review_decisions_payload,
    app,
)


_UNIT_KML = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              -1,0 1,0 1,2 -1,2 -1,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>
"""


def _write_test_kmz(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("doc.kml", _UNIT_KML)


def test_parse_review_decisions_payload_accepts_row_level_apply_and_reject() -> None:
    payload = json.dumps(
        [
            {
                "rowKey": "3__row4",
                "action": "apply",
                "latitude": 1.0003,
                "longitude": 0.0,
                "note": "Confirmed manual map placement.",
            },
            {
                "rowKey": "4__row5",
                "action": "reject",
            },
        ]
    )

    decisions = _parse_review_decisions_payload(payload)

    assert set(decisions) == {"3__row4", "4__row5"}
    assert decisions["3__row4"].latitude == 1.0003
    assert decisions["3__row4"].longitude == 0.0
    assert decisions["3__row4"].action == "apply"
    assert decisions["3__row4"].note == "Confirmed manual map placement."
    assert decisions["4__row5"].action == "reject"
    assert decisions["4__row5"].latitude is None
    assert decisions["4__row5"].longitude is None
    assert decisions["4__row5"].note == "Rejected in browser review wizard."


def test_run_review_wizard_endpoint_returns_steps_and_map_data(tmp_path: Path) -> None:
    run_id = "wizardtest123"
    output_dir = tmp_path / run_id
    input_dir = output_dir / "inputs"
    input_dir.mkdir(parents=True)

    data_name = "crashes.csv"
    kmz_name = "boundary.kmz"
    _write_test_kmz(input_dir / kmz_name)

    refined_path = refined_output_path(output_dir, data_name)
    write_spreadsheet(
        str(refined_path),
        [
            {
                "crash_id": "1",
                "lat": 1.0,
                "lon": 0.0,
            }
        ],
    )

    review_path = coordinate_review_output_path(refined_path)
    write_spreadsheet(
        str(review_path),
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
                "suggested_latitude": 1.0003,
                "suggested_longitude": 0.0,
                "suggested_inside_boundary": True,
                "project_relevance_bucket": "primary",
                "project_relevance_score": 84,
                "project_relevance_reason": "Route/intersection pattern matches rows that already fall inside the KMZ.",
                "project_relevance_details": "Decision rule: score 84 meets the primary-review threshold of 45.\nRoute + cross street: SR2 at OAK appears in 2 inside-boundary and 0 outside-boundary known-coordinate crash(es) (100% inside).",
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
            },
        ],
    )

    state = RunState(run_id=run_id, created_at=datetime.now(timezone.utc), output_dir=output_dir)
    state.inputs = {
        "dataFile": data_name,
        "kmzFile": kmz_name,
        "latColumn": "Lat",
        "lonColumn": "Lon",
    }
    with RUNS_LOCK:
        RUNS[run_id] = state

    try:
        with app.test_client() as client:
            response = client.get(f"/api/run/{run_id}/review-wizard")
        assert response.status_code == 200
        data = response.get_json()
        assert data["primaryStepCount"] == 1
        assert data["secondaryStepCount"] == 1
        assert data["primarySteps"][0]["rowKey"] == "10__row4"
        assert data["primarySteps"][0]["hasNarrative"] is True
        assert data["primarySteps"][0]["narrative"] == "Driver left roadway and struck curb."
        assert data["primarySteps"][0]["reviewDetails"][0] == "Decision rule: score 84 meets the primary-review threshold of 45."
        assert data["secondarySteps"][0]["rowKey"] == "12__row9"
        assert data["mapData"]["pointCount"] == 1
        assert data["mapData"]["points"] == [[1.0, 0.0]]
        assert len(data["mapData"]["polygon"]) == 1
    finally:
        with RUNS_LOCK:
            RUNS.pop(run_id, None)
