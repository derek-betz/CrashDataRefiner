"""Run the refiner against the latest inputs in tests/refiner_inputs."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from crash_data_refiner.geo import load_kmz_polygon, parse_coordinate
from crash_data_refiner.kmz_report import write_kmz_report
from crash_data_refiner.refiner import CrashDataRefiner, _normalize_header
from crash_data_refiner.spreadsheets import read_spreadsheet, write_spreadsheet
from crash_data_refiner.summary_report import generate_summary_report

SUPPORTED_SPREADSHEETS = {".csv", ".xlsx", ".xlsm"}
SUPPORTED_KMZ = {".kmz"}


def _score_lat_header(header: str) -> int:
    norm = _normalize_header(header)
    if norm in {"lat", "latitude"}:
        return 100
    if "latitude" in norm:
        return 90
    if norm.startswith("lat_") or norm.endswith("_lat"):
        return 80
    if norm in {"y", "y_coord", "y_coordinate"}:
        return 70
    if "lat" in norm:
        return 50
    return 0


def _score_lon_header(header: str) -> int:
    norm = _normalize_header(header)
    if norm in {"lon", "long", "longitude"}:
        return 100
    if "longitude" in norm:
        return 90
    if norm.startswith(("lon_", "long_")) or norm.endswith(("_lon", "_long")):
        return 80
    if norm in {"x", "x_coord", "x_coordinate"}:
        return 70
    if "lon" in norm or "long" in norm:
        return 50
    return 0


def _guess_lat_lon(headers: List[str]) -> Tuple[Optional[str], Optional[str]]:
    scored_lat = [(_score_lat_header(h), h) for h in headers]
    lat_choice = max(scored_lat, default=(0, None))
    scored_lon = [(_score_lon_header(h), h) for h in headers]
    lon_choice = max(scored_lon, default=(0, None))
    lat = lat_choice[1] if lat_choice[0] > 0 else None
    lon = lon_choice[1] if lon_choice[0] > 0 else None
    return lat, lon


def _order_and_number_rows(
    rows: List[Dict[str, Any]],
    *,
    lat_column: str,
    lon_column: str,
    label_order: str,
) -> List[Dict[str, Any]]:
    lat_key = _normalize_header(lat_column)
    lon_key = _normalize_header(lon_column)
    indexed: List[Tuple[Tuple[float, float, int] | Tuple[int], Dict[str, Any]]] = []

    for idx, row in enumerate(rows):
        lat = parse_coordinate(row.get(lat_key))
        lon = parse_coordinate(row.get(lon_key))
        if label_order == "south_to_north":
            lat_value = lat if lat is not None else float("inf")
            lon_value = lon if lon is not None else float("inf")
            key = (lat_value, lon_value, idx)
        elif label_order == "west_to_east":
            lon_value = lon if lon is not None else float("inf")
            lat_value = lat if lat is not None else float("inf")
            key = (lon_value, lat_value, idx)
        else:
            key = (idx,)
        indexed.append((key, row))

    indexed.sort(key=lambda item: item[0])
    ordered = [item[1] for item in indexed]
    for number, row in enumerate(ordered, start=1):
        row["kmz_label"] = number
    return ordered


def _build_output_headers(rows: List[Dict[str, Any]]) -> List[str]:
    header_set: set[str] = set()
    for row in rows:
        header_set.update(row.keys())
    headers = sorted(header_set)
    if "kmz_label" in headers:
        headers.remove("kmz_label")
        headers.insert(0, "kmz_label")
    return headers


def _refined_output_path(output_dir: Path, input_name: str) -> Path:
    input_file = Path(input_name)
    suffix = input_file.suffix or ".csv"
    return output_dir / f"{input_file.stem}_refined{suffix}"


def _invalid_output_path(output_path: Path) -> Path:
    return output_path.with_name(f"Crashes Without Valid Lat-Long Data{output_path.suffix}")


def _kmz_output_path(output_path: Path) -> Path:
    base_name = output_path.stem
    if base_name.lower().endswith("_refined"):
        base_name = base_name[:-8]
    return output_path.with_name(f"{base_name}_Crash Data.kmz")


def _summary_output_path(output_path: Path) -> Path:
    base_name = output_path.stem
    if base_name.lower().endswith("_refined"):
        base_name = base_name[:-8]
    return output_path.with_name(f"{base_name}_Crash Data Summary Report.pdf")


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
    lat_column, lon_column = _guess_lat_lon(data.headers)
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
    refined_rows = _order_and_number_rows(
        refined_rows,
        lat_column=lat_column,
        lon_column=lon_column,
        label_order=args.label_order,
    )

    output_path = _refined_output_path(output_dir, data_path.name)
    output_headers = _build_output_headers(refined_rows)
    write_spreadsheet(str(output_path), refined_rows, headers=output_headers)

    invalid_path = _invalid_output_path(output_path)
    write_spreadsheet(str(invalid_path), invalid_rows)

    kmz_output_path = _kmz_output_path(output_path)
    kmz_count = write_kmz_report(
        str(kmz_output_path),
        rows=refined_rows,
        latitude_column=lat_column,
        longitude_column=lon_column,
        label_order=args.label_order,
    )

    summary_output_path = _summary_output_path(output_path)
    generate_summary_report(
        str(summary_output_path),
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
