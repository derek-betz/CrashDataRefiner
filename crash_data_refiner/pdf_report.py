"""Generate polished PDF crash reports with aerial imagery and bullet summaries."""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import requests
from PIL import Image, ImageDraw, ImageFilter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

from .geo import parse_coordinate
from .refiner import _normalize_header


DEFAULT_TILE_URL = "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
TILE_SIZE = 256


@dataclass
class CrashReportConfig:
    """Tuning values that influence the generated PDF layout."""

    title: str = "Crash Data Full Report"
    page_size: tuple[float, float] = letter
    margin: float = 0.65 * inch
    header_font: str = "Helvetica-Bold"
    body_font: str = "Helvetica"
    header_size: int = 18
    label_size: int = 13
    map_zoom: int = 17
    map_width_px: int = 1400
    map_height_px: int = 800
    bullet_leading: float = 16.0


class AerialTileRenderer:
    """Render an aerial map around a crash location using ArcGIS World Imagery."""

    def __init__(self, tile_url: str = DEFAULT_TILE_URL, timeout: float = 8.0) -> None:
        self.tile_url = tile_url
        self.timeout = timeout
        self._session = requests.Session()

    def render(self, lat: float | None, lon: float | None, *, width: int, height: int, zoom: int) -> Image.Image:
        if lat is None or lon is None:
            return self._fallback_image(width, height, "Location unavailable")

        center_x, center_y = self._latlon_to_tile(lat, lon, zoom)
        center_px = center_x * TILE_SIZE
        center_py = center_y * TILE_SIZE

        half_w = width / 2
        half_h = height / 2
        min_px = center_px - half_w
        max_px = center_px + half_w
        min_py = center_py - half_h
        max_py = center_py + half_h

        tile_min_x = math.floor(min_px / TILE_SIZE)
        tile_max_x = math.floor(max_px / TILE_SIZE)
        tile_min_y = math.floor(min_py / TILE_SIZE)
        tile_max_y = math.floor(max_py / TILE_SIZE)

        map_image = Image.new("RGB", (width, height), (12, 16, 23))
        tiles = 2**zoom
        for tile_x in range(tile_min_x, tile_max_x + 1):
            wrapped_x = tile_x % tiles
            for tile_y in range(tile_min_y, tile_max_y + 1):
                if tile_y < 0 or tile_y >= tiles:
                    tile_image = self._blank_tile()
                else:
                    tile_image = self._fetch_tile(wrapped_x, tile_y, zoom)
                dest_x = int((tile_x * TILE_SIZE) - min_px)
                dest_y = int((tile_y * TILE_SIZE) - min_py)
                map_image.paste(tile_image, (dest_x, dest_y))

        self._draw_marker(map_image, width // 2, height // 2)
        return map_image

    def _fetch_tile(self, x: int, y: int, z: int) -> Image.Image:
        url = self.tile_url.format(x=x, y=y, z=z)
        try:
            response = self._session.get(url, timeout=self.timeout)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content)).convert("RGB")
        except Exception:
            image = self._blank_tile()
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
    def _draw_marker(image: Image.Image, x: int, y: int) -> None:
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
            map_image = self.renderer.render(
                lat,
                lon,
                width=self.config.map_width_px,
                height=self.config.map_height_px,
                zoom=self.config.map_zoom,
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
        top_height = page_height * 0.46
        map_height = page_height - top_height - (margin * 2)
        content_top = page_height - margin
        panel_width = page_width - (margin * 2)

        self._draw_header(canvas_obj, margin, content_top, panel_width, top_height, index, total)
        bullet_lines = self._build_bullet_lines(row, lat, lon)
        self._draw_bullets(canvas_obj, margin, content_top - 0.8 * inch, panel_width, top_height - inch, bullet_lines)
        self._draw_map(canvas_obj, margin, margin, panel_width, map_height, map_image)

    def _draw_header(self, canvas_obj: canvas.Canvas, x: float, top: float, width: float, height: float, index: int, total: int) -> None:
        canvas_obj.setFillColor(colors.Color(0.07, 0.09, 0.13))
        canvas_obj.roundRect(x, top - height, width, height, 12, fill=1, stroke=0)
        canvas_obj.setFillColor(colors.Color(0.09, 0.13, 0.19))
        canvas_obj.roundRect(x + 6, top - height + 6, width - 12, height - 12, 10, fill=1, stroke=0)

        canvas_obj.setFillColor(colors.white)
        canvas_obj.setFont(self.config.header_font, self.config.header_size)
        canvas_obj.drawString(x + 18, top - 26, self.config.title)
        canvas_obj.setFillColor(colors.Color(0.35, 0.44, 0.55))
        canvas_obj.setFont(self.config.body_font, 11)
        canvas_obj.drawString(x + 18, top - 46, f"Crash {index} of {total}")

    def _draw_bullets(
        self,
        canvas_obj: canvas.Canvas,
        x: float,
        top: float,
        width: float,
        height: float,
        lines: Sequence[str],
    ) -> None:
        padding = 22
        max_width = width - (padding * 2)
        font_name = self.config.body_font
        font_size = self.config.label_size
        wrapped_lines = self._wrap_lines(lines, font_name, font_size, max_width)

        max_line_count = int(height // self.config.bullet_leading)
        overflow = max(0, len(wrapped_lines) - max_line_count)
        display_lines = wrapped_lines[:max_line_count]
        if overflow:
            display_lines.append(f"+ {overflow} more data points available in spreadsheet")

        text_object = canvas_obj.beginText()
        text_object.setTextOrigin(x + padding, top)
        text_object.setFont(font_name, font_size)
        text_object.setFillColor(colors.white)
        for line in display_lines:
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
    ) -> None:
        canvas_obj.setFillColor(colors.Color(0.06, 0.08, 0.12))
        canvas_obj.roundRect(x, y, width, height, 12, fill=1, stroke=0)
        canvas_obj.setFillColor(colors.Color(0.09, 0.13, 0.19))
        canvas_obj.roundRect(x + 6, y + 6, width - 12, height - 12, 10, fill=1, stroke=0)

        inset_x = x + 12
        inset_y = y + 18
        inset_width = width - 24
        inset_height = height - 42

        softened = map_image.filter(ImageFilter.GaussianBlur(radius=0.35))
        map_reader = ImageReader(softened)
        canvas_obj.drawImage(
            map_reader,
            inset_x,
            inset_y,
            width=inset_width,
            height=inset_height,
            preserveAspectRatio=True,
            anchor="sw",
        )

        canvas_obj.setFillColor(colors.Color(0.35, 0.44, 0.55))
        canvas_obj.setFont(self.config.body_font, 10)
        canvas_obj.drawString(x + 18, y + 10, "Google Earth-style aerial with crash pin")

    def _build_bullet_lines(
        self,
        row: Mapping[str, Any],
        lat: float | None,
        lon: float | None,
    ) -> list[str]:
        prioritized = self._prioritized_fields(row)
        remaining_keys = [
            key
            for key in row.keys()
            if key not in prioritized and key not in {"latitude", "longitude", "kmz_label"}
        ]
        remaining_keys.sort()

        bullets: list[str] = []
        bullets.extend(self._format_fields(row, prioritized))
        bullets.extend(self._format_fields(row, remaining_keys))

        if lat is not None and lon is not None:
            bullets.insert(0, f"Coordinates: {lat:.5f} deg, {lon:.5f} deg")
        return bullets

    def _format_fields(self, row: Mapping[str, Any], keys: Iterable[str]) -> list[str]:
        formatted: list[str] = []
        for key in keys:
            value = row.get(key)
            text = _stringify(value)
            if not text:
                continue
            label = _human_label(key)
            formatted.append(f"{label}: {text}")
        return formatted

    def _prioritized_fields(self, row: Mapping[str, Any]) -> list[str]:
        candidates: Sequence[Sequence[str]] = (
            ("crash_id", "report_number", "case_number", "collision_id", "event_number"),
            ("crash_date_time", "crash_date", "collision_date", "date", "time_of_crash", "time"),
            ("city", "municipality", "county", "state"),
            (
                "location",
                "address",
                "street_name",
                "road_name",
                "route",
                "intersection",
                "cross_street",
            ),
            (
                "injury_severity",
                "severity",
                "fatalities",
                "serious_injuries",
                "minor_injuries",
                "injuries",
                "property_damage",
            ),
            ("weather", "road_surface", "lighting", "work_zone", "workzone"),
            ("collision_type", "manner_of_collision", "primary_factor", "contributing_factor"),
        )

        prioritized: list[str] = []
        for group in candidates:
            for key in group:
                if key in row and _stringify(row.get(key)):
                    prioritized.append(key)
                    break
        return prioritized

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
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text
