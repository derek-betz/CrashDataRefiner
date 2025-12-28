"""Geospatial helpers for CrashDataRefiner."""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Iterable, List, Sequence, Tuple
import xml.etree.ElementTree as ET
import zipfile


Coordinate = Tuple[float, float]  # (lon, lat)


@dataclass(frozen=True)
class PolygonBoundary:
    """Polygon boundary with optional interior holes."""

    outer: List[Coordinate]
    holes: List[List[Coordinate]] = field(default_factory=list)

    @property
    def bbox(self) -> Tuple[float, float, float, float]:
        lons = [coord[0] for coord in self.outer]
        lats = [coord[1] for coord in self.outer]
        return min(lons), min(lats), max(lons), max(lats)


@dataclass(frozen=True)
class BoundaryFilterReport:
    total_rows: int
    included_rows: int
    excluded_rows: int
    invalid_rows: int


def load_kmz_polygon(path: str) -> PolygonBoundary:
    """Load a single polygon boundary from a KMZ file."""
    kml_text = _read_kml_from_kmz(path)
    polygons = _parse_kml_polygons(kml_text)
    if not polygons:
        raise ValueError("No polygon found in KMZ.")
    if len(polygons) > 1:
        raise ValueError("KMZ contains multiple polygons; only one is supported.")
    return polygons[0]


def _read_kml_from_kmz(path: str) -> str:
    with zipfile.ZipFile(path, "r") as archive:
        candidates = [name for name in archive.namelist() if name.lower().endswith(".kml")]
        if not candidates:
            raise ValueError("KMZ does not contain a KML file.")
        with archive.open(candidates[0], "r") as handle:
            return handle.read().decode("utf-8")


def _parse_kml_polygons(kml_text: str) -> List[PolygonBoundary]:
    root = ET.fromstring(kml_text)
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0].lstrip("{")

    def _findall(element: ET.Element, tag: str) -> Iterable[ET.Element]:
        if ns:
            return element.findall(f".//{{{ns}}}{tag}")
        return element.findall(f".//{tag}")

    boundaries: List[PolygonBoundary] = []
    for polygon in _findall(root, "Polygon"):
        outer = _parse_ring(polygon, "outerBoundaryIs", ns)
        if not outer:
            continue
        holes = [_ring for _ring in _parse_holes(polygon, ns) if _ring]
        boundaries.append(PolygonBoundary(outer=outer, holes=holes))
    return boundaries


def _parse_ring(polygon: ET.Element, ring_tag: str, namespace: str) -> List[Coordinate]:
    ring = polygon.find(f".//{{{namespace}}}{ring_tag}" if namespace else f".//{ring_tag}")
    if ring is None:
        return []
    coords = ring.find(f".//{{{namespace}}}coordinates" if namespace else ".//coordinates")
    if coords is None or not coords.text:
        return []
    return _parse_coordinates(coords.text)


def _parse_holes(polygon: ET.Element, namespace: str) -> List[List[Coordinate]]:
    holes: List[List[Coordinate]] = []
    for ring in polygon.findall(f".//{{{namespace}}}innerBoundaryIs" if namespace else ".//innerBoundaryIs"):
        coords = ring.find(f".//{{{namespace}}}coordinates" if namespace else ".//coordinates")
        if coords is None or not coords.text:
            continue
        holes.append(_parse_coordinates(coords.text))
    return holes


def _parse_coordinates(text: str) -> List[Coordinate]:
    coords: List[Coordinate] = []
    for token in text.replace("\n", " ").split():
        parts = token.split(",")
        if len(parts) < 2:
            continue
        try:
            lon = float(parts[0])
            lat = float(parts[1])
        except ValueError:
            continue
        coords.append((lon, lat))
    if coords and coords[0] != coords[-1]:
        coords.append(coords[0])
    return coords


def parse_coordinate(value: Any) -> float | None:
    """Parse a coordinate value into a float, if possible."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if not re.fullmatch(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", text):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def point_in_polygon(lon: float, lat: float, polygon: PolygonBoundary) -> bool:
    min_lon, min_lat, max_lon, max_lat = polygon.bbox
    if lon < min_lon or lon > max_lon or lat < min_lat or lat > max_lat:
        return False
    if not _point_in_ring(lon, lat, polygon.outer):
        return False
    for hole in polygon.holes:
        if _point_in_ring(lon, lat, hole):
            return False
    return True


def _point_in_ring(lon: float, lat: float, ring: Sequence[Coordinate]) -> bool:
    inside = False
    if len(ring) < 3:
        return False
    for idx in range(len(ring) - 1):
        x1, y1 = ring[idx]
        x2, y2 = ring[idx + 1]
        intersects = ((y1 > lat) != (y2 > lat)) and (
            lon < (x2 - x1) * (lat - y1) / (y2 - y1 + 1e-12) + x1
        )
        if intersects:
            inside = not inside
    return inside
