"""Generate KMZ crash outputs matching the standard crash data template."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, Tuple
import zipfile
from xml.sax.saxutils import escape

from .geo import parse_coordinate
from .normalize import normalize_header


_SUMMARY_FIELDS: Sequence[Sequence[str]] = (
    ("weather", "weather_condition", "weather_conditions"),
    ("road_surface", "road_surface_condition", "surface_condition", "roadway_surface"),
    ("primary_factor", "contributing_factor", "contributing_factors", "primary_cause", "cause"),
    ("collision_type", "manner_of_collision", "crash_type", "collision_manner"),
)

_NARRATIVE_FIELDS: Sequence[str] = (
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
)

_FATALITY_FIELDS: Sequence[str] = (
    "fatalities",
    "fatality",
    "injury_fatal_number",
    "fatal_count",
)

_INJURY_FIELDS: Sequence[str] = (
    "injury_nonfatal_number",
    "serious_injuries",
    "injuries",
    "injury_count",
    "bodily_injuries",
    "bodily_injury_count",
    "possible_injuries",
    "minor_injuries",
    "non_incapacitating_injuries",
    "incapacitating_injuries",
    "evident_injuries",
)

_VEHICLE_ICON_HREF = "http://maps.google.com/mapfiles/kml/shapes/cabs.png"
_SERIOUS_ICON_COLOR = "ff2a2aff"
_PDO_ICON_COLOR = "ff2dbb63"


def write_kmz_report(
    path: str,
    *,
    rows: Iterable[Mapping[str, Any]],
    latitude_column: str,
    longitude_column: str,
    folder_name: str = "Crash Data",
    label_order: str = "source",
) -> int:
    lat_key = normalize_header(latitude_column)
    lon_key = normalize_header(longitude_column)

    placemarks: list[Tuple[float, float, str, str]] = []
    for row in rows:
        normalized_row = {normalize_header(key): value for key, value in row.items()}
        lat = parse_coordinate(normalized_row.get(lat_key))
        lon = parse_coordinate(normalized_row.get(lon_key))
        if lat is None or lon is None:
            continue
        description = _build_description(normalized_row, lat_key=lat_key, lon_key=lon_key)
        severity_style = _placemark_style_id(normalized_row)
        placemarks.append((lat, lon, description, severity_style))

    placemarks = _order_placemarks(placemarks, label_order)
    kml = _render_kml(Path(path).name, folder_name, placemarks)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("doc.kml", kml)
    return len(placemarks)


def _order_placemarks(
    placemarks: Sequence[Tuple[float, float, str, str]],
    label_order: str,
) -> list[Tuple[float, float, str, str]]:
    normalized = (label_order or "").strip().lower()
    if normalized == "west_to_east":
        return sorted(placemarks, key=lambda item: (item[1], item[0]))
    if normalized == "south_to_north":
        return sorted(placemarks, key=lambda item: (item[0], item[1]))
    return list(placemarks)


def _to_number(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0


def _has_positive_value(row: Mapping[str, Any], keys: Sequence[str]) -> bool:
    for key in keys:
        if key in row and _to_number(row.get(key)) > 0:
            return True
    return False


def _placemark_style_id(row: Mapping[str, Any]) -> str:
    has_fatality = _has_positive_value(row, _FATALITY_FIELDS)
    has_injury = _has_positive_value(row, _INJURY_FIELDS)
    return "#seriousCrash" if has_fatality or has_injury else "#pdoCrash"


def _severity_label(row: Mapping[str, Any]) -> str:
    has_fatality = _has_positive_value(row, _FATALITY_FIELDS)
    has_injury = _has_positive_value(row, _INJURY_FIELDS)
    if has_fatality:
        return "Severity: Fatal Crash"
    if has_injury:
        return "Severity: Bodily Injury Crash"
    return "Severity: Property Damage Only (PDO)"


def _build_description(row: Mapping[str, Any], *, lat_key: str, lon_key: str) -> str:
    # The KML description drives the Google Earth click preview bubble.
    used_keys = {lat_key, lon_key, "kmz_label"}
    summary_values: list[str] = [_severity_label(row)]

    for candidates in _SUMMARY_FIELDS:
        key, value = _first_nonempty(row, candidates)
        if key:
            used_keys.add(key)
        summary_values.append(value)

    narrative_key, narrative_value = _first_nonempty(row, _NARRATIVE_FIELDS)
    if not narrative_value:
        narrative_key, narrative_value = _first_nonempty_by_substring(
            row,
            ("narrative", "description"),
        )
    if narrative_key:
        used_keys.add(narrative_key)

    remaining = [
        _stringify(value)
        for key, value in row.items()
        if key not in used_keys and _stringify(value)
    ]

    for index in range(1, 5):
        if not summary_values[index] and remaining:
            summary_values[index] = remaining.pop(0)

    if not narrative_value and remaining:
        narrative_value = remaining.pop(0)

    segments = [_normalize_line(value) for value in summary_values]
    segments.append(_normalize_line(narrative_value))
    return "<br/>".join(segments)


def _first_nonempty(row: Mapping[str, Any], candidates: Sequence[str]) -> Tuple[str | None, str]:
    for key in candidates:
        if key not in row:
            continue
        value = _stringify(row.get(key))
        if value:
            return key, value
    return None, ""


def _first_nonempty_by_substring(
    row: Mapping[str, Any],
    substrings: Sequence[str],
) -> Tuple[str | None, str]:
    for substring in substrings:
        for key, value in row.items():
            if substring not in key:
                continue
            text = _stringify(value)
            if text:
                return key, text
    return None, ""


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_line(value: str) -> str:
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\n", "<br/>")
    return text


def _wrap_cdata(text: str) -> str:
    safe = text.replace("]]>", "]]]]><![CDATA[>")
    return f"<![CDATA[{safe}]]>"


def _render_kml(
    document_name: str,
    folder_name: str,
    placemarks: Sequence[Tuple[float, float, str, str]],
) -> str:
    doc_name = escape(document_name)
    folder_label = escape(folder_name)

    placemark_blocks = []
    for index, (lat, lon, description, style_url) in enumerate(placemarks, start=1):
        placemark_blocks.append(
            f"""    <Placemark>
      <name>{index}</name>
      <Snippet maxLines="0"></Snippet>
      <description>{_wrap_cdata(description)}</description>
      <LookAt>
        <longitude>{lon}</longitude>
        <latitude>{lat}</latitude>
        <altitude>0</altitude>
        <heading>0</heading>
        <tilt>0</tilt>
        <range>1000</range>
        <altitudeMode>relativeToGround</altitudeMode>
      </LookAt>
      <styleUrl>{style_url}</styleUrl>
      <ExtendedData>
      </ExtendedData>
      <Point>
        <coordinates>{lon},{lat},0</coordinates>
      </Point>
    </Placemark>"""
        )

    placemark_text = "\n".join(placemark_blocks)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:kml="http://www.opengis.net/kml/2.2" xmlns:atom="http://www.w3.org/2005/Atom">
<Document>
  <name>{doc_name}</name>
  <StyleMap id="seriousCrash">
    <Pair>
      <key>normal</key>
      <styleUrl>#seriousCrashNormal</styleUrl>
    </Pair>
    <Pair>
      <key>highlight</key>
      <styleUrl>#seriousCrashHighlight</styleUrl>
    </Pair>
  </StyleMap>
  <StyleMap id="pdoCrash">
    <Pair>
      <key>normal</key>
      <styleUrl>#pdoCrashNormal</styleUrl>
    </Pair>
    <Pair>
      <key>highlight</key>
      <styleUrl>#pdoCrashHighlight</styleUrl>
    </Pair>
  </StyleMap>
  <Style id="seriousCrashHighlight">
    <IconStyle>
      <color>{_SERIOUS_ICON_COLOR}</color>
      <scale>1.15</scale>
      <Icon>
        <href>{_VEHICLE_ICON_HREF}</href>
      </Icon>
    </IconStyle>
    <BalloonStyle>
      <text>$[description]</text>
    </BalloonStyle>
    <LineStyle>
      <width>3</width>
    </LineStyle>
  </Style>
  <Style id="pdoCrashHighlight">
    <IconStyle>
      <color>{_PDO_ICON_COLOR}</color>
      <scale>1.15</scale>
      <Icon>
        <href>{_VEHICLE_ICON_HREF}</href>
      </Icon>
    </IconStyle>
    <BalloonStyle>
      <text>$[description]</text>
    </BalloonStyle>
    <LineStyle>
      <width>3</width>
    </LineStyle>
  </Style>
  <Style id="seriousCrashNormal">
    <IconStyle>
      <color>{_SERIOUS_ICON_COLOR}</color>
      <Icon>
        <href>{_VEHICLE_ICON_HREF}</href>
      </Icon>
    </IconStyle>
    <BalloonStyle>
      <text>$[description]</text>
    </BalloonStyle>
    <LineStyle>
      <width>2</width>
    </LineStyle>
  </Style>
  <Style id="pdoCrashNormal">
    <IconStyle>
      <color>{_PDO_ICON_COLOR}</color>
      <Icon>
        <href>{_VEHICLE_ICON_HREF}</href>
      </Icon>
    </IconStyle>
    <BalloonStyle>
      <text>$[description]</text>
    </BalloonStyle>
    <LineStyle>
      <width>2</width>
    </LineStyle>
  </Style>
  <Folder>
    <name>{folder_label}</name>
{placemark_text}
    <atom:link rel="app" href="https://www.google.com/earth/about/versions/#earth-pro" title="Google Earth Pro 7.3.6.10441"></atom:link>
  </Folder>
</Document>
</kml>
"""
