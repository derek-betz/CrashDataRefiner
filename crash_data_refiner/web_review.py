"""Coordinate-review helpers for the Flask web surface."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .coordinate_recovery import (
    CoordinateReviewDecision,
    build_coordinate_review_queue,
    build_coordinate_review_wizard_steps,
)
from .geo import is_usable_coordinate_pair, load_kmz_polygon, parse_coordinate
from .normalize import normalize_header
from .output_paths import coordinate_review_output_path, refined_output_path
from .spreadsheets import read_spreadsheet


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
    refined_data = read_spreadsheet(str(refined_path))
    lat_key = normalize_header(lat_column)
    lon_key = normalize_header(lon_column)
    points: List[List[float]] = []
    for row in refined_data.rows:
        lat = parse_coordinate(row.get(lat_key))
        lon = parse_coordinate(row.get(lon_key))
        if not is_usable_coordinate_pair(lat, lon):
            continue
        points.append([lat, lon])

    return {
        "polygon": polygon_to_leaflet(boundary),
        "points": points,
        "pointCount": len(points),
    }


def load_review_wizard_for_state(state: Any) -> Dict[str, Any]:
    review_path = resolve_coordinate_review_path(state)
    if review_path is None:
        return {
            "primarySteps": [],
            "secondarySteps": [],
            "mapData": None,
        }

    data = read_spreadsheet(str(review_path))
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
