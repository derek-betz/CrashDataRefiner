"""Run the refiner against the latest inputs in tests/refiner_inputs."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from crash_data_refiner.normalize import guess_lat_lon_columns
from crash_data_refiner.refiner import CrashDataRefiner
from crash_data_refiner.services import (
    build_output_headers,
    invalid_output_path,
    kmz_output_path,
    order_and_number_rows,
    refined_output_path,
    summary_output_path,
)
from crash_data_refiner.spreadsheets import read_spreadsheet, write_spreadsheet
from crash_data_refiner.kmz_report import write_kmz_report
from crash_data_refiner.geo import load_kmz_polygon
from crash_data_refiner.summary_report import generate_summary_report

SUPPORTED_SPREADSHEETS = {".csv", ".xlsx", ".xlsm"}
SUPPORTED_KMZ = {".kmz"}


def _pick_latest(paths: List[Path]) -> Path:
    if len(paths) == 1:
        return paths[0]
    return max(paths, key=lambda path: path.stat().st_mtime)


def _clear_output_dir(output_dir: Path, root: Path) -> None:
    resolved_output = output_dir.resolve()
    if resolved_output == root or root not in resolved_output.parents:
        raise SystemExit(f"Refusing to clear output outside repo root: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for entry in output_dir.iterdir():
        if entry.is_dir():
            for child in entry.rglob("*"):
                if child.is_file():
                    child.unlink()
            for child in sorted(entry.rglob("*"), reverse=True):
                if child.is_dir():
                    child.rmdir()
            entry.rmdir()
        else:
            entry.unlink()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run refiner using tests/refiner_inputs.")
    parser.add_argument(
        "--label-order",
        choices=("source", "west_to_east", "south_to_north"),
        default="west_to_east",
        help="KMZ label order (default: west_to_east).",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=None,
        help="Override input directory (defaults to tests/refiner_inputs).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Override output directory (defaults to tests/refiner_outputs).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    root = Path(__file__).resolve().parent.parent
    input_dir = args.input_dir or (root / "tests" / "refiner_inputs")
    output_dir = args.output_dir or (root / "tests" / "refiner_outputs")

    if not input_dir.exists():
        raise SystemExit(f"Input folder not found: {input_dir}")

    spreadsheets = [
        path for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_SPREADSHEETS
    ]
    kmz_files = [
        path for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_KMZ
    ]

    if not spreadsheets:
        raise SystemExit(f"No spreadsheet found in {input_dir}")
    if not kmz_files:
        raise SystemExit(f"No KMZ found in {input_dir}")

    data_path = _pick_latest(spreadsheets)
    kmz_path = _pick_latest(kmz_files)
    if len(spreadsheets) > 1:
        print(f"Multiple spreadsheets found; using newest: {data_path.name}")
    if len(kmz_files) > 1:
        print(f"Multiple KMZ files found; using newest: {kmz_path.name}")

    _clear_output_dir(output_dir, root)

    data = read_spreadsheet(str(data_path))
    lat_column, lon_column = guess_lat_lon_columns(data.headers)
    if not lat_column or not lon_column:
        raise SystemExit("Unable to infer latitude/longitude columns from headers.")

    boundary = load_kmz_polygon(str(kmz_path))
    refiner = CrashDataRefiner()
    refined_rows, report, boundary_report, invalid_rows = refiner.refine_rows_with_boundary(
        data.rows,
        boundary=boundary,
        latitude_column=lat_column,
        longitude_column=lon_column,
    )
    refined_rows = order_and_number_rows(
        refined_rows,
        lat_column=lat_column,
        lon_column=lon_column,
        label_order=args.label_order,
    )

    output_path = refined_output_path(output_dir, data_path.name)
    output_headers = build_output_headers(refined_rows)
    write_spreadsheet(str(output_path), refined_rows, headers=output_headers)

    invalid_path = invalid_output_path(output_path)
    write_spreadsheet(str(invalid_path), invalid_rows)

    kmz_out_path = kmz_output_path(output_path)
    kmz_count = write_kmz_report(
        str(kmz_out_path),
        rows=refined_rows,
        latitude_column=lat_column,
        longitude_column=lon_column,
        label_order=args.label_order,
    )

    summary_out_path = summary_output_path(output_path)
    generate_summary_report(
        str(summary_out_path),
        rows=refined_rows,
        latitude_column=lat_column,
        longitude_column=lon_column,
        boundary_report=boundary_report,
        source_name=data_path.name,
    )

    print("Refiner run complete.")
    print(f"Input: {data_path.name}")
    print(f"Boundary: {kmz_path.name}")
    print(f"Output rows: {report.output_rows}")
    print(f"Included: {boundary_report.included_rows}")
    print(f"Excluded: {boundary_report.excluded_rows}")
    print(f"Invalid: {boundary_report.invalid_rows}")
    print(f"KMZ placemarks: {kmz_count}")
    print(f"Outputs: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
