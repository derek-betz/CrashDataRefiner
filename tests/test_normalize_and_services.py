"""Tests for the shared normalize and services modules."""
from __future__ import annotations

from pathlib import Path
import zipfile

from crash_data_refiner.normalize import normalize_header, guess_lat_lon_columns
from crash_data_refiner.services import (
    refined_output_path,
    invalid_output_path,
    kmz_output_path,
    pdf_output_path,
    build_output_headers,
    order_and_number_rows,
    run_refinement_pipeline,
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


# ---------------------------------------------------------------------------
# normalize_header
# ---------------------------------------------------------------------------


def test_normalize_header_basic() -> None:
    assert normalize_header("Crash ID") == "crash_id"
    assert normalize_header("Crash Date") == "crash_date"
    assert normalize_header("  Hit and Run  ") == "hit_and_run"


def test_normalize_header_special_chars() -> None:
    assert normalize_header("Lat/Long") == "lat_long"
    assert normalize_header("__foo__") == "foo"


# ---------------------------------------------------------------------------
# guess_lat_lon_columns
# ---------------------------------------------------------------------------


def test_guess_lat_lon_exact_match() -> None:
    lat, lon = guess_lat_lon_columns(["Crash ID", "Latitude", "Longitude", "City"])
    assert lat == "Latitude"
    assert lon == "Longitude"


def test_guess_lat_lon_short_names() -> None:
    lat, lon = guess_lat_lon_columns(["lat", "lon"])
    assert lat == "lat"
    assert lon == "lon"


def test_guess_lat_lon_no_match() -> None:
    lat, lon = guess_lat_lon_columns(["Crash ID", "City"])
    assert lat is None
    assert lon is None


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def test_refined_output_path(tmp_path: Path) -> None:
    p = refined_output_path(tmp_path, "crashes.csv")
    assert p == tmp_path / "crashes_refined.csv"


def test_refined_output_path_xlsx(tmp_path: Path) -> None:
    p = refined_output_path(tmp_path, "data.xlsx")
    assert p == tmp_path / "data_refined.xlsx"


def test_invalid_output_path(tmp_path: Path) -> None:
    base = tmp_path / "crashes_refined.csv"
    p = invalid_output_path(base)
    assert p.name == "Crashes Without Valid Lat-Long Data.csv"


def test_kmz_output_path_strips_refined(tmp_path: Path) -> None:
    base = tmp_path / "crashes_refined.csv"
    p = kmz_output_path(base)
    assert p.name == "crashes_Crash Data.kmz"


def test_pdf_output_path_strips_refined(tmp_path: Path) -> None:
    base = tmp_path / "crashes_refined.csv"
    p = pdf_output_path(base)
    assert p.name == "crashes_Crash Data Full Report.pdf"


# ---------------------------------------------------------------------------
# build_output_headers
# ---------------------------------------------------------------------------


def test_build_output_headers_kmz_label_first() -> None:
    rows = [{"kmz_label": 1, "b": 2, "a": 3}]
    headers = build_output_headers(rows)
    assert headers[0] == "kmz_label"
    assert sorted(headers[1:]) == sorted(["a", "b"])


def test_build_output_headers_no_kmz_label() -> None:
    rows = [{"b": 1, "a": 2}]
    headers = build_output_headers(rows)
    assert headers == ["a", "b"]


# ---------------------------------------------------------------------------
# order_and_number_rows
# ---------------------------------------------------------------------------


def test_order_south_to_north() -> None:
    rows = [
        {"lat": "40.0", "lon": "-100.0"},
        {"lat": "30.0", "lon": "-100.0"},
        {"lat": "35.0", "lon": "-100.0"},
    ]
    ordered = order_and_number_rows(rows, lat_column="lat", lon_column="lon", label_order="south_to_north")
    lats = [float(r["lat"]) for r in ordered]
    assert lats == sorted(lats)
    assert [r["kmz_label"] for r in ordered] == [1, 2, 3]


def test_order_west_to_east() -> None:
    rows = [
        {"lat": "35.0", "lon": "-90.0"},
        {"lat": "35.0", "lon": "-110.0"},
        {"lat": "35.0", "lon": "-100.0"},
    ]
    ordered = order_and_number_rows(rows, lat_column="lat", lon_column="lon", label_order="west_to_east")
    lons = [float(r["lon"]) for r in ordered]
    assert lons == sorted(lons)


# ---------------------------------------------------------------------------
# run_refinement_pipeline integration
# ---------------------------------------------------------------------------


def _write_test_kmz(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("doc.kml", _UNIT_KML)


def test_run_refinement_pipeline(tmp_path: Path) -> None:
    import csv

    # Write a small crash CSV with one point inside and one outside the boundary.
    data_file = tmp_path / "crashes.csv"
    with data_file.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Crash ID", "Lat", "Lon"])
        writer.writeheader()
        writer.writerow({"Crash ID": "1", "Lat": "1.0", "Lon": "0.0"})   # inside
        writer.writerow({"Crash ID": "2", "Lat": "5.0", "Lon": "0.0"})   # outside

    kmz_file = tmp_path / "boundary.kmz"
    _write_test_kmz(kmz_file)

    run_dir = tmp_path / "run_001"
    result = run_refinement_pipeline(
        data_path=data_file,
        kmz_path=kmz_file,
        run_dir=run_dir,
        lat_column="Lat",
        lon_column="Lon",
    )

    assert result.boundary_report.included_rows == 1
    assert result.boundary_report.excluded_rows == 1
    assert result.output_path.exists()
    assert result.kmz_path.exists()
    assert result.kmz_count == 1
