from __future__ import annotations

from pathlib import Path
import zipfile

from crash_data_refiner.geo import load_kmz_polygon
from crash_data_refiner.refiner import CrashDataRefiner


def _write_kmz(path: Path) -> None:
    kml = """<?xml version="1.0" encoding="UTF-8"?>
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
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("doc.kml", kml)


def test_kmz_polygon_filtering(tmp_path: Path) -> None:
    kmz_path = tmp_path / "boundary.kmz"
    _write_kmz(kmz_path)
    boundary = load_kmz_polygon(str(kmz_path))

    refiner = CrashDataRefiner()
    rows = [
        {"Lat": "1", "Lon": "0"},
        {"Lat": "3", "Lon": "0"},
        {"Lat": "", "Lon": "0"},
    ]

    included, excluded, invalid, report = refiner.filter_rows_by_boundary(
        rows,
        boundary=boundary,
        latitude_column="Lat",
        longitude_column="Lon",
    )

    assert report.total_rows == 3
    assert report.included_rows == 1
    assert report.excluded_rows == 1
    assert report.invalid_rows == 1
    assert len(included) == 1
    assert len(excluded) == 1
    assert len(invalid) == 1
