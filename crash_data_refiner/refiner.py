"""Core data refinement logic for CrashDataRefiner.

This module exposes the :class:`CrashDataRefiner` class which is responsible for
transforming crash data sets into a consistent, analysis-friendly format.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from collections import Counter
import re
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple

from .geo import BoundaryFilterReport, PolygonBoundary, parse_coordinate, point_in_polygon


_DATE_FORMATS: Sequence[str] = (
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%m/%d/%Y",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%d-%b-%Y",
)


def _normalize_header(header: str) -> str:
    """Convert a column header to ``snake_case`` suitable for programmatic access."""
    cleaned = re.sub(r"[^0-9a-zA-Z]+", "_", header.strip().lower())
    cleaned = re.sub(r"_{2,}", "_", cleaned)
    return cleaned.strip("_")


def _parse_date(value: str) -> Optional[str]:
    """Attempt to parse a free-form date string.

    Returns an ISO-8601 formatted date string on success. If the value cannot be
    parsed it is returned unchanged to allow downstream inspection.
    """
    if value is None:
        return None

    text = value.strip()
    if not text:
        return None

    # If the string is already ISO-8601-ish we accept it as-is to avoid
    # unnecessary parsing failures.
    iso_match = re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?", text)
    if iso_match:
        return text.replace("T", " ")

    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        else:
            # When only a date is provided we emit the canonical YYYY-MM-DD form.
            if fmt == "%Y-%m-%d" or fmt == "%m/%d/%Y" or fmt == "%d-%b-%Y":
                return parsed.strftime("%Y-%m-%d")
            return parsed.strftime("%Y-%m-%d %H:%M:%S")
    return text


def _coerce_numeric(value: str, numeric_type: type) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return numeric_type(text)
    except (TypeError, ValueError):
        return None


def _coerce_boolean(value: str) -> Optional[bool]:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "t", "1", "yes", "y"}:
        return True
    if text in {"false", "f", "0", "no", "n"}:
        return False
    return None


_CRASH_TYPE_COLUMNS = {
    "crash_type",
    "manner_of_collision",
    "collision_type",
    "collision_manner",
}
_ROUTE_COLUMNS = {
    "route",
    "roadway_name",
    "roadway_id",
    "road_name",
    "street_name",
    "roadway_number",
    "roadway_suffix",
    "intersecting_road_name",
    "intersecting_road_number",
}

_CRASH_TYPE_CANONICAL = {
    "rear end": "Rear End",
    "rearend": "Rear End",
    "head on": "Head On",
    "headon": "Head On",
    "left turn": "Left Turn",
    "right turn": "Right Turn",
    "sideswipe same direction": "Same Direction Sideswipe",
    "same direction sideswipe": "Same Direction Sideswipe",
    "sideswipe opposite direction": "Opposite Direction Sideswipe",
    "opposite direction sideswipe": "Opposite Direction Sideswipe",
    "backing": "Backing Crash",
    "backing crash": "Backing Crash",
}

_ROUTE_TOKEN_MAP = {
    "AVENUE": "AVE",
    "BOULEVARD": "BLVD",
    "CIRCLE": "CIR",
    "COURT": "CT",
    "DRIVE": "DR",
    "EAST": "E",
    "EASTBOUND": "E",
    "EB": "E",
    "EXPRESSWAY": "EXPY",
    "FREEWAY": "FWY",
    "FORT": "FT",
    "HIGHWAY": "HWY",
    "INTERSTATE": "I",
    "JUNCTION": "JCT",
    "LANE": "LN",
    "MOUNT": "MT",
    "NORTH": "N",
    "NORTHBOUND": "N",
    "NB": "N",
    "PARKWAY": "PKWY",
    "PLACE": "PL",
    "ROAD": "RD",
    "SOUTH": "S",
    "SOUTHBOUND": "S",
    "SB": "S",
    "SQUARE": "SQ",
    "STREET": "ST",
    "TURNPIKE": "TPKE",
    "TRAIL": "TRL",
    "WEST": "W",
    "WESTBOUND": "W",
    "WB": "W",
}
_ROUTE_MULTI_TOKENS = (
    (("U", "S", "ROUTE"), "US"),
    (("U", "S", "HWY"), "US"),
    (("U", "S", "HIGHWAY"), "US"),
    (("US", "ROUTE"), "US"),
    (("US", "HWY"), "US"),
    (("US", "HIGHWAY"), "US"),
    (("U", "S"), "US"),
    (("STATE", "ROAD"), "SR"),
    (("STATE", "ROUTE"), "SR"),
    (("STATE", "RD"), "SR"),
    (("STATE", "HWY"), "SR"),
    (("STATE", "HIGHWAY"), "SR"),
    (("ST", "RD"), "SR"),
    (("ST", "ROAD"), "SR"),
    (("S", "R"), "SR"),
    (("COUNTY", "ROAD"), "CR"),
    (("COUNTY", "RD"), "CR"),
    (("CO", "RD"), "CR"),
)
_DIRECTION_TOKENS = {
    "N",
    "S",
    "E",
    "W",
    "NE",
    "NW",
    "SE",
    "SW",
    "NB",
    "SB",
    "EB",
    "WB",
}
_ROUTE_PREFIX_TOKENS = {"SR", "US", "I", "CR"}
_ROUTE_SUFFIX_TOKENS = {
    "AVE",
    "BLVD",
    "CIR",
    "CT",
    "DR",
    "EXPY",
    "FWY",
    "HWY",
    "JCT",
    "LN",
    "PKWY",
    "PL",
    "RD",
    "SQ",
    "ST",
    "TPKE",
    "TRL",
}


def _strip_direction_tokens(tokens: List[str]) -> List[str]:
    while tokens and tokens[0] in _DIRECTION_TOKENS:
        tokens = tokens[1:]
    while tokens and tokens[-1] in _DIRECTION_TOKENS:
        tokens = tokens[:-1]
    return tokens


def _is_numeric_token(token: str) -> bool:
    return token.isdigit()


def _is_route_number(tokens: List[str]) -> bool:
    if any(token in _ROUTE_PREFIX_TOKENS for token in tokens):
        return True
    return any(_is_numeric_token(token) for token in tokens)


def _preferred_route_suffixes(rows: Iterable[Dict[str, Any]]) -> Dict[str, str]:
    suffix_counts: Dict[str, Counter[str]] = {}
    for row in rows:
        for column in _ROUTE_COLUMNS:
            value = row.get(column)
            if value is None or not isinstance(value, str):
                continue
            tokens = value.split()
            if not tokens or _is_route_number(tokens):
                continue
            if tokens[-1] not in _ROUTE_SUFFIX_TOKENS:
                continue
            base = " ".join(tokens[:-1]).strip()
            if not base:
                continue
            suffix_counts.setdefault(base, Counter())[tokens[-1]] += 1
    preferred: Dict[str, str] = {}
    for base, counts in suffix_counts.items():
        if len(counts) == 1:
            preferred[base] = next(iter(counts.keys()))
    return preferred


def _apply_route_suffixes(rows: List[Dict[str, Any]]) -> None:
    preferred = _preferred_route_suffixes(rows)
    if not preferred:
        return
    for row in rows:
        for column in _ROUTE_COLUMNS:
            value = row.get(column)
            if value is None or not isinstance(value, str):
                continue
            tokens = value.split()
            if not tokens or _is_route_number(tokens):
                continue
            if tokens[-1] in _ROUTE_SUFFIX_TOKENS:
                continue
            base = " ".join(tokens).strip()
            suffix = preferred.get(base)
            if suffix:
                row[column] = f"{base} {suffix}"

def _standardize_crash_type(value: Any) -> Any:
    if value is None or not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return value
    cleaned = re.sub(r"[^0-9a-zA-Z]+", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return value
    normalized = cleaned.lower()
    if normalized in _CRASH_TYPE_CANONICAL:
        return _CRASH_TYPE_CANONICAL[normalized]
    return " ".join(word.capitalize() for word in normalized.split())


def _standardize_route(value: Any) -> Any:
    if value is None or not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return value
    cleaned = re.sub(r"[.,]", "", text)
    cleaned = re.sub(r"[-/]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return value
    tokens = cleaned.upper().split()
    collapsed: list[str] = []
    index = 0
    while index < len(tokens):
        if tokens[index] == "IN":
            next_token = tokens[index + 1] if index + 1 < len(tokens) else ""
            if next_token and _is_numeric_token(next_token):
                collapsed.append("SR")
                index += 1
                continue
        matched = False
        for parts, replacement in _ROUTE_MULTI_TOKENS:
            length = len(parts)
            if tokens[index:index + length] == list(parts):
                collapsed.append(replacement)
                index += length
                matched = True
                break
        if not matched:
            collapsed.append(tokens[index])
            index += 1

    normalized = [_ROUTE_TOKEN_MAP.get(token, token) for token in collapsed]
    if "HWY" in normalized and any(token in _ROUTE_PREFIX_TOKENS for token in normalized):
        normalized = [token for token in normalized if token != "HWY"]
    normalized = _strip_direction_tokens(normalized)
    return " ".join(normalized)


@dataclass
class RefinementConfig:
    """Configuration describing how a crash dataset should be cleaned."""

    required_columns: Sequence[str] = field(default_factory=list)
    date_columns: Sequence[str] = field(default_factory=list)
    integer_columns: Sequence[str] = field(default_factory=list)
    float_columns: Sequence[str] = field(default_factory=list)
    boolean_columns: Sequence[str] = field(default_factory=list)
    dedupe_on: Sequence[str] = field(default_factory=list)
    fill_defaults: Mapping[str, Any] = field(default_factory=dict)

    def normalized(self) -> "RefinementConfig":
        return RefinementConfig(
            required_columns=[_normalize_header(col) for col in self.required_columns],
            date_columns=[_normalize_header(col) for col in self.date_columns],
            integer_columns=[_normalize_header(col) for col in self.integer_columns],
            float_columns=[_normalize_header(col) for col in self.float_columns],
            boolean_columns=[_normalize_header(col) for col in self.boolean_columns],
            dedupe_on=[_normalize_header(col) for col in self.dedupe_on],
            fill_defaults={_normalize_header(k): v for k, v in self.fill_defaults.items()},
        )


@dataclass
class RefinementReport:
    total_rows: int
    kept_rows: int
    dropped_missing_required: int
    dropped_duplicates: int
    coerced_dates: int
    coerced_numbers: int
    coerced_booleans: int

    @property
    def output_rows(self) -> int:
        return self.kept_rows


class CrashDataRefiner:
    """Perform configurable refinement of crash datasets.

    The refiner operates on in-memory row dictionaries so it can be reused with a
    variety of data sources (CSV, JSON, SQL exports, etc.).
    """

    def __init__(self, config: RefinementConfig | None = None):
        self.config = (config or RefinementConfig()).normalized()

    def refine_rows(
        self,
        rows: Iterable[Mapping[str, Any]],
        *,
        normalize_headers: bool = True,
    ) -> Tuple[List[Dict[str, Any]], RefinementReport]:
        total_rows = 0
        kept_rows = 0
        dropped_missing_required = 0
        dropped_duplicates = 0
        coerced_dates = 0
        coerced_numbers = 0
        coerced_booleans = 0

        dedupe_index: set[Tuple[Any, ...]] = set()
        refined_rows: List[Dict[str, Any]] = []

        for raw_row in rows:
            total_rows += 1
            row = self._normalize_row(raw_row) if normalize_headers else dict(raw_row)

            if not self._has_required_columns(row):
                dropped_missing_required += 1
                continue

            if self.config.dedupe_on:
                dedupe_key = tuple(row.get(column) for column in self.config.dedupe_on)
                if dedupe_key in dedupe_index:
                    dropped_duplicates += 1
                    continue
                dedupe_index.add(dedupe_key)

            # Apply default values before coercion so they also get converted.
            for column, value in self.config.fill_defaults.items():
                current = row.get(column)
                if current is None:
                    row[column] = value
                    continue
                if isinstance(current, str) and not current.strip():
                    row[column] = value
                    continue

            for column in self.config.date_columns:
                original = row.get(column)
                parsed = _parse_date(original) if original is not None else None
                if parsed != original and parsed is not None:
                    row[column] = parsed
                    coerced_dates += 1
                elif parsed is None:
                    row[column] = None

            for column in self.config.integer_columns:
                original = row.get(column)
                coerced = _coerce_numeric(original, int)
                if coerced is not None:
                    row[column] = int(coerced)
                    if coerced != original:
                        coerced_numbers += 1
                else:
                    row[column] = None

            for column in self.config.float_columns:
                original = row.get(column)
                coerced = _coerce_numeric(original, float)
                if coerced is not None:
                    row[column] = float(coerced)
                    if coerced != original:
                        coerced_numbers += 1
                else:
                    row[column] = None

            for column in self.config.boolean_columns:
                original = row.get(column)
                coerced = _coerce_boolean(original)
                if coerced is not None:
                    row[column] = coerced
                    if coerced != original:
                        coerced_booleans += 1
                else:
                    row[column] = None

            for column in _CRASH_TYPE_COLUMNS:
                if column in row:
                    row[column] = _standardize_crash_type(row.get(column))

            for column in _ROUTE_COLUMNS:
                if column in row:
                    row[column] = _standardize_route(row.get(column))

            refined_rows.append(row)
            kept_rows += 1

        _apply_route_suffixes(refined_rows)

        report = RefinementReport(
            total_rows=total_rows,
            kept_rows=kept_rows,
            dropped_missing_required=dropped_missing_required,
            dropped_duplicates=dropped_duplicates,
            coerced_dates=coerced_dates,
            coerced_numbers=coerced_numbers,
            coerced_booleans=coerced_booleans,
        )
        return refined_rows, report

    def filter_rows_by_boundary(
        self,
        rows: Iterable[Mapping[str, Any]],
        *,
        boundary: PolygonBoundary,
        latitude_column: str,
        longitude_column: str,
        normalize_headers: bool = True,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], BoundaryFilterReport]:
        lat_column = _normalize_header(latitude_column)
        lon_column = _normalize_header(longitude_column)

        included: List[Dict[str, Any]] = []
        excluded: List[Dict[str, Any]] = []
        invalid: List[Dict[str, Any]] = []
        total_rows = 0

        for raw_row in rows:
            total_rows += 1
            row = self._normalize_row(raw_row) if normalize_headers else dict(raw_row)

            lat = parse_coordinate(row.get(lat_column))
            lon = parse_coordinate(row.get(lon_column))

            if lat is None or lon is None:
                invalid.append(row)
                continue

            if point_in_polygon(lon, lat, boundary):
                included.append(row)
            else:
                excluded.append(row)

        report = BoundaryFilterReport(
            total_rows=total_rows,
            included_rows=len(included),
            excluded_rows=len(excluded),
            invalid_rows=len(invalid),
        )
        return included, excluded, invalid, report

    def refine_rows_with_boundary(
        self,
        rows: Iterable[Mapping[str, Any]],
        *,
        boundary: PolygonBoundary,
        latitude_column: str,
        longitude_column: str,
    ) -> Tuple[List[Dict[str, Any]], RefinementReport, BoundaryFilterReport, List[Dict[str, Any]]]:
        included, _excluded, invalid, boundary_report = self.filter_rows_by_boundary(
            rows,
            boundary=boundary,
            latitude_column=latitude_column,
            longitude_column=longitude_column,
            normalize_headers=True,
        )
        refined_rows, report = self.refine_rows(included, normalize_headers=False)
        return refined_rows, report, boundary_report, invalid

    def _normalize_row(self, row: Mapping[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        for key, value in row.items():
            normalized[_normalize_header(key)] = value
        return normalized

    def _has_required_columns(self, row: Mapping[str, Any]) -> bool:
        for column in self.config.required_columns:
            value = row.get(column)
            if value in (None, ""):
                return False
        return True

    def refine_file(self, input_path: str, output_path: str) -> RefinementReport:
        rows = list(self._read_csv(input_path))
        refined_rows, report = self.refine_rows(rows)
        self._write_csv(output_path, refined_rows)
        return report

    def _read_csv(self, path: str) -> Iterator[Dict[str, Any]]:
        import csv

        with open(path, "r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                yield row

    def _write_csv(self, path: str, rows: Sequence[Mapping[str, Any]]) -> None:
        import csv

        if not rows:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                handle.write("")
            return

        header_set = set()
        for row in rows:
            header_set.update(row.keys())
        headers = sorted(header_set)
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            for row in rows:
                writer.writerow({header: row.get(header) for header in headers})
