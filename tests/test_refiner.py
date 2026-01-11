from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crash_data_refiner.cli import main as cli_main
from crash_data_refiner.refiner import CrashDataRefiner, RefinementConfig


def test_refine_rows_normalizes_and_filters(tmp_path: Path) -> None:
    config = RefinementConfig(
        required_columns=["Crash ID", "Crash Date"],
        date_columns=["Crash Date"],
        integer_columns=["Fatalities"],
        float_columns=["Serious Injuries"],
        boolean_columns=["Hit and Run"],
        dedupe_on=["Crash ID"],
        fill_defaults={"City": "Unknown"},
    )

    refiner = CrashDataRefiner(config)
    input_rows = [
        {
            "Crash ID": "1001",
            "Crash Date": "2024-01-04",
            "Fatalities": "1",
            "Serious Injuries": "0",
            "City": "Springfield",
            "Hit and Run": "Yes",
        },
        {
            "Crash ID": "1002",
            "Crash Date": "01/05/2024",
            "Fatalities": "0",
            "Serious Injuries": "1",
            "City": "Shelbyville",
            "Hit and Run": "No",
        },
        {
            "Crash ID": "1003",
            "Crash Date": "2024-01-06",
            "Fatalities": "",
            "Serious Injuries": "2",
            "City": "",
            "Hit and Run": "Yes",
        },
        {
            "Crash ID": "",  # Missing required column
            "Crash Date": "2024-01-07",
        },
        {
            "Crash ID": "1001",  # Duplicate
            "Crash Date": "2024-01-04",
            "Fatalities": "1",
            "Serious Injuries": "0",
            "City": "Springfield",
            "Hit and Run": "Yes",
        },
    ]

    refined_rows, report = refiner.refine_rows(input_rows)

    assert report.total_rows == 5
    assert report.kept_rows == 3
    assert report.dropped_missing_required == 1
    assert report.dropped_duplicates == 1
    assert report.coerced_dates == 1  # One non-ISO date
    assert report.coerced_numbers >= 1
    assert report.coerced_booleans == 3

    assert refined_rows[0]["crash_id"] == "1001"
    assert refined_rows[1]["crash_date"] == "2024-01-05"
    assert refined_rows[2]["fatalities"] is None
    assert refined_rows[2]["city"] == "Unknown"
    assert refined_rows[0]["hit_and_run"] is True
    assert refined_rows[1]["hit_and_run"] is False


def test_refine_file_writes_csv(tmp_path: Path) -> None:
    config = RefinementConfig(
        required_columns=["Crash ID", "Crash Date"],
        date_columns=["Crash Date"],
        integer_columns=["Fatalities"],
        float_columns=["Serious Injuries"],
        boolean_columns=["Hit and Run"],
        dedupe_on=["Crash ID"],
    )
    refiner = CrashDataRefiner(config)

    raw_path = Path("tests/data/raw_crashes.csv")
    output_path = tmp_path / "refined.csv"

    report = refiner.refine_file(str(raw_path), str(output_path))

    assert report.total_rows == 4
    assert report.kept_rows == 3
    assert report.dropped_duplicates == 1

    contents = output_path.read_text().strip().splitlines()
    assert contents[0] == "city,crash_date,crash_id,fatalities,hit_and_run,serious_injuries"
    assert "Springfield" in contents[1]


def test_cli_round_trip(tmp_path: Path) -> None:
    raw = Path("tests/data/raw_crashes.csv")
    output = tmp_path / "refined.csv"

    args = [
        str(raw),
        str(output),
        "--required-columns",
        "Crash ID,Crash Date",
        "--date-columns",
        "Crash Date",
        "--integer-columns",
        "Fatalities",
        "--float-columns",
        "Serious Injuries",
        "--boolean-columns",
        "Hit and Run",
        "--dedupe-on",
        "Crash ID",
    ]

    # The CLI prints JSON to stdout. We simply ensure it exits successfully and
    # produces an output file.
    exit_code = cli_main(args)
    assert exit_code == 0
    assert output.exists()


def test_refine_rows_standardizes_crash_type_and_route() -> None:
    refiner = CrashDataRefiner()
    refined_rows, report = refiner.refine_rows(
        [
            {
                "Crash Type": "rear-end",
                "Route": " N St. Rd. 127 ",
                "Intersecting Road Name": "W Broad St",
                "Roadway Name": "Broad",
                "Roadway ID": "State Road 4",
            },
            {
                "Route": "IN 127",
                "Intersecting Road Name": "Broad",
                "Roadway Name": "Broad St",
            },
        ]
    )

    assert report.total_rows == 2
    assert refined_rows[0]["crash_type"] == "Rear End"
    assert refined_rows[0]["route"] == "SR 127"
    assert refined_rows[1]["route"] == "SR 127"
    assert refined_rows[0]["intersecting_road_name"] == "BROAD ST"
    assert refined_rows[1]["intersecting_road_name"] == "BROAD ST"
    assert refined_rows[0]["roadway_name"] == "BROAD ST"
    assert refined_rows[1]["roadway_name"] == "BROAD ST"
    assert refined_rows[0]["roadway_id"] == "SR 4"
