"""Generate polished PDF crash reports with aerial imagery and bullet summaries."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from io import BytesIO
import math
from pathlib import Path
import re
import textwrap
from typing import Any, Mapping, Sequence

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

from .geo import parse_coordinate
from .refiner import _normalize_header


DEFAULT_TILE_URL = "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
DEFAULT_ROADS_TILE_URL = (
    "https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}"
)
DEFAULT_LABELS_TILE_URL = (
    "https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
)
TILE_SIZE = 256
IDENTIFIER_FIELDS: Sequence[tuple[str, str]] = (
    ("crash_id", "Crash ID"),
    ("report_number", "Report #"),
    ("case_number", "Case #"),
    ("collision_id", "Collision ID"),
    ("event_number", "Event #"),
    ("master_record_number", "Master Record #"),
    ("unique_location_id", "Location ID"),
)
IDENTIFIER_KEYS = {key for key, _label in IDENTIFIER_FIELDS}
DATE_TIME_FIELDS: Sequence[str] = ("crash_date_time", "collision_date_time", "crash_datetime")
DATE_FIELDS: Sequence[str] = ("crash_date", "collision_date", "date")
TIME_FIELDS: Sequence[str] = ("time_of_crash", "time", "hour_of_collision_timestamp", "crash_time")
LOCATION_FIELDS: Sequence[str] = ("location", "address")
ROAD_FIELDS: Sequence[str] = (
    "roadway_name",
    "road_name",
    "street_name",
    "route",
    "roadway_id",
    "roadway_number",
)
INTERSECTION_FIELDS: Sequence[str] = (
    "intersection",
    "cross_street",
    "intersecting_road_name",
    "intersecting_road_number",
)
SEVERITY_FIELDS: Sequence[str] = ("crash_severity_calc", "injury_severity", "severity", "crash_severity")
COLLISION_FIELDS: Sequence[str] = ("manner_of_collision", "collision_type", "crash_type", "collision_manner")
PRIMARY_FACTOR_FIELDS: Sequence[str] = ("primary_factor", "primary_cause")
CONTRIBUTING_FACTOR_FIELDS: Sequence[str] = ("contributing_factor", "secondary_factor", "contributing_cause")
CONDITION_PARTS: Sequence[tuple[str, Sequence[str]]] = (
    ("Weather", ("weather",)),
    ("Surface", ("surface_condition", "surface_type", "road_surface")),
    ("Light", ("light_condition", "lighting")),
)
FLAG_FIELDS: Sequence[tuple[str, str]] = (
    ("hit_and_run_indic", "Hit and run"),
    ("work_zone", "Work zone"),
    ("workzone", "Work zone"),
    ("construct_indic", "Construction zone"),
    ("school_zone_indic", "School zone"),
    ("secondary_crash_indic", "Secondary crash"),
    ("in_corporate_limit_indic", "In city limits"),
)
INJURY_COUNT_FIELDS: Sequence[tuple[str, Sequence[str]]] = (
    ("Fatal", ("fatalities", "injury_fatal_number", "fatal_injuries", "fatal_count")),
    ("Serious", ("serious_injuries", "inj_incapacitating_number", "incapacitating_injuries")),
    ("Minor", ("minor_injuries", "inj_nonincapacitating_number", "nonincapacitating_injuries")),
    ("Possible", ("inj_possible_number", "possible_injuries")),
    ("Unknown", ("inj_unknown_number", "injury_unknown_number")),
    ("Non-fatal", ("injury_nonfatal_number", "nonfatal_injuries")),
)
NARRATIVE_FIELDS: Sequence[str] = (
    "accident_narrative",
    "crash_narrative",
    "crash_report_narrative",
    "report_narrative",
    "narrative",
)
DAMAGE_FIELDS: Sequence[str] = ("property_damage_type", "property_damage", "damage_type")
LONG_TEXT_HINTS: Sequence[str] = ("narrative", "comment", "statement", "summary", "note")
EXCLUDED_KEYS = {"latitude", "longitude", "kmz_label"}
SKIP_TEXT_VALUES = {
    "none",
    "null",
    "nan",
    "n/a",
    "na",
    "unknown",
    "unspecified",
    "not reported",
    "no junction involved",
    "no",
}
LABEL_OVERRIDES = {
    "crash_id": "Crash ID",
    "report_number": "Report #",
    "case_number": "Case #",
    "collision_id": "Collision ID",
    "event_number": "Event #",
    "master_record_number": "Master Record #",
    "unique_location_id": "Location ID",
    "crash_severity_calc": "Severity",
    "injury_severity": "Severity",
    "manner_of_collision": "Collision",
    "collision_type": "Collision type",
    "crash_type": "Crash type",
    "primary_factor": "Primary factor",
    "contributing_factor": "Contributing factor",
    "property_damage_type": "Damage",
    "roadway_name": "Roadway",
    "roadway_number": "Route",
    "surface_condition": "Surface",
    "surface_type": "Surface",
    "light_condition": "Light",
    "accident_narrative": "Narrative",
    "crash_narrative": "Narrative",
    "crash_report_narrative": "Narrative",
    "report_narrative": "Narrative",
}
FIELD_SCORE_RULES: Sequence[tuple[int, Sequence[str]]] = (
    (90, ("severity", "injur", "fatal", "serious", "minor")),
    (85, ("collision", "manner", "crash_type", "primary_factor", "contributing_factor")),
    (80, ("weather", "surface", "light", "roadway", "road", "street", "route", "intersection", "cross_street")),
    (70, ("city", "county", "state", "location", "address")),
    (60, ("vehicle", "driver", "unit", "speed", "occupant")),
    (50, ("property_damage", "damage", "deer", "animal", "median")),
    (40, ("work_zone", "school_zone", "construction", "workzone")),
    (30, ("report", "case", "event", "number")),
    (20, ("id",)),
)


@dataclass
class CrashReportConfig:
    """Tuning values that influence the generated PDF layout."""

    title: str = "Crash Data Full Report"
    page_size: tuple[float, float] = letter
    margin: float = 0.7 * inch
    header_font: str = "Helvetica-Bold"
    body_font: str = "Helvetica"
    header_size: int = 20
    label_size: int = 12
    map_zoom: int = 17
    map_zoom_factor: float = 5.0
    map_width_px: int = 1600
    map_height_px: int = 1000
    bullet_leading: float = 15.0
    max_bullets: int = 12
    max_value_chars: int = 120
    narrative_size: int = 11
    narrative_min_size: int = 9
    narrative_leading: float = 14.0
    narrative_gap: float = 8.0


class AerialTileRenderer:
    """Render an aerial map around a crash location using ArcGIS tiles."""

    def __init__(
        self,
        tile_url: str = DEFAULT_TILE_URL,
        *,
        overlay_urls: Sequence[str] | None = None,
        timeout: float = 8.0,
    ) -> None:
        self.tile_url = tile_url
        self.overlay_urls = overlay_urls or [DEFAULT_ROADS_TILE_URL, DEFAULT_LABELS_TILE_URL]
        self.timeout = timeout
        self._session = requests.Session()

    def render(
        self,
        lat: float | None,
        lon: float | None,
        *,
        width: int,
        height: int,
        zoom: int,
        zoom_factor: float = 1.0,
        kmz_label: str | None = None,
    ) -> Image.Image:
        if lat is None or lon is None:
            return self._fallback_image(width, height, "Location unavailable")

        render_zoom, render_width, render_height = self._resolve_zoom(width, height, zoom, zoom_factor)

        center_x, center_y = self._latlon_to_tile(lat, lon, render_zoom)
        center_px = center_x * TILE_SIZE
        center_py = center_y * TILE_SIZE

        half_w = render_width / 2
        half_h = render_height / 2
        min_px = center_px - half_w
        max_px = center_px + half_w
        min_py = center_py - half_h
        max_py = center_py + half_h

        tile_min_x = math.floor(min_px / TILE_SIZE)
        tile_max_x = math.floor(max_px / TILE_SIZE)
        tile_min_y = math.floor(min_py / TILE_SIZE)
        tile_max_y = math.floor(max_py / TILE_SIZE)

        map_image = Image.new("RGBA", (render_width, render_height), (12, 16, 23, 255))
        tiles = 2**render_zoom
        for tile_x in range(tile_min_x, tile_max_x + 1):
            wrapped_x = tile_x % tiles
            for tile_y in range(tile_min_y, tile_max_y + 1):
                if tile_y < 0 or tile_y >= tiles:
                    tile_image = self._blank_tile()
                else:
                    tile_image = self._fetch_tile(wrapped_x, tile_y, render_zoom)
                dest_x = int((tile_x * TILE_SIZE) - min_px)
                dest_y = int((tile_y * TILE_SIZE) - min_py)
                map_image.paste(tile_image, (dest_x, dest_y))

        if (render_width, render_height) != (width, height):
            map_image = map_image.resize((width, height), resample=Image.LANCZOS)

        self._draw_marker(map_image, width // 2, height // 2, kmz_label)
        return map_image.convert("RGB")

    def _resolve_zoom(self, width: int, height: int, zoom: int, zoom_factor: float) -> tuple[int, int, int]:
        if zoom_factor <= 1.0:
            return zoom, width, height
        zoom_delta = math.log(zoom_factor, 2)
        render_zoom = int(math.ceil(zoom + zoom_delta))
        scale = (2 ** (render_zoom - zoom)) / zoom_factor
        render_width = max(1, int(math.ceil(width * scale)))
        render_height = max(1, int(math.ceil(height * scale)))
        return render_zoom, render_width, render_height

    def _fetch_tile(self, x: int, y: int, z: int) -> Image.Image:
        base_image = self._fetch_tile_layer(self.tile_url, x, y, z, convert_mode="RGBA")
        for overlay_url in self.overlay_urls:
            overlay = self._fetch_tile_layer(overlay_url, x, y, z, convert_mode="RGBA")
            base_image = Image.alpha_composite(base_image, overlay)
        return base_image

    def _fetch_tile_layer(self, url_template: str, x: int, y: int, z: int, *, convert_mode: str) -> Image.Image:
        url = url_template.format(x=x, y=y, z=z)
        try:
            response = self._session.get(url, timeout=self.timeout)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content)).convert(convert_mode)
        except Exception:
            image = self._blank_tile().convert(convert_mode)
        return image

    @staticmethod
    def _latlon_to_tile(lat: float, lon: float, zoom: int) -> tuple[float, float]:
        lat_rad = math.radians(lat)
        n = 2.0**zoom
        x = (lon + 180.0) / 360.0 * n
        y = (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n
        return x, y

    @staticmethod
    def _blank_tile() -> Image.Image:
        tile = Image.new("RGB", (TILE_SIZE, TILE_SIZE), (15, 21, 33))
        draw = ImageDraw.Draw(tile)
        draw.rectangle((0, 0, TILE_SIZE, TILE_SIZE), fill=(15, 21, 33))
        draw.line((0, 0, TILE_SIZE, TILE_SIZE), fill=(36, 56, 75), width=1)
        draw.line((0, TILE_SIZE, TILE_SIZE, 0), fill=(36, 56, 75), width=1)
        return tile

    @staticmethod
    def _fallback_image(width: int, height: int, caption: str) -> Image.Image:
        gradient = Image.new("RGB", (width, height), (15, 21, 33))
        overlay = Image.new("RGBA", (width, height))
        draw = ImageDraw.Draw(gradient)
        for y in range(height):
            ratio = y / max(height - 1, 1)
            r = int(15 + (12 * ratio))
            g = int(21 + (12 * ratio))
            b = int(33 + (16 * ratio))
            draw.line((0, y, width, y), fill=(r, g, b))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle((0, 0, width, height), fill=(12, 16, 23, 160))
        combined = Image.alpha_composite(gradient.convert("RGBA"), overlay).convert("RGB")
        text_draw = ImageDraw.Draw(combined)
        text_draw.text((24, 18), "Aerial preview unavailable", fill=(227, 237, 243))
        text_draw.text((24, 44), caption, fill=(154, 167, 178))
        return combined

    @staticmethod
    def _draw_marker(image: Image.Image, x: int, y: int, kmz_label: str | None = None) -> None:
        draw = ImageDraw.Draw(image)
        radius = 10
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=(232, 79, 62),
            outline=(0, 0, 0),
            width=2,
        )
        inner_radius = 4
        draw.ellipse(
            (x - inner_radius, y - inner_radius, x + inner_radius, y + inner_radius),
            fill=(255, 255, 255),
        )
        if kmz_label:
            font = ImageFont.load_default()
            text = kmz_label
            bbox = font.getbbox(text)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            padding = 4
            label_x = x - radius - text_w - padding
            label_y = y - radius - text_h - padding
            rect = (
                label_x - padding,
                label_y - padding,
                label_x + text_w + padding,
                label_y + text_h + padding,
            )
            draw.rounded_rectangle(rect, radius=4, fill=(18, 24, 32, 220))
            draw.text((label_x, label_y), text, font=font, fill=(255, 255, 255))


def generate_pdf_report(
    path: str,
    *,
    rows: Sequence[Mapping[str, Any]],
    latitude_column: str,
    longitude_column: str,
    config: CrashReportConfig | None = None,
) -> Path:
    pdf_path = Path(path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        raise ValueError("No rows available to include in the crash report PDF.")

    normalized_rows = [_normalize_row(row) for row in rows]
    builder = CrashReportPDFBuilder(config or CrashReportConfig())
    builder.render(pdf_path, normalized_rows, latitude_column, longitude_column)
    return pdf_path


class CrashReportPDFBuilder:
    def __init__(self, config: CrashReportConfig) -> None:
        self.config = config
        self.renderer = AerialTileRenderer()

    def render(
        self,
        pdf_path: Path,
        rows: Sequence[Mapping[str, Any]],
        latitude_column: str,
        longitude_column: str,
    ) -> None:
        canvas_obj = canvas.Canvas(str(pdf_path), pagesize=self.config.page_size)
        width, height = self.config.page_size
        for index, row in enumerate(rows, start=1):
            lat = parse_coordinate(row.get(_normalize_header(latitude_column)))
            lon = parse_coordinate(row.get(_normalize_header(longitude_column)))
            kmz_label = _format_kmz_label(row.get("kmz_label"))
            map_image = self.renderer.render(
                lat,
                lon,
                width=self.config.map_width_px,
                height=self.config.map_height_px,
                zoom=self.config.map_zoom,
                zoom_factor=self.config.map_zoom_factor,
                kmz_label=kmz_label,
            )
            self._render_page(canvas_obj, width, height, row, map_image, lat, lon, index, len(rows))
            canvas_obj.showPage()
        canvas_obj.save()

    def _render_page(
        self,
        canvas_obj: canvas.Canvas,
        page_width: float,
        page_height: float,
        row: Mapping[str, Any],
        map_image: Image.Image,
        lat: float | None,
        lon: float | None,
        index: int,
        total: int,
    ) -> None:
        margin = self.config.margin
        content_height = page_height - (margin * 2)
        header_height = 1.05 * inch
        gutter = 0.22 * inch
        body_height = content_height - header_height - 0.15 * inch
        left_width = (page_width - (margin * 2) - gutter) * 0.54
        right_width = (page_width - (margin * 2) - gutter) - left_width
        content_top = page_height - margin

        self._draw_header(canvas_obj, margin, content_top, page_width - (margin * 2), header_height, index, total)
        summary_lines, narrative = self._build_bullet_lines(row, lat, lon)
        self._draw_bullets(
            canvas_obj,
            margin,
            content_top - header_height - 0.25 * inch,
            left_width,
            body_height,
            summary_lines,
            narrative,
        )
        self._draw_map(canvas_obj, margin + left_width + gutter, margin, right_width, body_height, map_image, lat, lon)

    def _draw_header(self, canvas_obj: canvas.Canvas, x: float, top: float, width: float, height: float, index: int, total: int) -> None:
        accent = colors.Color(0.07, 0.22, 0.36)
        ink = colors.Color(0.11, 0.14, 0.18)
        canvas_obj.setFillColor(colors.white)
        canvas_obj.roundRect(x, top - height, width, height, 9, fill=1, stroke=0)
        canvas_obj.setFillColor(accent)
        canvas_obj.roundRect(x + width - 120, top - height + 14, 104, 20, 6, fill=1, stroke=0)
        canvas_obj.setFillColor(colors.white)
        canvas_obj.setFont(self.config.body_font, 10)
        canvas_obj.drawRightString(x + width - 16, top - height + 28, f"Crash {index} of {total}")

        canvas_obj.setFillColor(ink)
        canvas_obj.setFont(self.config.header_font, self.config.header_size)
        canvas_obj.drawString(x + 18, top - 26, self.config.title)
        canvas_obj.setFillColor(colors.Color(0.35, 0.39, 0.45))
        canvas_obj.setFont(self.config.body_font, 11)
        canvas_obj.drawString(x + 18, top - 44, "Comprehensive incident overview")
        canvas_obj.setFillColor(accent)
        canvas_obj.rect(x + 18, top - height + 14, 48, 3, fill=1, stroke=0)

    def _draw_bullets(
        self,
        canvas_obj: canvas.Canvas,
        x: float,
        top: float,
        width: float,
        height: float,
        summary_lines: Sequence[str],
        narrative_text: str,
    ) -> None:
        canvas_obj.setFillColor(colors.Color(0.96, 0.97, 0.99))
        canvas_obj.roundRect(x, top - height + 6, width, height, 10, fill=1, stroke=0)
        canvas_obj.setStrokeColor(colors.Color(0.86, 0.89, 0.93))
        canvas_obj.setLineWidth(1)
        canvas_obj.roundRect(x + 4, top - height + 10, width - 8, height - 8, 8, fill=0, stroke=1)

        padding = 16
        max_width = width - (padding * 2)
        font_name = self.config.body_font
        summary_font_size = self.config.label_size
        summary_wrapped = self._wrap_lines(summary_lines, font_name, summary_font_size, max_width)

        narrative_body = narrative_text.strip() if narrative_text else "Not provided."
        narrative_font_size = self.config.narrative_size
        narrative_min_size = self.config.narrative_min_size

        narrative_lines = self._wrap_paragraph(narrative_body, font_name, narrative_font_size, max_width)
        available_height = height

        summary_wrapped, narrative_lines, narrative_font_size = self._fit_text_blocks(
            summary_wrapped,
            narrative_body,
            font_name,
            summary_font_size,
            narrative_font_size,
            narrative_min_size,
            max_width,
            available_height,
        )

        text_object = canvas_obj.beginText()
        text_object.setTextOrigin(x + padding, top)
        text_object.setFont(font_name, summary_font_size)
        text_object.setLeading(self.config.bullet_leading)
        text_object.setFillColor(colors.Color(0.09, 0.12, 0.16))
        for line in summary_wrapped:
            text_object.textLine(line)
        if summary_wrapped and narrative_lines:
            text_object.moveCursor(0, -self.config.narrative_gap)
        if narrative_lines:
            text_object.setFont(font_name, narrative_font_size)
            scaled_leading = self.config.narrative_leading * (narrative_font_size / max(summary_font_size, 1))
            text_object.setLeading(scaled_leading)
            for line in narrative_lines:
                text_object.textLine(line)
        canvas_obj.drawText(text_object)

    def _draw_map(
        self,
        canvas_obj: canvas.Canvas,
        x: float,
        y: float,
        width: float,
        height: float,
        map_image: Image.Image,
        lat: float | None,
        lon: float | None,
    ) -> None:
        canvas_obj.setFillColor(colors.white)
        canvas_obj.roundRect(x, y, width, height, 10, fill=1, stroke=0)
        canvas_obj.setStrokeColor(colors.Color(0.82, 0.86, 0.9))
        canvas_obj.setLineWidth(1)
        canvas_obj.roundRect(x + 4, y + 4, width - 8, height - 8, 9, fill=0, stroke=1)

        inset_x = x + 12
        inset_y = y + 16
        inset_width = width - 24
        inset_height = height - 32

        prepared = self._prepare_map_image(map_image, lat)
        target_size = (max(1, int(inset_width)), max(1, int(inset_height)))
        fitted = ImageOps.fit(prepared, target_size, method=Image.LANCZOS, centering=(0.5, 0.5))
        map_reader = ImageReader(fitted)
        canvas_obj.drawImage(
            map_reader,
            inset_x,
            inset_y,
            width=inset_width,
            height=inset_height,
            preserveAspectRatio=False,
        )

    def _prepare_map_image(self, map_image: Image.Image, lat: float | None) -> Image.Image:
        softened = ImageEnhance.Color(map_image).enhance(0.9)
        sharpened = ImageEnhance.Contrast(softened).enhance(1.05)
        annotated = sharpened.convert("RGBA")
        draw = ImageDraw.Draw(annotated)
        self._add_north_arrow(draw, annotated.size)
        self._add_scale_bar(draw, annotated.size, lat)
        return annotated.convert("RGB")

    def _add_north_arrow(self, draw: ImageDraw.ImageDraw, size: tuple[int, int]) -> None:
        width, height = size
        arrow_height = 68
        base_x = width - 52
        base_y = 32
        shaft_top = base_y
        shaft_bottom = base_y + arrow_height
        draw.line((base_x, shaft_bottom, base_x, shaft_top + 14), fill=(20, 26, 33), width=3)
        draw.polygon(
            [
                (base_x, shaft_top),
                (base_x - 10, shaft_top + 16),
                (base_x + 10, shaft_top + 16),
            ],
            fill=(14, 90, 142),
        )
        draw.line((base_x - 8, shaft_bottom - 6, base_x + 8, shaft_bottom - 6), fill=(20, 26, 33), width=3)
        font = ImageFont.load_default()
        draw.text((base_x - 5, shaft_top - 14), "N", font=font, fill=(20, 26, 33))

    def _add_scale_bar(self, draw: ImageDraw.ImageDraw, size: tuple[int, int], lat: float | None) -> None:
        width, height = size
        if lat is None:
            return
        meters_per_px = 156543.03392 * math.cos(math.radians(lat)) / (2**self.config.map_zoom)
        target_meters = meters_per_px * (width * 0.18)
        candidates = [25, 50, 100, 200, 400, 800, 1600, 3200]
        chosen = min(candidates, key=lambda m: abs(m - target_meters))
        bar_px = chosen / max(meters_per_px, 1e-6)
        origin_x = 28
        origin_y = height - 38
        draw.rectangle((origin_x, origin_y, origin_x + bar_px, origin_y + 8), fill=(20, 26, 33))
        draw.rectangle((origin_x, origin_y, origin_x + bar_px, origin_y + 3), fill=(255, 255, 255))
        font = ImageFont.load_default()
        label = f"{int(chosen)} m" if chosen < 1000 else f"{chosen/1000:.1f} km"
        text_w, text_h = font.getsize(label)
        draw.text((origin_x + bar_px / 2 - text_w / 2, origin_y - text_h - 4), label, font=font, fill=(20, 26, 33))

    def _build_bullet_lines(
        self,
        row: Mapping[str, Any],
        lat: float | None,
        lon: float | None,
    ) -> tuple[list[str], str]:
        bullets: list[str] = []
        used_keys: set[str] = set()

        if lat is not None and lon is not None:
            bullets.append(f"Coordinates: {lat:.5f} deg, {lon:.5f} deg")
            used_keys.update({"latitude", "longitude"})

        builders = (
            self._build_identifier_line,
            self._build_datetime_line,
            self._build_location_line,
            self._build_severity_line,
            self._build_injury_line,
            self._build_collision_line,
            self._build_factor_line,
            self._build_conditions_line,
            self._build_context_line,
            self._build_damage_line,
        )
        for builder in builders:
            if len(bullets) >= self.config.max_bullets:
                return bullets[: self.config.max_bullets]
            line, keys = builder(row)
            if line:
                bullets.append(line)
                used_keys.update(keys)

        if len(bullets) < self.config.max_bullets:
            bullets.extend(
                self._select_additional_fields(
                    row,
                    used_keys=used_keys,
                    limit=self.config.max_bullets - len(bullets),
                )
            )
        narrative_text, narrative_keys = self._extract_narrative_text(row)
        used_keys.update(narrative_keys)
        return bullets, narrative_text or ""

    def _first_value(
        self,
        row: Mapping[str, Any],
        keys: Sequence[str],
        *,
        skip_zero: bool = False,
    ) -> tuple[str, Any] | None:
        for key in keys:
            value = row.get(key)
            text = _stringify(value)
            if not text or _is_skippable_text(text):
                continue
            if skip_zero and _is_zeroish(text):
                continue
            return key, value
        return None

    def _format_date_value(self, value: Any) -> tuple[str, bool]:
        if value is None:
            return "", False
        if isinstance(value, datetime):
            if value.time() == time(0, 0):
                return value.strftime("%Y-%m-%d"), False
            return value.strftime("%Y-%m-%d %H:%M"), True
        if isinstance(value, date) and not isinstance(value, datetime):
            return value.strftime("%Y-%m-%d"), False
        if isinstance(value, time):
            return value.strftime("%H:%M"), True
        text = _stringify(value)
        if not text:
            return "", False
        if " " in text:
            date_part, time_part = text.split(" ", 1)
            if time_part in {"00:00", "00:00:00"}:
                return date_part, False
        return text, ":" in text

    def _build_identifier_line(self, row: Mapping[str, Any]) -> tuple[str | None, set[str]]:
        for key, label in IDENTIFIER_FIELDS:
            text = _stringify(row.get(key))
            if text and not _is_skippable_text(text):
                return f"{label}: {text}", set(IDENTIFIER_KEYS)
        return None, set()

    def _build_datetime_line(self, row: Mapping[str, Any]) -> tuple[str | None, set[str]]:
        date_time_entry = self._first_value(row, DATE_TIME_FIELDS)
        if date_time_entry:
            key, value = date_time_entry
            text, has_time = self._format_date_value(value)
            if text:
                if has_time:
                    return f"Date/Time: {text}", {key}
                time_entry = self._first_value(row, TIME_FIELDS)
                if time_entry:
                    time_key, time_value = time_entry
                    time_text, _has_time = self._format_date_value(time_value)
                    if time_text:
                        return f"Date/Time: {text} {time_text}", {key, time_key}
                return f"Date: {text}", {key}

        date_entry = self._first_value(row, DATE_FIELDS)
        time_entry = self._first_value(row, TIME_FIELDS)
        if date_entry:
            date_key, date_value = date_entry
            date_text, has_time = self._format_date_value(date_value)
            if date_text:
                if has_time:
                    return f"Date/Time: {date_text}", {date_key}
                if time_entry:
                    time_key, time_value = time_entry
                    time_text, _has_time = self._format_date_value(time_value)
                    if time_text:
                        return f"Date/Time: {date_text} {time_text}", {date_key, time_key}
                return f"Date: {date_text}", {date_key}

        if time_entry:
            time_key, time_value = time_entry
            time_text, _has_time = self._format_date_value(time_value)
            if time_text:
                return f"Time: {time_text}", {time_key}
        return None, set()

    def _build_location_line(self, row: Mapping[str, Any]) -> tuple[str | None, set[str]]:
        used_keys: set[str] = set()
        address = ""

        location_entry = self._first_value(row, LOCATION_FIELDS)
        if location_entry:
            key, value = location_entry
            address = _stringify(value)
            used_keys.add(key)
        else:
            road_entry = self._first_value(row, ROAD_FIELDS)
            if road_entry:
                road_key, road_value = road_entry
                road_text = _stringify(road_value)
                used_keys.add(road_key)
                used_keys.update(ROAD_FIELDS)

                house = _stringify(row.get("roadway_house_number"))
                if house and not _is_skippable_text(house):
                    used_keys.add("roadway_house_number")
                else:
                    house = ""

                suffix = _stringify(row.get("roadway_suffix"))
                if suffix and not _is_skippable_text(suffix):
                    used_keys.add("roadway_suffix")
                else:
                    suffix = ""

                address = " ".join(part for part in [house, road_text, suffix] if part)

        intersection_entry = self._first_value(row, INTERSECTION_FIELDS)
        if intersection_entry:
            intersection_key, intersection_value = intersection_entry
            intersection_text = _stringify(intersection_value)
            used_keys.add(intersection_key)
            if address:
                address = f"{address} at {intersection_text}"
            else:
                address = intersection_text

        city_text = _stringify(row.get("city"))
        if city_text and not _is_skippable_text(city_text):
            used_keys.add("city")
        else:
            city_text = ""

        county_text = _stringify(row.get("county"))
        if county_text and not _is_skippable_text(county_text):
            used_keys.add("county")
            if "county" not in county_text.lower():
                county_text = f"{county_text} County"
        else:
            county_text = ""

        state_text = _stringify(row.get("state"))
        if state_text and not _is_skippable_text(state_text):
            used_keys.add("state")
        else:
            state_text = ""

        place_parts = [part for part in [city_text, county_text, state_text] if part]
        location_parts = [part for part in [address, ", ".join(place_parts) if place_parts else ""] if part]

        if location_parts:
            return f"Location: {', '.join(location_parts)}", used_keys
        return None, set()

    def _build_severity_line(self, row: Mapping[str, Any]) -> tuple[str | None, set[str]]:
        severity_entry = self._first_value(row, SEVERITY_FIELDS)
        if severity_entry:
            key, value = severity_entry
            text = _stringify(value)
            return f"Severity: {text}", {key}
        return None, set()

    def _build_injury_line(self, row: Mapping[str, Any]) -> tuple[str | None, set[str]]:
        used_keys: set[str] = set()
        parts: list[str] = []
        saw_counts = False

        for label, keys in INJURY_COUNT_FIELDS:
            for key in keys:
                raw = row.get(key)
                text = _stringify(raw)
                if not text or _is_skippable_text(text):
                    continue
                number = _coerce_number(text)
                if number is None:
                    continue
                saw_counts = True
                used_keys.add(key)
                if number > 0:
                    if label == "Non-fatal" and parts:
                        break
                    count = int(number) if number.is_integer() else number
                    parts.append(f"{label} {count}")
                break

        if parts:
            return f"Injuries: {', '.join(parts)}", used_keys

        injury_entry = self._first_value(row, ("injuries", "injury_count", "injury"), skip_zero=True)
        if injury_entry:
            key, value = injury_entry
            text = _stringify(value)
            if text:
                return f"Injuries: {text}", {key}

        if saw_counts:
            return "Injuries: None reported", used_keys
        return None, set()

    def _build_collision_line(self, row: Mapping[str, Any]) -> tuple[str | None, set[str]]:
        collision_entry = self._first_value(row, COLLISION_FIELDS)
        if collision_entry:
            key, value = collision_entry
            text = _stringify(value)
            return f"Collision: {text}", {key}
        return None, set()

    def _build_factor_line(self, row: Mapping[str, Any]) -> tuple[str | None, set[str]]:
        primary_entry = self._first_value(row, PRIMARY_FACTOR_FIELDS)
        contributing_entry = self._first_value(row, CONTRIBUTING_FACTOR_FIELDS)

        if primary_entry and contributing_entry:
            primary_key, primary_value = primary_entry
            contributing_key, contributing_value = contributing_entry
            primary_text = _stringify(primary_value)
            contributing_text = _stringify(contributing_value)
            return (
                f"Factors: Primary - {primary_text}; Contributing - {contributing_text}",
                {primary_key, contributing_key},
            )

        if primary_entry:
            key, value = primary_entry
            return f"Primary factor: {_stringify(value)}", {key}

        if contributing_entry:
            key, value = contributing_entry
            return f"Contributing factor: {_stringify(value)}", {key}
        return None, set()

    def _build_conditions_line(self, row: Mapping[str, Any]) -> tuple[str | None, set[str]]:
        used_keys: set[str] = set()
        parts: list[str] = []
        for label, keys in CONDITION_PARTS:
            values: list[str] = []
            group_keys: set[str] = set()
            for key in keys:
                text = _stringify(row.get(key))
                if not text or _is_skippable_text(text):
                    continue
                if text not in values:
                    values.append(text)
                group_keys.add(key)
            if values:
                used_keys.update(group_keys)
                combined = " / ".join(values[:2])
                parts.append(f"{label} {combined}")
        if parts:
            return f"Conditions: {'; '.join(parts)}", used_keys
        return None, set()

    def _build_context_line(self, row: Mapping[str, Any]) -> tuple[str | None, set[str]]:
        used_keys: set[str] = set()
        flags: list[str] = []
        for key, label in FLAG_FIELDS:
            truthy = _is_truthy(row.get(key))
            if truthy is True:
                flags.append(label)
                used_keys.add(key)

        deer_entry = self._first_value(row, ("deer_number",), skip_zero=True)
        if deer_entry:
            deer_key, deer_value = deer_entry
            deer_count = _coerce_number(_stringify(deer_value))
            if deer_count is not None and deer_count > 0:
                used_keys.add(deer_key)
                if flags:
                    flags.append(f"Deer involved {int(deer_count)}")
                else:
                    return f"Deer involved: {int(deer_count)}", used_keys

        if flags:
            return f"Flags: {'; '.join(flags)}", used_keys
        return None, set()

    def _build_damage_line(self, row: Mapping[str, Any]) -> tuple[str | None, set[str]]:
        damage_entry = self._first_value(row, DAMAGE_FIELDS)
        if damage_entry:
            key, value = damage_entry
            text = _stringify(value)
            return f"Damage: {text}", {key}
        return None, set()

    def _extract_narrative_text(self, row: Mapping[str, Any]) -> tuple[str | None, set[str]]:
        candidates: list[tuple[int, str, str]] = []
        for key in NARRATIVE_FIELDS:
            text = _stringify(row.get(key))
            if text:
                candidates.append((len(text), key, text))
        if not candidates:
            return None, set()
        candidates.sort(reverse=True)
        _length, key, text = candidates[0]
        return text, {key}

    def _select_additional_fields(
        self,
        row: Mapping[str, Any],
        *,
        used_keys: set[str],
        limit: int,
    ) -> list[str]:
        if limit <= 0:
            return []

        candidates: list[tuple[int, str, str]] = []
        for key, value in row.items():
            if key in used_keys or key in EXCLUDED_KEYS:
                continue
            if key.endswith("_id") and key not in IDENTIFIER_KEYS:
                continue
            if key in NARRATIVE_FIELDS or _has_long_text_hint(key):
                continue
            text = _stringify(value)
            if not text or _is_skippable_text(text):
                continue
            if _is_zeroish(text):
                continue
            score = self._score_field(key, text)
            candidates.append((score, key, text))

        candidates.sort(key=lambda item: (-item[0], item[1]))
        lines: list[str] = []
        for _score, key, text in candidates[:limit]:
            trimmed = _truncate_text(text, self.config.max_value_chars)
            lines.append(f"{_label_for_key(key)}: {trimmed}")
        return lines

    def _score_field(self, key: str, text: str) -> int:
        score = 0
        for weight, tokens in FIELD_SCORE_RULES:
            if any(token in key for token in tokens):
                score += weight
                break
        if key.endswith("_id"):
            score -= 25
        if len(text) <= 12:
            score += 6
        elif len(text) <= 24:
            score += 3
        return score

    def _wrap_lines(
        self,
        lines: Sequence[str],
        font_name: str,
        font_size: int,
        max_width: float,
    ) -> list[str]:
        wrapped: list[str] = []
        for line in lines:
            wrapped.extend(self._wrap_line(line, font_name, font_size, max_width))
        return wrapped

    def _wrap_paragraph(
        self,
        text: str,
        font_name: str,
        font_size: int,
        max_width: float,
        *,
        prefix: str = "Narrative: ",
    ) -> list[str]:
        words = text.split()
        if not words:
            return [prefix.strip()]
        wrapped: list[str] = []
        current = f"{prefix}{words[0]}"
        for word in words[1:]:
            candidate = f"{current} {word}"
            if self._string_width(candidate, font_name, font_size) <= max_width:
                current = candidate
            else:
                wrapped.append(current)
                current = f"    {word}"
        wrapped.append(current)
        return wrapped

    def _fit_text_blocks(
        self,
        summary_lines: list[str],
        narrative_text: str,
        font_name: str,
        summary_font_size: int,
        narrative_font_size: int,
        narrative_min_size: int,
        max_width: float,
        available_height: float,
    ) -> tuple[list[str], list[str], int]:
        summary_leading = self.config.bullet_leading
        narrative_leading = self.config.narrative_leading

        def total_height(summary_count: int, narrative_count: int, narrative_size: int) -> float:
            gap = self.config.narrative_gap if summary_count and narrative_count else 0.0
            scaled_leading = narrative_leading * (narrative_size / max(summary_font_size, 1))
            return (summary_count * summary_leading) + gap + (narrative_count * scaled_leading)

        summary_wrapped = summary_lines
        narrative_wrapped = self._wrap_paragraph(narrative_text, font_name, narrative_font_size, max_width)

        while total_height(len(summary_wrapped), len(narrative_wrapped), narrative_font_size) > available_height:
            if summary_wrapped:
                summary_wrapped = summary_wrapped[:-1]
                continue
            if narrative_font_size <= narrative_min_size:
                break
            narrative_font_size -= 1
            narrative_wrapped = self._wrap_paragraph(
                narrative_text,
                font_name,
                narrative_font_size,
                max_width,
            )

        return summary_wrapped, narrative_wrapped, narrative_font_size

    def _wrap_line(
        self,
        line: str,
        font_name: str,
        font_size: int,
        max_width: float,
    ) -> list[str]:
        words = line.split()
        if not words:
            return []
        wrapped: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if self._string_width(candidate, font_name, font_size) <= max_width:
                current = candidate
            else:
                wrapped.append(current)
                current = f"    {word}"  # indent wrapped lines
        wrapped.append(current)
        return [f"- {text}" if idx == 0 else text for idx, text in enumerate(wrapped)]

    @staticmethod
    def _string_width(text: str, font_name: str, font_size: int) -> float:
        return pdfmetrics.stringWidth(text, font_name, font_size)


def _normalize_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {_normalize_header(key): value for key, value in row.items()}


def _human_label(key: str) -> str:
    parts = key.replace("_", " ").split()
    normalized_parts = []
    for part in parts:
        if part.upper() in {"ID", "UID", "GPS"}:
            normalized_parts.append(part.upper())
        else:
            normalized_parts.append(part.capitalize())
    return " ".join(normalized_parts)


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, datetime):
        if value.time() == time(0, 0):
            return value.strftime("%Y-%m-%d")
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        if value.is_integer():
            return str(int(value))
        return f"{value:.2f}".rstrip("0").rstrip(".")
    if isinstance(value, int):
        return str(value)
    text = str(value).strip()
    if not text:
        return ""
    lowered = text.lower()
    if lowered in {"nan", "none", "null"}:
        return ""
    if lowered in {"y", "yes", "true", "t"}:
        return "Yes"
    if lowered in {"n", "no", "false", "f"}:
        return "No"
    return " ".join(text.split())


def _label_for_key(key: str) -> str:
    return LABEL_OVERRIDES.get(key, _human_label(key))


def _is_skippable_text(text: str) -> bool:
    return text.strip().lower() in SKIP_TEXT_VALUES


def _format_kmz_label(value: Any) -> str | None:
    text = _stringify(value)
    if not text:
        return None
    match = re.search(r"\d+", text)
    if match:
        return match.group(0)
    return text


def _coerce_number(text: str) -> float | None:
    if text is None:
        return None
    cleaned = str(text).replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _is_zeroish(text: str) -> bool:
    number = _coerce_number(text)
    return number is not None and abs(number) < 1e-9


def _is_truthy(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"y", "yes", "true", "1"}:
        return True
    if text in {"n", "no", "false", "0"}:
        return False
    return None


def _truncate_text(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    return textwrap.shorten(text, width=max_chars, placeholder="...")


def _has_long_text_hint(key: str) -> bool:
    return any(hint in key for hint in LONG_TEXT_HINTS)
