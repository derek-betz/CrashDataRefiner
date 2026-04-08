"""Coordinate-review helpers for the Flask web surface."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from zipfile import BadZipFile

from .coordinate_recovery import (
    CoordinateReviewDecision,
    build_coordinate_review_queue,
    build_coordinate_review_wizard_steps,
)
from .geo import is_usable_coordinate_pair, load_kmz_polygon, parse_coordinate
from .normalize import normalize_header
from .output_paths import coordinate_review_output_path, refined_output_path
from .spreadsheets import read_spreadsheet


_REVIEW_ID_KEYS = ("crash_id", "master_record_number", "local_code")
_REVIEW_ROUTE_KEYS = ("roadway_id", "road_number", "roadway_number", "route", "roadway_name", "road_name")
_REVIEW_CROSS_KEYS = (
    "intersecting_road_number",
    "intersection_number",
    "intersecting_road",
    "intersecting_road_name",
    "intersection_name",
)
_REVIEW_LOCALITY_KEYS = ("city", "township", "county")


def _normalize_review_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {normalize_header(key): value for key, value in row.items()}


def _first_review_text(row: Dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def _build_context_crash(row: Dict[str, Any], *, latitude: float, longitude: float) -> Dict[str, Any]:
    route = _first_review_text(row, _REVIEW_ROUTE_KEYS)
    cross = _first_review_text(row, _REVIEW_CROSS_KEYS)
    locality_parts = [part for part in (_first_review_text(row, (key,)) for key in _REVIEW_LOCALITY_KEYS) if part]
    locality = " / ".join(locality_parts)
    detail_parts = []
    if cross:
        detail_parts.append(f"At {cross}")
    if locality:
        detail_parts.append(locality)
    return {
        "latitude": latitude,
        "longitude": longitude,
        "crashId": _first_review_text(row, _REVIEW_ID_KEYS),
        "title": route or cross or "Refined crash",
        "detail": " | ".join(detail_parts) or "Refined crash inside the project boundary.",
    }


def resolve_coordinate_review_path(state: Any) -> Optional[Path]:
    if not state.output_dir:
        return None
    data_name = str((state.inputs or {}).get("dataFile") or "").strip()
    if not data_name:
        return None
    output_path = refined_output_path(state.output_dir, data_name)
    review_path = coordinate_review_output_path(output_path)
    if review_path.exists():
        return review_path
    return None


def load_review_queue_for_state(state: Any) -> List[Dict[str, Any]]:
    review_path = resolve_coordinate_review_path(state)
    if review_path is None:
        return []
    data = read_spreadsheet(str(review_path))
    return build_coordinate_review_queue(data.rows)


def polygon_to_leaflet(polygon: Any) -> List[List[List[float]]]:
    outer = [[lat, lon] for lon, lat in polygon.outer]
    holes = [[[lat, lon] for lon, lat in ring] for ring in polygon.holes]
    if holes:
        return [outer, *holes]
    return [outer]


def load_review_map_data_for_state(state: Any) -> Optional[Dict[str, Any]]:
    if not state.output_dir:
        return None

    inputs = dict(state.inputs or {})
    data_name = str(inputs.get("dataFile") or "").strip()
    kmz_name = str(inputs.get("kmzFile") or "").strip()
    lat_column = str(inputs.get("latColumn") or "").strip()
    lon_column = str(inputs.get("lonColumn") or "").strip()
    if not data_name or not kmz_name or not lat_column or not lon_column:
        return None

    input_dir = state.output_dir / "inputs"
    kmz_path = input_dir / kmz_name
    refined_path = refined_output_path(state.output_dir, data_name)
    if not kmz_path.exists() or not refined_path.exists():
        return None

    boundary = load_kmz_polygon(str(kmz_path))
    try:
        refined_data = read_spreadsheet(str(refined_path))
    except (BadZipFile, OSError, ValueError):
        return None
    lat_key = normalize_header(lat_column)
    lon_key = normalize_header(lon_column)
    points: List[List[float]] = []
    context_crashes: List[Dict[str, Any]] = []
    for row in refined_data.rows:
        normalized_row = _normalize_review_row(row)
        lat = parse_coordinate(normalized_row.get(lat_key))
        lon = parse_coordinate(normalized_row.get(lon_key))
        if not is_usable_coordinate_pair(lat, lon):
            continue
        points.append([lat, lon])
        context_crashes.append(_build_context_crash(normalized_row, latitude=lat, longitude=lon))

    return {
        "polygon": polygon_to_leaflet(boundary),
        "points": points,
        "pointCount": len(points),
        "contextCrashes": context_crashes,
    }


def load_review_wizard_for_state(state: Any) -> Dict[str, Any]:
    review_path = resolve_coordinate_review_path(state)
    if review_path is None:
        return {
            "primarySteps": [],
            "secondarySteps": [],
            "mapData": None,
        }

    try:
        data = read_spreadsheet(str(review_path))
    except (BadZipFile, OSError, ValueError):
        return {
            "primarySteps": [],
            "secondarySteps": [],
            "mapData": load_review_map_data_for_state(state),
        }
    steps = build_coordinate_review_wizard_steps(data.rows)
    primary_steps = [
        step for step in steps
        if str(step.get("reviewBucket") or "primary") != "secondary"
    ]
    secondary_steps = [
        step for step in steps
        if str(step.get("reviewBucket") or "primary") == "secondary"
    ]
    return {
        "primarySteps": primary_steps,
        "secondarySteps": secondary_steps,
        "mapData": load_review_map_data_for_state(state),
    }


def parse_review_decisions_payload(text: str) -> Dict[str, CoordinateReviewDecision]:
    if not text.strip():
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Review decisions must be valid JSON.") from exc

    if not isinstance(payload, list):
        raise ValueError("Review decisions must be a JSON array.")

    decisions: Dict[str, CoordinateReviewDecision] = {}
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Review decision #{index} must be an object.")
        group_key = str(item.get("rowKey") or item.get("groupKey") or "").strip()
        action = str(item.get("action") or "apply").strip().lower()
        latitude = parse_coordinate(item.get("latitude"))
        longitude = parse_coordinate(item.get("longitude"))
        note = str(item.get("note") or "").strip()
        if not group_key:
            raise ValueError(f"Review decision #{index} must include rowKey or groupKey.")
        if action not in {"apply", "reject"}:
            raise ValueError(f"Review decision #{index} action must be 'apply' or 'reject'.")
        if action == "apply" and not is_usable_coordinate_pair(latitude, longitude):
            raise ValueError(
                f"Review decision #{index} must include usable latitude and longitude for applied placements."
            )
        existing = decisions.get(group_key)
        if existing and (
            existing.action != action
            or (
                action == "apply"
                and (
                    existing.latitude is None
                    or existing.longitude is None
                    or latitude is None
                    or longitude is None
                    or abs(existing.latitude - latitude) > 1e-6
                    or abs(existing.longitude - longitude) > 1e-6
                )
            )
        ):
            raise ValueError(f"Review group '{group_key}' contains conflicting browser decisions.")
        decisions[group_key] = CoordinateReviewDecision(
            group_key=group_key,
            latitude=latitude,
            longitude=longitude,
            action=action,
            note=note or (
                "Excluded from project in browser review workbench."
                if action == "reject"
                else "Applied from browser review workbench."
            ),
        )
    return decisions
