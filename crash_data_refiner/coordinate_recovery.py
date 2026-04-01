"""Same-project coordinate recovery for crash rows missing latitude/longitude."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
import math
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .geo import PolygonBoundary, is_usable_coordinate_pair, parse_coordinate, point_in_polygon
from .normalize import normalize_header
from .refiner import _standardize_route


Coordinate = Tuple[float, float]  # (lat, lon)
_IDENTIFIER_KEYS: Tuple[str, ...] = (
    "crash_id",
    "master_record_number",
    "local_code",
)

MODE_ORDER: Tuple[str, ...] = (
    "offset_match",
    "intersection_match",
    "mile_marker_match",
    "unique_location_match",
)

MODE_LABELS: Dict[str, str] = {
    "offset_match": "offset match",
    "intersection_match": "intersection match",
    "mile_marker_match": "mile marker match",
    "unique_location_match": "unique location match",
}

MODE_CLUSTER_DISTANCE_FEET: Dict[str, float] = {
    "offset_match": 250.0,
    "intersection_match": 100.0,
    "mile_marker_match": 150.0,
    "unique_location_match": 100.0,
}

MODE_REVIEW_DISTANCE_FEET: Dict[str, float] = {
    "offset_match": 600.0,
    "intersection_match": 300.0,
    "mile_marker_match": 400.0,
    "unique_location_match": 300.0,
}

MODE_HIGH_SHARE: Dict[str, float] = {
    "offset_match": 0.75,
    "intersection_match": 0.85,
    "mile_marker_match": 0.85,
    "unique_location_match": 0.90,
}

_ROUTE_ID_KEYS: Tuple[str, ...] = (
    "roadway_id",
    "road_number",
    "roadway_number",
    "route",
)
_ROUTE_NAME_KEYS: Tuple[Tuple[str, str], ...] = (
    ("roadway_name", "roadway_suffix"),
    ("road_name", "road_suffix"),
)
_HOUSE_NUMBER_KEYS: Tuple[str, ...] = (
    "roadway_house_number",
    "house_number",
)
_CROSS_KEYS: Tuple[str, ...] = (
    "intersecting_road_number",
    "intersection_number",
    "intersecting_road",
    "intersecting_road_name",
    "intersection_name",
)
_MILE_MARKER_KEYS: Tuple[str, ...] = (
    "mile_marker",
    "intersecting_road_mile_marker",
    "intersection_mile_marker",
)
_FEET_KEYS: Tuple[str, ...] = (
    "feet_from",
    "feet_from_point",
)
_DIRECTION_KEYS: Tuple[str, ...] = (
    "direction",
    "direction_from",
    "direction_from_point_code",
)
_LOCALITY_KEYS: Tuple[str, ...] = (
    "city",
    "township",
    "county",
)
_DATE_KEYS: Tuple[str, ...] = (
    "crash_date",
    "date",
    "collision_date",
    "accident_date",
    "incident_date",
)
_TIME_KEYS: Tuple[str, ...] = (
    "crash_time",
    "time",
    "collision_time",
    "accident_time",
    "incident_time",
)
_NARRATIVE_KEYS: Tuple[str, ...] = (
    "narrative",
    "crash_narrative",
    "crash_narrative_text",
    "crash_report_narrative",
    "report_narrative",
    "narrative_text",
    "description",
    "summary",
    "remarks",
    "notes",
    "comment",
    "comments",
    "statement",
)

PROJECT_RELEVANCE_PRIMARY_SCORE = 45
PROJECT_RELEVANCE_MIN_INSIDE_ROWS = 10
PROJECT_RELEVANCE_BUCKET_PRIMARY = "primary"
PROJECT_RELEVANCE_BUCKET_SECONDARY = "secondary"


@dataclass(frozen=True)
class CoordinateRecoveryReport:
    missing_rows: int
    recovered_rows: int
    approved_rows: int
    rejected_rows: int
    review_rows: int
    suggested_rows: int
    primary_review_rows: int = 0
    secondary_review_rows: int = 0
    recovered_by_method: Dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class CoordinateReviewDecision:
    group_key: str
    latitude: float | None = None
    longitude: float | None = None
    action: str = "apply"
    note: str = ""


@dataclass(frozen=True)
class _RecoverySuggestion:
    method: str
    fingerprint: str
    latitude: float
    longitude: float
    matched_rows: int
    candidate_count: int
    confidence: str
    note: str
    inside_boundary: Optional[bool]
    priority: int


@dataclass(frozen=True)
class _ProjectRelevanceProfile:
    inside_rows: int
    dominant_locality: str
    inside_locality_counts: Counter[str]
    inside_route_counts: Counter[str]
    outside_route_counts: Counter[str]
    inside_cross_counts: Counter[str]
    outside_cross_counts: Counter[str]
    inside_pair_counts: Counter[str]
    outside_pair_counts: Counter[str]


@dataclass(frozen=True)
class _ProjectRelevanceAssessment:
    bucket: str
    score: int
    reason: str
    details: Tuple[str, ...] = ()


@dataclass(frozen=True)
class _ProjectRelevanceSignal:
    score: int
    reason: str
    detail: str


@dataclass
class _ClusterBuilder:
    total_count: int = 0
    weighted_lat: float = 0.0
    weighted_lon: float = 0.0
    members: List[Tuple[Coordinate, int]] = field(default_factory=list)

    @property
    def centroid(self) -> Coordinate:
        if self.total_count <= 0:
            return (0.0, 0.0)
        return (self.weighted_lat / self.total_count, self.weighted_lon / self.total_count)

    def accepts(self, coord: Coordinate, *, threshold_feet: float) -> bool:
        if not self.members:
            return True
        return _distance_feet(coord, self.centroid) <= threshold_feet

    def add(self, coord: Coordinate, count: int) -> None:
        self.total_count += count
        self.weighted_lat += coord[0] * count
        self.weighted_lon += coord[1] * count
        self.members.append((coord, count))

    def spread_feet(self) -> float:
        if len(self.members) < 2:
            return 0.0
        max_distance = 0.0
        points = [coord for coord, _count in self.members]
        for left_idx in range(len(points)):
            for right_idx in range(left_idx + 1, len(points)):
                max_distance = max(max_distance, _distance_feet(points[left_idx], points[right_idx]))
        return max_distance


def recover_missing_coordinates(
    rows: Iterable[Mapping[str, Any]],
    *,
    latitude_column: str,
    longitude_column: str,
    boundary: PolygonBoundary | None = None,
    review_decisions: Mapping[str, CoordinateReviewDecision] | None = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], CoordinateRecoveryReport]:
    """Recover missing coordinates from other rows in the same crash dataset.

    The function never calls external services. It only uses exact-location
    patterns found in rows that already have coordinates in the current input
    spreadsheet and adds audit metadata describing any recovery decision.
    """

    lat_key = normalize_header(latitude_column)
    lon_key = normalize_header(longitude_column)

    normalized_rows = [_normalize_row(row) for row in rows]
    evidence = _build_evidence(normalized_rows, lat_key=lat_key, lon_key=lon_key)
    relevance_profile = _build_project_relevance_profile(
        normalized_rows,
        lat_key=lat_key,
        lon_key=lon_key,
        boundary=boundary,
    )

    output_rows: List[Dict[str, Any]] = []
    review_rows: List[Dict[str, Any]] = []
    recovered_by_method: Counter[str] = Counter()
    missing_rows = 0
    approved_rows = 0
    rejected_rows = 0
    suggested_rows = 0
    decision_map = dict(review_decisions or {})

    for source_row_number, original_row in enumerate(normalized_rows, start=2):
        row = dict(original_row)
        lat = parse_coordinate(row.get(lat_key))
        lon = parse_coordinate(row.get(lon_key))
        if lat is not None and lon is not None:
            row["coordinate_source"] = "original"
            row["coordinate_recovery_status"] = "original"
            output_rows.append(row)
            continue

        missing_rows += 1
        group_key = _review_group_key(row) or ""
        row_key = _review_row_key(row, source_row_number=source_row_number)
        row["coordinate_recovery_group"] = group_key
        row["coordinate_recovery_row_key"] = row_key
        row["coordinate_recovery_source_row"] = source_row_number
        manual_decision = decision_map.get(row_key) or decision_map.get(group_key)
        if manual_decision is not None:
            decision_action = str(manual_decision.action or "apply").strip().lower()
            row["coordinate_recovery_method"] = "manual_review"
            row["coordinate_recovery_match_count"] = 0
            row["coordinate_recovery_candidate_count"] = 1
            if decision_action == "reject":
                row["coordinate_source"] = "review_rejected"
                row["coordinate_recovery_status"] = "review_rejected"
                row["coordinate_recovery_confidence"] = "user_rejected"
                row["coordinate_recovery_note"] = (
                    manual_decision.note or "Excluded from project in browser review workbench."
                )
                output_rows.append(row)
                rejected_rows += 1
                continue

            if manual_decision.latitude is None or manual_decision.longitude is None:
                raise ValueError(
                    f"Review decision for '{row_key}' is missing latitude/longitude coordinates."
                )

            row[lat_key] = round(manual_decision.latitude, 6)
            row[lon_key] = round(manual_decision.longitude, 6)
            row["coordinate_source"] = "review_approved"
            row["coordinate_recovery_status"] = "review_applied"
            row["coordinate_recovery_confidence"] = "user_approved"
            row["coordinate_recovery_note"] = (
                manual_decision.note or "Applied from approved coordinate review workflow."
            )
            output_rows.append(row)
            recovered_by_method["manual_review"] += 1
            approved_rows += 1
            continue

        suggestion = _select_suggestion(row, evidence=evidence, boundary=boundary)

        if suggestion and suggestion.confidence == "high":
            row[lat_key] = round(suggestion.latitude, 6)
            row[lon_key] = round(suggestion.longitude, 6)
            _apply_suggestion_metadata(row, suggestion, status="auto_recovered", group_key=group_key)
            row["coordinate_source"] = "recovered"
            output_rows.append(row)
            recovered_by_method[suggestion.method] += 1
            continue

        row["coordinate_source"] = "missing"
        if suggestion:
            _apply_suggestion_metadata(row, suggestion, status="review_required", group_key=group_key)
            if _is_surfaceable_review_suggestion(
                suggestion.latitude,
                suggestion.longitude,
                suggestion.inside_boundary,
            ):
                row["suggested_latitude"] = round(suggestion.latitude, 6)
                row["suggested_longitude"] = round(suggestion.longitude, 6)
                row["suggested_inside_boundary"] = suggestion.inside_boundary
                suggested_rows += 1
        else:
            row["coordinate_recovery_status"] = "no_match"
            row["coordinate_recovery_method"] = ""
            row["coordinate_recovery_confidence"] = "none"
            row["coordinate_recovery_match_count"] = 0
            row["coordinate_recovery_candidate_count"] = 0
            row["coordinate_recovery_note"] = "No same-project coordinate match found."
        row.setdefault("approve_for_group", "")
        row.setdefault("approved_latitude", "")
        row.setdefault("approved_longitude", "")
        row.setdefault("review_notes", "")
        relevance = _assess_project_relevance(
            row,
            profile=relevance_profile,
            suggestion=suggestion,
        )
        row["project_relevance_bucket"] = relevance.bucket
        row["project_relevance_score"] = relevance.score
        row["project_relevance_reason"] = relevance.reason
        row["project_relevance_details"] = "\n".join(relevance.details)
        review_rows.append(dict(row))
        output_rows.append(row)

    _apply_review_group_sizes(review_rows)
    primary_review_rows = sum(
        1
        for row in review_rows
        if str(row.get("project_relevance_bucket") or PROJECT_RELEVANCE_BUCKET_PRIMARY)
        != PROJECT_RELEVANCE_BUCKET_SECONDARY
    )
    secondary_review_rows = len(review_rows) - primary_review_rows
    review_rows.sort(
        key=lambda row: (
            0
            if str(row.get("project_relevance_bucket") or PROJECT_RELEVANCE_BUCKET_PRIMARY)
            != PROJECT_RELEVANCE_BUCKET_SECONDARY
            else 1,
            -int(row.get("coordinate_recovery_group_size") or 0),
            -int(row.get("project_relevance_score") or 0),
            str(row.get("coordinate_recovery_group") or ""),
            str(row.get("coordinate_recovery_status") or ""),
        )
    )

    report = CoordinateRecoveryReport(
        missing_rows=missing_rows,
        recovered_rows=sum(recovered_by_method.values()),
        approved_rows=approved_rows,
        rejected_rows=rejected_rows,
        review_rows=len(review_rows),
        suggested_rows=suggested_rows,
        primary_review_rows=primary_review_rows,
        secondary_review_rows=secondary_review_rows,
        recovered_by_method=dict(sorted(recovered_by_method.items())),
    )
    return output_rows, review_rows, report


def load_coordinate_review_decisions(
    rows: Iterable[Mapping[str, Any]],
) -> Dict[str, CoordinateReviewDecision]:
    """Parse approved group decisions from a coordinate review workbook."""

    decisions: Dict[str, CoordinateReviewDecision] = {}
    for raw_row in rows:
        row = _normalize_row(raw_row)
        group_key = str(row.get("coordinate_recovery_group") or "").strip()
        if not group_key:
            continue

        approved = _parse_review_boolean(row.get("approve_for_group"))
        approved_lat = parse_coordinate(row.get("approved_latitude"))
        approved_lon = parse_coordinate(row.get("approved_longitude"))
        suggested_lat = parse_coordinate(row.get("suggested_latitude"))
        suggested_lon = parse_coordinate(row.get("suggested_longitude"))
        suggested_inside_boundary = _parse_optional_bool(row.get("suggested_inside_boundary"))
        if not _is_surfaceable_review_suggestion(
            suggested_lat,
            suggested_lon,
            suggested_inside_boundary,
        ):
            suggested_lat = None
            suggested_lon = None

        if approved is False:
            continue

        if approved_lat is None and approved_lon is None and approved is None:
            continue

        if approved_lat is None:
            approved_lat = suggested_lat
        if approved_lon is None:
            approved_lon = suggested_lon

        if approved_lat is None or approved_lon is None:
            raise ValueError(
                f"Review group '{group_key}' is marked for approval but is missing approved coordinates."
            )

        note = str(row.get("review_notes") or row.get("coordinate_recovery_note") or "").strip()
        decision = CoordinateReviewDecision(
            group_key=group_key,
            latitude=approved_lat,
            longitude=approved_lon,
            action="apply",
            note=note,
        )
        existing = decisions.get(group_key)
        if existing and (
            abs(existing.latitude - decision.latitude) > 1e-6
            or abs(existing.longitude - decision.longitude) > 1e-6
        ):
            raise ValueError(f"Review group '{group_key}' contains conflicting approved coordinates.")
        if existing is None or (not existing.note and decision.note):
            decisions[group_key] = decision

    return decisions


def build_coordinate_review_queue(
    rows: Iterable[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Group review rows into UI-ready queue cards."""

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for raw_row in rows:
        row = _normalize_row(raw_row)
        group_key = str(row.get("coordinate_recovery_group") or "").strip()
        if not group_key:
            continue
        grouped[group_key].append(row)

    queue: List[Dict[str, Any]] = []
    for group_key, group_rows in grouped.items():
        first = group_rows[0]
        route = _route_text(first)
        cross = _cross_text(first)
        mile_marker = _mile_marker_text(first)
        direction = _direction_text(first)
        feet_from = _first_text(first, _FEET_KEYS)
        locality = _locality_text(first).replace("|", " / ")
        title = route or (mile_marker and f"Mile marker {mile_marker}") or group_key

        detail_parts: List[str] = []
        if cross:
            detail_parts.append(f"At {cross}")
        if mile_marker:
            detail_parts.append(f"Mile {mile_marker}")
        if feet_from:
            if direction:
                detail_parts.append(f"{feet_from} ft {direction}")
            else:
                detail_parts.append(f"{feet_from} ft from point")
        if locality:
            detail_parts.append(locality)

        sample_ids = [sample_id for sample_id in (_row_identifier(row) for row in group_rows) if sample_id][:3]
        suggested_lat = parse_coordinate(first.get("suggested_latitude"))
        suggested_lon = parse_coordinate(first.get("suggested_longitude"))
        suggested_inside_boundary = _parse_optional_bool(first.get("suggested_inside_boundary"))
        if not _is_surfaceable_review_suggestion(
            suggested_lat,
            suggested_lon,
            suggested_inside_boundary,
        ):
            suggested_lat = None
            suggested_lon = None
        group_size = int(first.get("coordinate_recovery_group_size") or len(group_rows))
        confidence = str(first.get("coordinate_recovery_confidence") or "none")
        review_bucket = str(first.get("project_relevance_bucket") or PROJECT_RELEVANCE_BUCKET_PRIMARY)
        review_score = int(first.get("project_relevance_score") or 0)

        queue.append(
            {
                "groupKey": group_key,
                "groupSize": group_size,
                "status": str(first.get("coordinate_recovery_status") or ""),
                "confidence": confidence,
                "method": str(first.get("coordinate_recovery_method") or ""),
                "matchCount": int(first.get("coordinate_recovery_match_count") or 0),
                "candidateCount": int(first.get("coordinate_recovery_candidate_count") or 0),
                "suggestedLatitude": suggested_lat,
                "suggestedLongitude": suggested_lon,
                "hasSuggestion": suggested_lat is not None and suggested_lon is not None,
                "title": title,
                "detail": " | ".join(detail_parts),
                "note": str(first.get("coordinate_recovery_note") or ""),
                "reviewBucket": review_bucket,
                "reviewScore": review_score,
                "reviewReason": str(first.get("project_relevance_reason") or ""),
                "reviewDetails": [
                    line.strip()
                    for line in str(first.get("project_relevance_details") or "").splitlines()
                    if line.strip()
                ],
                "sampleIds": sample_ids,
            }
        )

    queue.sort(
        key=lambda item: (
            0 if str(item["reviewBucket"]) != PROJECT_RELEVANCE_BUCKET_SECONDARY else 1,
            -int(item["groupSize"]),
            -int(item["reviewScore"]),
            _confidence_rank(str(item["confidence"])),
            0 if item["hasSuggestion"] else 1,
            str(item["title"]),
        )
    )
    return queue


def build_coordinate_review_wizard_steps(
    rows: Iterable[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Return individually ranked crash-review steps for the browser wizard."""

    steps: List[Dict[str, Any]] = []
    for fallback_row_number, raw_row in enumerate(rows, start=2):
        row = _normalize_row(raw_row)
        row_key = str(
            row.get("coordinate_recovery_row_key")
            or _review_row_key(
                row,
                source_row_number=int(row.get("coordinate_recovery_source_row") or fallback_row_number),
            )
        ).strip()
        if not row_key:
            continue

        route = _route_text(row)
        cross = _cross_text(row)
        mile_marker = _mile_marker_text(row)
        direction = _direction_text(row)
        feet_from = _first_text(row, _FEET_KEYS)
        locality = _display_locality(row)
        crash_id = _row_identifier(row) or f"Source row {int(row.get('coordinate_recovery_source_row') or fallback_row_number)}"
        crash_date = _first_text(row, _DATE_KEYS)
        crash_time = _first_text(row, _TIME_KEYS)

        location_parts: List[str] = []
        if cross:
            location_parts.append(f"At {cross}")
        if mile_marker:
            location_parts.append(f"Mile {mile_marker}")
        if feet_from:
            if direction:
                location_parts.append(f"{feet_from} ft {direction}")
            else:
                location_parts.append(f"{feet_from} ft from point")
        if locality:
            location_parts.append(locality)

        narrative = _extract_review_narrative(row)
        suggested_lat = parse_coordinate(row.get("suggested_latitude"))
        suggested_lon = parse_coordinate(row.get("suggested_longitude"))
        review_bucket = str(row.get("project_relevance_bucket") or PROJECT_RELEVANCE_BUCKET_PRIMARY)
        review_score = int(row.get("project_relevance_score") or 0)
        group_size = int(row.get("coordinate_recovery_group_size") or 1)
        suggested_inside_boundary = _parse_optional_bool(row.get("suggested_inside_boundary"))
        if not _is_surfaceable_review_suggestion(
            suggested_lat,
            suggested_lon,
            suggested_inside_boundary,
        ):
            suggested_lat = None
            suggested_lon = None
            suggested_inside_boundary = None

        steps.append(
            {
                "rowKey": row_key,
                "groupKey": str(row.get("coordinate_recovery_group") or ""),
                "crashId": crash_id,
                "sourceRow": int(row.get("coordinate_recovery_source_row") or fallback_row_number),
                "title": route or (mile_marker and f"Mile marker {mile_marker}") or "Unplaced crash",
                "detail": " | ".join(location_parts) or "Location details unavailable.",
                "crashDate": crash_date,
                "crashTime": crash_time,
                "narrative": narrative,
                "hasNarrative": bool(narrative),
                "status": str(row.get("coordinate_recovery_status") or ""),
                "confidence": str(row.get("coordinate_recovery_confidence") or "none"),
                "method": str(row.get("coordinate_recovery_method") or ""),
                "matchCount": int(row.get("coordinate_recovery_match_count") or 0),
                "candidateCount": int(row.get("coordinate_recovery_candidate_count") or 0),
                "groupSize": group_size,
                "hasSuggestion": suggested_lat is not None and suggested_lon is not None,
                "suggestedLatitude": suggested_lat,
                "suggestedLongitude": suggested_lon,
                "suggestedInsideBoundary": suggested_inside_boundary,
                "note": str(row.get("coordinate_recovery_note") or ""),
                "reviewBucket": review_bucket,
                "reviewScore": review_score,
                "reviewReason": str(row.get("project_relevance_reason") or ""),
                "reviewDetails": [
                    line.strip()
                    for line in str(row.get("project_relevance_details") or "").splitlines()
                    if line.strip()
                ],
            }
        )

    steps.sort(
        key=lambda item: (
            0 if str(item["reviewBucket"]) != PROJECT_RELEVANCE_BUCKET_SECONDARY else 1,
            -int(item["reviewScore"]),
            _confidence_rank(str(item["confidence"])),
            0 if item["hasSuggestion"] else 1,
            -int(item["groupSize"]),
            int(item["sourceRow"]),
            str(item["rowKey"]),
        )
    )
    return steps


def _normalize_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for key, value in row.items():
        normalized[normalize_header(key)] = value
    return normalized


def _parse_review_boolean(value: Any) -> Optional[bool]:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    if text in {"true", "t", "1", "yes", "y"}:
        return True
    if text in {"false", "f", "0", "no", "n"}:
        return False
    return None


def _build_evidence(
    rows: Sequence[Mapping[str, Any]],
    *,
    lat_key: str,
    lon_key: str,
) -> Dict[str, Dict[str, Counter[Coordinate]]]:
    evidence: Dict[str, Dict[str, Counter[Coordinate]]] = {
        mode: defaultdict(Counter) for mode in MODE_ORDER
    }
    for row in rows:
        lat = parse_coordinate(row.get(lat_key))
        lon = parse_coordinate(row.get(lon_key))
        if not is_usable_coordinate_pair(lat, lon):
            continue
        coord = (lat, lon)
        for mode in MODE_ORDER:
            fingerprint = _fingerprint(row, mode)
            if fingerprint:
                evidence[mode][fingerprint][coord] += 1
    return evidence


def _build_project_relevance_profile(
    rows: Sequence[Mapping[str, Any]],
    *,
    lat_key: str,
    lon_key: str,
    boundary: PolygonBoundary | None,
) -> Optional[_ProjectRelevanceProfile]:
    if boundary is None:
        return None

    inside_route_counts: Counter[str] = Counter()
    outside_route_counts: Counter[str] = Counter()
    inside_cross_counts: Counter[str] = Counter()
    outside_cross_counts: Counter[str] = Counter()
    inside_pair_counts: Counter[str] = Counter()
    outside_pair_counts: Counter[str] = Counter()
    inside_locality_counts: Counter[str] = Counter()
    inside_rows = 0

    for row in rows:
        lat = parse_coordinate(row.get(lat_key))
        lon = parse_coordinate(row.get(lon_key))
        if not is_usable_coordinate_pair(lat, lon):
            continue

        route_signal = _relevance_route_signal(row)
        cross_signal = _relevance_cross_signal(row)
        locality_signal = _relevance_locality_signal(row)
        is_inside = point_in_polygon(lon, lat, boundary)

        if is_inside:
            inside_rows += 1
            if locality_signal:
                inside_locality_counts[locality_signal] += 1
            if route_signal:
                inside_route_counts[route_signal] += 1
            if cross_signal:
                inside_cross_counts[cross_signal] += 1
            if route_signal and cross_signal:
                inside_pair_counts[f"{route_signal}|{cross_signal}"] += 1
        else:
            if route_signal:
                outside_route_counts[route_signal] += 1
            if cross_signal:
                outside_cross_counts[cross_signal] += 1
            if route_signal and cross_signal:
                outside_pair_counts[f"{route_signal}|{cross_signal}"] += 1

    if inside_rows < PROJECT_RELEVANCE_MIN_INSIDE_ROWS:
        return None

    dominant_locality = inside_locality_counts.most_common(1)[0][0] if inside_locality_counts else ""
    return _ProjectRelevanceProfile(
        inside_rows=inside_rows,
        dominant_locality=dominant_locality,
        inside_locality_counts=inside_locality_counts,
        inside_route_counts=inside_route_counts,
        outside_route_counts=outside_route_counts,
        inside_cross_counts=inside_cross_counts,
        outside_cross_counts=outside_cross_counts,
        inside_pair_counts=inside_pair_counts,
        outside_pair_counts=outside_pair_counts,
    )


def _assess_project_relevance(
    row: Mapping[str, Any],
    *,
    profile: Optional[_ProjectRelevanceProfile],
    suggestion: Optional[_RecoverySuggestion],
) -> _ProjectRelevanceAssessment:
    if profile is None:
        return _ProjectRelevanceAssessment(
            bucket=PROJECT_RELEVANCE_BUCKET_PRIMARY,
            score=0,
            reason="No KMZ-based project profile was available; kept in the primary review queue.",
            details=(
                "Decision rule: no inside/outside project profile could be built from rows that already had coordinates.",
            ),
        )

    route_signal = _relevance_route_signal(row)
    cross_signal = _relevance_cross_signal(row)
    locality_signal = _relevance_locality_signal(row)
    pair_signal = f"{route_signal}|{cross_signal}" if route_signal and cross_signal else ""
    route_display = _route_text(row) or "Unknown route"
    cross_display = _cross_text(row) or "Unknown cross street"
    locality_display = _display_locality(row)

    score = 0
    reasons: List[str] = []
    details: List[str] = []

    if pair_signal:
        pair_result = _score_project_signature(
            key=pair_signal,
            signal_label=f"{route_display} at {cross_display}",
            evidence_label="Route + cross street",
            inside_counts=profile.inside_pair_counts,
            outside_counts=profile.outside_pair_counts,
            strong_min_inside=2,
            strong_min_ratio=0.75,
            strong_score=85,
            likely_min_inside=1,
            likely_min_ratio=0.45,
            likely_score=68,
            possible_min_inside=2,
            possible_min_ratio=0.25,
            possible_score=50,
            outside_only_min_count=3,
            outside_only_score=-35,
            positive_label="Route/intersection pattern matches rows that already fall inside the KMZ",
            negative_label="Route/intersection pattern appears only outside the KMZ in rows with coordinates",
        )
        score += pair_result.score
        if pair_result.reason:
            reasons.append(pair_result.reason)
        if pair_result.detail:
            details.append(pair_result.detail)

    if route_signal:
        route_result = _score_project_signature(
            key=route_signal,
            signal_label=route_display,
            evidence_label="Route only",
            inside_counts=profile.inside_route_counts,
            outside_counts=profile.outside_route_counts,
            strong_min_inside=8,
            strong_min_ratio=0.40,
            strong_score=42,
            likely_min_inside=5,
            likely_min_ratio=0.25,
            likely_score=32,
            possible_min_inside=15,
            possible_min_ratio=0.12,
            possible_score=18,
            outside_only_min_count=5,
            outside_only_score=-35,
            positive_label="Route frequently appears inside the KMZ",
            negative_label="Route appears only outside the KMZ in rows with coordinates",
        )
        score += route_result.score
        if route_result.reason:
            reasons.append(route_result.reason)
        if route_result.detail:
            details.append(route_result.detail)

    if cross_signal:
        cross_result = _score_project_signature(
            key=cross_signal,
            signal_label=cross_display,
            evidence_label="Cross street only",
            inside_counts=profile.inside_cross_counts,
            outside_counts=profile.outside_cross_counts,
            strong_min_inside=4,
            strong_min_ratio=0.35,
            strong_score=18,
            likely_min_inside=2,
            likely_min_ratio=0.20,
            likely_score=10,
            possible_min_inside=0,
            possible_min_ratio=1.0,
            possible_score=0,
            outside_only_min_count=5,
            outside_only_score=-12,
            positive_label="Cross street shows up inside the KMZ corridor",
            negative_label="Cross street appears only outside the KMZ in rows with coordinates",
        )
        score += cross_result.score
        if cross_result.reason:
            reasons.append(cross_result.reason)
        if cross_result.detail:
            details.append(cross_result.detail)

    if locality_signal and locality_signal == profile.dominant_locality:
        score += 5
        reasons.append("Crash locality matches the dominant inside-the-project locality.")
        inside_locality_count = int(profile.inside_locality_counts[locality_signal])
        details.append(
            f"Locality: {locality_display} is the dominant inside-boundary locality in "
            f"{inside_locality_count} known-coordinate crash(es)."
        )

    if suggestion is not None:
        if suggestion.inside_boundary is True:
            score += 18
            reasons.append("Suggested coordinate falls inside the KMZ boundary.")
            details.append(
                "Suggested point check: the proposed coordinate lands inside the KMZ boundary."
            )
        elif suggestion.inside_boundary is False:
            score -= 18
            reasons.append("Suggested coordinate falls outside the KMZ boundary.")
            details.append(
                "Suggested point check: the proposed coordinate lands outside the KMZ boundary."
            )

    bucket = (
        PROJECT_RELEVANCE_BUCKET_PRIMARY
        if score >= PROJECT_RELEVANCE_PRIMARY_SCORE
        else PROJECT_RELEVANCE_BUCKET_SECONDARY
    )
    reason_text = reasons[0] if reasons else ""
    if not reason_text:
        if bucket == PROJECT_RELEVANCE_BUCKET_PRIMARY:
            reason_text = "Structured crash fields still align closely enough with inside-the-project patterns."
        else:
            reason_text = "No strong inside-the-project pattern matched rows already inside the KMZ."
    decision_detail = (
        f"Decision rule: score {score} meets the primary-review threshold of "
        f"{PROJECT_RELEVANCE_PRIMARY_SCORE}."
        if bucket == PROJECT_RELEVANCE_BUCKET_PRIMARY
        else f"Decision rule: score {score} stays below the primary-review threshold of "
        f"{PROJECT_RELEVANCE_PRIMARY_SCORE}."
    )
    detail_lines = [decision_detail]
    detail_lines.extend(details[:4])
    return _ProjectRelevanceAssessment(
        bucket=bucket,
        score=score,
        reason=reason_text,
        details=tuple(detail_lines),
    )


def _score_project_signature(
    *,
    key: str,
    signal_label: str,
    evidence_label: str,
    inside_counts: Counter[str],
    outside_counts: Counter[str],
    strong_min_inside: int,
    strong_min_ratio: float,
    strong_score: int,
    likely_min_inside: int,
    likely_min_ratio: float,
    likely_score: int,
    possible_min_inside: int,
    possible_min_ratio: float,
    possible_score: int,
    outside_only_min_count: int,
    outside_only_score: int,
    positive_label: str,
    negative_label: str,
) -> _ProjectRelevanceSignal:
    inside_count = int(inside_counts[key])
    outside_count = int(outside_counts[key])
    total = inside_count + outside_count
    inside_ratio = inside_count / total if total else 0.0
    detail = _build_project_signal_detail(
        evidence_label=evidence_label,
        signal_label=signal_label,
        inside_count=inside_count,
        outside_count=outside_count,
    )

    if strong_min_inside and inside_count >= strong_min_inside and inside_ratio >= strong_min_ratio:
        return _ProjectRelevanceSignal(score=strong_score, reason=positive_label, detail=detail)
    if likely_min_inside and inside_count >= likely_min_inside and inside_ratio >= likely_min_ratio:
        return _ProjectRelevanceSignal(score=likely_score, reason=positive_label, detail=detail)
    if possible_min_inside and inside_count >= possible_min_inside and inside_ratio >= possible_min_ratio:
        return _ProjectRelevanceSignal(score=possible_score, reason=positive_label, detail=detail)
    if inside_count == 0 and outside_count >= outside_only_min_count:
        return _ProjectRelevanceSignal(
            score=outside_only_score,
            reason=negative_label,
            detail=detail or (
                f"{evidence_label}: {signal_label} appears in {outside_count} known-coordinate "
                "crash(es), all outside the KMZ."
            ),
        )
    if total:
        return _ProjectRelevanceSignal(
            score=0,
            reason="",
            detail=f"{detail} This signal was too mixed or too small to change the review score.",
        )
    return _ProjectRelevanceSignal(score=0, reason="", detail="")


def _build_project_signal_detail(
    *,
    evidence_label: str,
    signal_label: str,
    inside_count: int,
    outside_count: int,
) -> str:
    total = inside_count + outside_count
    if total <= 0:
        return ""
    inside_pct = round((inside_count / total) * 100)
    sample_note = " Limited sample." if total < 4 else ""
    return (
        f"{evidence_label}: {signal_label} appears in {inside_count} inside-boundary and "
        f"{outside_count} outside-boundary known-coordinate crash(es) ({inside_pct}% inside)."
        f"{sample_note}"
    )


def _relevance_route_signal(row: Mapping[str, Any]) -> str:
    direct = _first_text(row, _ROUTE_ID_KEYS, route=True)
    if direct:
        return _compact_signal(direct)
    for name_key, suffix_key in _ROUTE_NAME_KEYS:
        name = _first_text(row, (name_key,), route=True)
        suffix = _first_text(row, (suffix_key,))
        if name:
            return _compact_signal(" ".join(part for part in (name, suffix) if part))
    return ""


def _relevance_cross_signal(row: Mapping[str, Any]) -> str:
    return _compact_signal(_cross_text(row))


def _relevance_locality_signal(row: Mapping[str, Any]) -> str:
    parts = [_compact_signal(_first_text(row, ("city", "township"))), _compact_signal(_first_text(row, ("county",)))]
    return "|".join(part for part in parts if part)


def _display_locality(row: Mapping[str, Any]) -> str:
    return _locality_text(row).replace("|", " / ") or "Unknown locality"


def _review_row_key(row: Mapping[str, Any], *, source_row_number: int) -> str:
    identifier = _row_identifier(row)
    if identifier:
        return f"{identifier}__row{source_row_number}"
    return f"source-row-{source_row_number}"


def _extract_review_narrative(row: Mapping[str, Any]) -> str:
    for key in _NARRATIVE_KEYS:
        if key not in row:
            continue
        text = _raw_text(row.get(key))
        if text:
            return text
    for key, value in row.items():
        if not any(token in key for token in ("narrative", "description", "remark", "note", "comment", "statement")):
            continue
        text = _raw_text(value)
        if text:
            return text
    return ""


def _parse_optional_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    if text in {"true", "t", "1", "yes", "y"}:
        return True
    if text in {"false", "f", "0", "no", "n"}:
        return False
    return None


def _raw_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _compact_signal(value: str) -> str:
    if not value:
        return ""
    return re.sub(r"[^A-Z0-9]+", "", value.upper())


def _row_identifier(row: Mapping[str, Any]) -> str:
    for key in _IDENTIFIER_KEYS:
        value = _clean_text(row.get(key))
        if value:
            return value
    return ""


def _confidence_rank(value: str) -> int:
    mapping = {
        "high": 0,
        "medium": 1,
        "user_approved": 2,
        "none": 3,
    }
    return mapping.get(value, 4)


def _select_suggestion(
    row: Mapping[str, Any],
    *,
    evidence: Dict[str, Dict[str, Counter[Coordinate]]],
    boundary: PolygonBoundary | None,
) -> Optional[_RecoverySuggestion]:
    best_review_suggestion: Optional[_RecoverySuggestion] = None

    for priority, mode in enumerate(MODE_ORDER):
        fingerprint = _fingerprint(row, mode)
        if not fingerprint:
            continue
        counter = evidence[mode].get(fingerprint)
        if not counter:
            continue

        suggestion = _build_suggestion(
            mode,
            fingerprint=fingerprint,
            counter=counter,
            boundary=boundary,
            priority=priority,
        )
        if suggestion.confidence == "high":
            return suggestion

        if suggestion.confidence == "medium" and (
            best_review_suggestion is None
            or suggestion.priority < best_review_suggestion.priority
            or (
                suggestion.priority == best_review_suggestion.priority
                and suggestion.matched_rows > best_review_suggestion.matched_rows
            )
        ):
            best_review_suggestion = suggestion

    return best_review_suggestion


def _is_surfaceable_review_suggestion(
    latitude: float | None,
    longitude: float | None,
    inside_boundary: Optional[bool],
) -> bool:
    return is_usable_coordinate_pair(latitude, longitude) and inside_boundary is not False


def _build_suggestion(
    mode: str,
    *,
    fingerprint: str,
    counter: Counter[Coordinate],
    boundary: PolygonBoundary | None,
    priority: int,
) -> _RecoverySuggestion:
    clusters = _build_clusters(
        counter,
        threshold_feet=MODE_CLUSTER_DISTANCE_FEET[mode],
        boundary=boundary,
    )
    top_cluster = clusters[0]
    total_matches = sum(cluster.total_count for cluster in clusters)
    top_share = top_cluster.total_count / max(total_matches, 1)
    review_limit = MODE_REVIEW_DISTANCE_FEET[mode]
    high_limit = MODE_CLUSTER_DISTANCE_FEET[mode]

    if len(clusters) == 1 and top_cluster.spread_feet <= high_limit:
        confidence = "high"
    elif (
        top_cluster.total_count >= 2
        and top_share >= MODE_HIGH_SHARE[mode]
        and top_cluster.spread_feet <= high_limit
    ):
        confidence = "high"
    elif (
        len(clusters) == 1 and top_cluster.spread_feet <= review_limit
    ) or (
        top_cluster.total_count >= 2
        and top_share >= 0.5
        and top_cluster.spread_feet <= review_limit
    ):
        confidence = "medium"
    else:
        confidence = "none"

    note = (
        f"{MODE_LABELS[mode].title()}: {top_cluster.total_count} of {total_matches} "
        f"matched rows clustered within {int(round(top_cluster.spread_feet))} ft "
        f"across {len(clusters)} candidate location(s)."
    )
    if top_cluster.inside_boundary is True:
        note += " Top candidate is inside the KMZ boundary."
    elif top_cluster.inside_boundary is False:
        note += " Top candidate is outside the KMZ boundary."

    return _RecoverySuggestion(
        method=mode,
        fingerprint=fingerprint,
        latitude=top_cluster.latitude,
        longitude=top_cluster.longitude,
        matched_rows=top_cluster.total_count,
        candidate_count=len(clusters),
        confidence=confidence,
        note=note,
        inside_boundary=top_cluster.inside_boundary,
        priority=priority,
    )


def _build_clusters(
    counter: Counter[Coordinate],
    *,
    threshold_feet: float,
    boundary: PolygonBoundary | None,
) -> List["_ClusterSnapshot"]:
    clusters: List[_ClusterBuilder] = []
    for coord, count in counter.most_common():
        target = None
        for cluster in clusters:
            if cluster.accepts(coord, threshold_feet=threshold_feet):
                target = cluster
                break
        if target is None:
            target = _ClusterBuilder()
            clusters.append(target)
        target.add(coord, count)

    snapshots = [
        _ClusterSnapshot.from_builder(cluster, boundary=boundary)
        for cluster in clusters
    ]
    snapshots.sort(
        key=lambda cluster: (
            -cluster.total_count,
            _boundary_rank(cluster.inside_boundary),
            cluster.spread_feet,
        )
    )
    return snapshots


@dataclass(frozen=True)
class _ClusterSnapshot:
    latitude: float
    longitude: float
    total_count: int
    spread_feet: float
    inside_boundary: Optional[bool]

    @classmethod
    def from_builder(
        cls,
        cluster: _ClusterBuilder,
        *,
        boundary: PolygonBoundary | None,
    ) -> "_ClusterSnapshot":
        lat, lon = cluster.centroid
        inside_boundary = None
        if boundary is not None:
            inside_boundary = point_in_polygon(lon, lat, boundary)
        return cls(
            latitude=lat,
            longitude=lon,
            total_count=cluster.total_count,
            spread_feet=cluster.spread_feet(),
            inside_boundary=inside_boundary,
        )


def _boundary_rank(value: Optional[bool]) -> int:
    if value is True:
        return 0
    if value is False:
        return 1
    return 2


def _apply_suggestion_metadata(
    row: Dict[str, Any],
    suggestion: _RecoverySuggestion,
    *,
    status: str,
    group_key: str,
) -> None:
    row["coordinate_recovery_status"] = status
    row["coordinate_recovery_method"] = suggestion.method
    row["coordinate_recovery_confidence"] = suggestion.confidence
    row["coordinate_recovery_match_count"] = suggestion.matched_rows
    row["coordinate_recovery_candidate_count"] = suggestion.candidate_count
    row["coordinate_recovery_group"] = group_key
    row["coordinate_recovery_note"] = suggestion.note


def _apply_review_group_sizes(review_rows: List[Dict[str, Any]]) -> None:
    group_sizes = Counter(
        str(row.get("coordinate_recovery_group") or "")
        for row in review_rows
    )
    for row in review_rows:
        row["coordinate_recovery_group_size"] = group_sizes[str(row.get("coordinate_recovery_group") or "")]


def _review_group_key(row: Mapping[str, Any]) -> Optional[str]:
    for mode in MODE_ORDER:
        fingerprint = _fingerprint(row, mode)
        if fingerprint:
            return fingerprint
    route = _route_text(row)
    locality = _locality_text(row)
    if route and locality:
        return f"{route}|{locality}"
    if route:
        return route
    return None


def _fingerprint(row: Mapping[str, Any], mode: str) -> Optional[str]:
    route = _route_text(row)
    locality = _locality_text(row)

    if mode == "offset_match":
        reference = _cross_text(row) or _mile_marker_text(row)
        feet = _first_text(row, _FEET_KEYS)
        direction = _direction_text(row)
        if route and reference and feet and direction:
            return "|".join(part for part in (route, reference, feet, direction, locality) if part)
        return None

    if mode == "intersection_match":
        cross = _cross_text(row)
        if route and cross:
            return "|".join(part for part in (route, cross, locality) if part)
        return None

    if mode == "mile_marker_match":
        mile_marker = _mile_marker_text(row)
        if route and mile_marker:
            return "|".join(part for part in (route, mile_marker, locality) if part)
        return None

    if mode == "unique_location_match":
        unique_id = _first_text(row, ("unique_location_id",))
        return unique_id or None

    raise ValueError(f"Unsupported recovery mode: {mode}")


def _route_text(row: Mapping[str, Any]) -> str:
    direct = _first_text(row, _ROUTE_ID_KEYS, route=True)
    if direct:
        return direct

    house_number = _first_text(row, _HOUSE_NUMBER_KEYS)
    for name_key, suffix_key in _ROUTE_NAME_KEYS:
        name = _first_text(row, (name_key,), route=True)
        suffix = _first_text(row, (suffix_key,))
        if name:
            combined = " ".join(part for part in (house_number, name, suffix) if part)
            return _clean_text(combined, route=True)
    return ""


def _cross_text(row: Mapping[str, Any]) -> str:
    return _first_text(row, _CROSS_KEYS, route=True)


def _mile_marker_text(row: Mapping[str, Any]) -> str:
    return _first_text(row, _MILE_MARKER_KEYS)


def _direction_text(row: Mapping[str, Any]) -> str:
    value = _first_text(row, _DIRECTION_KEYS)
    if not value:
        return ""
    text = value.replace("BOUND", "").strip()
    mapping = {
        "NORTH": "N",
        "NB": "N",
        "SOUTH": "S",
        "SB": "S",
        "EAST": "E",
        "EB": "E",
        "WEST": "W",
        "WB": "W",
    }
    return mapping.get(text, text[:2] if len(text) > 2 else text)


def _locality_text(row: Mapping[str, Any]) -> str:
    city = _first_text(row, ("city", "township"))
    county = _first_text(row, ("county",))
    return "|".join(part for part in (city, county) if part)


def _first_text(
    row: Mapping[str, Any],
    keys: Sequence[str],
    *,
    route: bool = False,
) -> str:
    for key in keys:
        value = _clean_text(row.get(key), route=route)
        if value:
            return value
    return ""


def _clean_text(value: Any, *, route: bool = False) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if route:
        text = _standardize_route(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.upper()


def _distance_feet(left: Coordinate, right: Coordinate) -> float:
    if left == right:
        return 0.0
    lat1, lon1 = left
    lat2, lon2 = right
    radius_m = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return radius_m * c * 3.28084
