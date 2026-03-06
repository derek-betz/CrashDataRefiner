"""Shared column-name normalization and coordinate-header inference helpers.

These utilities are used by the refinement pipeline, the web app, and any other
surface that needs to interpret crash data column names in a consistent way.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple


def normalize_header(header: str) -> str:
    """Convert a column header to ``snake_case`` suitable for programmatic access."""
    cleaned = re.sub(r"[^0-9a-zA-Z]+", "_", header.strip().lower())
    cleaned = re.sub(r"_{2,}", "_", cleaned)
    return cleaned.strip("_")


def _score_lat_header(header: str) -> int:
    norm = normalize_header(header)
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
    norm = normalize_header(header)
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


def guess_lat_lon_columns(headers: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """Return the best-guess latitude and longitude column names from *headers*.

    Returns ``(lat_column, lon_column)`` where either value may be ``None`` if
    no plausible candidate is found.
    """
    scored_lat = [(_score_lat_header(h), h) for h in headers]
    lat_choice = max(scored_lat, default=(0, None))
    scored_lon = [(_score_lon_header(h), h) for h in headers]
    lon_choice = max(scored_lon, default=(0, None))
    lat = lat_choice[1] if lat_choice[0] > 0 else None
    lon = lon_choice[1] if lon_choice[0] > 0 else None
    return lat, lon
