"""KMZ label-order detection and relabeling helpers."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .normalize import normalize_header


VALID_LABEL_ORDERS = {"auto", "west_to_east", "south_to_north"}


def detect_label_order(
    rows: List[Dict[str, Any]],
    *,
    lat_column: str,
    lon_column: str,
) -> str:
    """Return the dominant geographic direction for KMZ labels."""
    from .geo import parse_coordinate

    lat_key = normalize_header(lat_column)
    lon_key = normalize_header(lon_column)
    latitudes: List[float] = []
    longitudes: List[float] = []
    for row in rows:
        lat = parse_coordinate(row.get(lat_key))
        lon = parse_coordinate(row.get(lon_key))
        if lat is None or lon is None:
            continue
        latitudes.append(lat)
        longitudes.append(lon)

    if not latitudes or not longitudes:
        return "west_to_east"

    lat_span = max(latitudes) - min(latitudes)
    lon_span = max(longitudes) - min(longitudes)
    if lat_span > lon_span:
        return "south_to_north"
    return "west_to_east"


def resolve_label_order(
    rows: List[Dict[str, Any]],
    *,
    lat_column: str,
    lon_column: str,
    label_order: str,
) -> str:
    """Resolve ``label_order`` to an explicit geographic direction."""
    normalized = (label_order or "auto").strip().lower()
    if normalized == "south_to_north":
        return "south_to_north"
    if normalized == "west_to_east":
        return "west_to_east"
    return detect_label_order(rows, lat_column=lat_column, lon_column=lon_column)


def order_and_number_rows(
    rows: List[Dict[str, Any]],
    *,
    lat_column: str,
    lon_column: str,
    label_order: str,
) -> List[Dict[str, Any]]:
    """Sort *rows* by geographic order and assign sequential ``kmz_label`` values."""
    from .geo import parse_coordinate

    resolved_order = resolve_label_order(
        rows,
        lat_column=lat_column,
        lon_column=lon_column,
        label_order=label_order,
    )
    lat_key = normalize_header(lat_column)
    lon_key = normalize_header(lon_column)
    indexed: List[Tuple[Any, Dict[str, Any]]] = []
    for idx, row in enumerate(rows):
        lat = parse_coordinate(row.get(lat_key))
        lon = parse_coordinate(row.get(lon_key))
        if resolved_order == "south_to_north":
            lat_value = lat if lat is not None else float("inf")
            lon_value = lon if lon is not None else float("inf")
            key: Any = (lat_value, lon_value, idx)
        else:
            lon_value = lon if lon is not None else float("inf")
            lat_value = lat if lat is not None else float("inf")
            key = (lon_value, lat_value, idx)
        indexed.append((key, row))

    indexed.sort(key=lambda item: item[0])
    ordered = [item[1] for item in indexed]
    for number, row in enumerate(ordered, start=1):
        row["kmz_label"] = number
    return ordered
