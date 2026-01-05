"""Generate a one-page PDF summary report for refined crash data."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time
import math
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

from .geo import BoundaryFilterReport
from .refiner import _normalize_header


DATE_TIME_FIELDS: Sequence[str] = (
    "crash_date_time",
    "collision_date_time",
    "crash_datetime",
    "timestamp",
)
DATE_FIELDS: Sequence[str] = (
    "crash_date",
    "collision_date",
    "date",
    "report_date",
)
TIME_FIELDS: Sequence[str] = (
    "time_of_crash",
    "time",
    "hour_of_collision_timestamp",
    "crash_time",
)
SEVERITY_FIELDS: Sequence[str] = (
    "crash_severity_calc",
    "injury_severity",
    "severity",
    "crash_severity",
)
COLLISION_FIELDS: Sequence[str] = (
    "manner_of_collision",
    "collision_type",
    "crash_type",
    "collision_manner",
)
PRIMARY_FACTOR_FIELDS: Sequence[str] = ("primary_factor", "primary_cause")
CONTRIBUTING_FACTOR_FIELDS: Sequence[str] = ("contributing_factor", "secondary_factor", "contributing_cause")
LOCATION_FIELDS: Sequence[str] = (
    "roadway_name",
    "road_name",
    "street_name",
    "route",
    "roadway_number",
    "location",
    "address",
    "intersection",
    "cross_street",
    "city",
    "county",
)
CONDITION_FIELDS: Sequence[tuple[str, Sequence[str]]] = (
    ("Weather", ("weather", "weather_condition", "weather_cond")),
    ("Surface", ("surface_condition", "surface_type", "road_surface")),
    ("Light", ("light_condition", "lighting")),
)
INJURY_COUNT_FIELDS: Sequence[tuple[str, Sequence[str]]] = (
    ("Fatal", ("fatalities", "injury_fatal_number", "fatal_injuries", "fatal_count")),
    ("Serious", ("serious_injuries", "inj_incapacitating_number", "incapacitating_injuries")),
    ("Minor", ("minor_injuries", "inj_nonincapacitating_number", "nonincapacitating_injuries")),
    ("Possible", ("inj_possible_number", "possible_injuries")),
)
SKIP_TEXT_VALUES = {
    "none",
    "null",
    "nan",
    "n/a",
    "na",
    "unknown",
    "unspecified",
    "not reported",
    "no",
}

PAGE_BG = colors.Color(0.96, 0.97, 0.98)
CARD_BG = colors.Color(1, 1, 1)
CARD_BORDER = colors.Color(0.84, 0.88, 0.92)
CARD_SHADOW = colors.Color(0.82, 0.86, 0.9)
ACCENT = colors.Color(0.13, 0.28, 0.42)
ACCENT_SOFT = colors.Color(0.88, 0.92, 0.96)
TEXT = colors.Color(0.12, 0.14, 0.17)
MUTED = colors.Color(0.44, 0.49, 0.54)


@dataclass
class SummaryReportConfig:
    title: str = "Crash Data Summary"
    page_size: tuple[float, float] = letter
    margin: float = 0.55 * inch
    header_height: float = 0.95 * inch
    metrics_height: float = 1.05 * inch
    row_gap: float = 0.2 * inch
    column_gap: float = 0.25 * inch
    header_font: str = "Helvetica-Bold"
    body_font: str = "Helvetica"
    title_size: int = 20
    subtitle_size: int = 10
    metric_value_size: int = 18
    metric_label_size: int = 9
    panel_title_size: int = 11
    body_size: int = 9


def generate_summary_report(
    path: str,
    *,
    rows: Sequence[Mapping[str, Any]],
    latitude_column: str | None = None,
    longitude_column: str | None = None,
    boundary_report: BoundaryFilterReport | None = None,
    source_name: str | None = None,
    config: SummaryReportConfig | None = None,
) -> Path:
    pdf_path = Path(path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    builder = SummaryReportPDFBuilder(config or SummaryReportConfig())
    builder.render(
        pdf_path,
        rows,
        latitude_column=latitude_column,
        longitude_column=longitude_column,
        boundary_report=boundary_report,
        source_name=source_name,
    )
    return pdf_path


class SummaryReportPDFBuilder:
    def __init__(self, config: SummaryReportConfig) -> None:
        self.config = config

    def render(
        self,
        pdf_path: Path,
        rows: Sequence[Mapping[str, Any]],
        *,
        latitude_column: str | None,
        longitude_column: str | None,
        boundary_report: BoundaryFilterReport | None,
        source_name: str | None,
    ) -> None:
        canvas_obj = canvas.Canvas(str(pdf_path), pagesize=self.config.page_size)
        width, height = self.config.page_size
        canvas_obj.setFillColor(PAGE_BG)
        canvas_obj.rect(0, 0, width, height, stroke=0, fill=1)

        stats = _analyze_rows(
            rows,
            latitude_column=latitude_column,
            longitude_column=longitude_column,
        )

        margin = self.config.margin
        content_width = width - (margin * 2)
        top = height - margin

        header_top = top
        header_bottom = header_top - self.config.header_height
        self._draw_header(
            canvas_obj,
            x=margin,
            y=header_bottom,
            width=content_width,
            height=self.config.header_height,
            stats=stats,
            boundary_report=boundary_report,
            source_name=source_name,
        )

        metrics_top = header_bottom - self.config.row_gap
        metrics_bottom = metrics_top - self.config.metrics_height
        self._draw_metrics_row(
            canvas_obj,
            x=margin,
            y=metrics_bottom,
            width=content_width,
            height=self.config.metrics_height,
            stats=stats,
        )

        panel_top = metrics_bottom - self.config.row_gap
        panel_bottom = margin
        panel_height = panel_top - panel_bottom
        row_height = (panel_height - self.config.row_gap) / 2
        col_width = (content_width - self.config.column_gap) / 2

        row1_bottom = panel_top - row_height
        row2_bottom = panel_bottom

        col1_x = margin
        col2_x = margin + col_width + self.config.column_gap

        self._draw_severity_panel(
            canvas_obj,
            x=col1_x,
            y=row1_bottom,
            width=col_width,
            height=row_height,
            stats=stats,
        )
        self._draw_factors_panel(
            canvas_obj,
            x=col2_x,
            y=row1_bottom,
            width=col_width,
            height=row_height,
            stats=stats,
        )
        self._draw_time_panel(
            canvas_obj,
            x=col1_x,
            y=row2_bottom,
            width=col_width,
            height=row_height,
            stats=stats,
        )
        self._draw_location_panel(
            canvas_obj,
            x=col2_x,
            y=row2_bottom,
            width=col_width,
            height=row_height,
            stats=stats,
        )

        canvas_obj.setFillColor(MUTED)
        canvas_obj.setFont(self.config.body_font, 8.5)
        footer = "Summary reflects crashes included within the relevance boundary."
        canvas_obj.drawString(margin, margin - 12, footer)
        canvas_obj.save()

    def _draw_header(
        self,
        canvas_obj: canvas.Canvas,
        *,
        x: float,
        y: float,
        width: float,
        height: float,
        stats: dict[str, Any],
        boundary_report: BoundaryFilterReport | None,
        source_name: str | None,
    ) -> None:
        self._draw_card(canvas_obj, x, y, width, height, radius=12)
        accent_width = min(20, width * 0.06)
        canvas_obj.setFillColor(ACCENT)
        canvas_obj.roundRect(x, y, accent_width, height, 12, fill=1, stroke=0)

        title_x = x + accent_width + 14
        title_y = y + height - 28
        canvas_obj.setFillColor(TEXT)
        canvas_obj.setFont(self.config.header_font, self.config.title_size)
        canvas_obj.drawString(title_x, title_y, self.config.title)

        canvas_obj.setFont(self.config.body_font, self.config.subtitle_size)
        subtitle = "Included crashes inside the relevance boundary"
        canvas_obj.setFillColor(MUTED)
        canvas_obj.drawString(title_x, title_y - 18, subtitle)

        right_x = x + width - 16
        now_text = datetime.now().strftime("%Y-%m-%d %H:%M")
        canvas_obj.setFillColor(MUTED)
        canvas_obj.setFont(self.config.body_font, 9)
        canvas_obj.drawRightString(right_x, title_y, f"Generated: {now_text}")

        if source_name:
            canvas_obj.drawRightString(right_x, title_y - 16, f"Source: {source_name}")

        boundary_text = _build_boundary_text(boundary_report, stats["total"])
        if boundary_text:
            canvas_obj.setFont(self.config.body_font, 8.8)
            canvas_obj.setFillColor(TEXT)
            canvas_obj.drawString(title_x, y + 14, boundary_text)

    def _draw_metrics_row(
        self,
        canvas_obj: canvas.Canvas,
        *,
        x: float,
        y: float,
        width: float,
        height: float,
        stats: dict[str, Any],
    ) -> None:
        gap = 10
        card_width = (width - (gap * 3)) / 4
        metrics = _build_key_metrics(stats)
        for idx, metric in enumerate(metrics):
            card_x = x + idx * (card_width + gap)
            self._draw_metric_card(canvas_obj, card_x, y, card_width, height, metric)

    def _draw_metric_card(
        self,
        canvas_obj: canvas.Canvas,
        x: float,
        y: float,
        width: float,
        height: float,
        metric: dict[str, str],
    ) -> None:
        self._draw_card(canvas_obj, x, y, width, height, radius=10)
        canvas_obj.setFillColor(MUTED)
        canvas_obj.setFont(self.config.body_font, self.config.metric_label_size)
        canvas_obj.drawString(x + 12, y + height - 18, metric["label"])

        canvas_obj.setFillColor(TEXT)
        canvas_obj.setFont(self.config.header_font, self.config.metric_value_size)
        canvas_obj.drawString(x + 12, y + height - 42, metric["value"])

        detail = metric.get("detail")
        if detail:
            canvas_obj.setFillColor(MUTED)
            canvas_obj.setFont(self.config.body_font, 8.5)
            canvas_obj.drawString(x + 12, y + 14, detail)

    def _draw_severity_panel(
        self,
        canvas_obj: canvas.Canvas,
        *,
        x: float,
        y: float,
        width: float,
        height: float,
        stats: dict[str, Any],
    ) -> None:
        self._draw_panel(canvas_obj, x, y, width, height, "Severity and Injuries")
        padding = 14
        title_space = 22
        inner_x = x + padding
        inner_y = y + padding
        inner_width = width - (padding * 2)
        inner_height = height - (padding * 2) - title_space
        chart_height = inner_height * 0.62
        detail_height = inner_height - chart_height - 6

        self._draw_bar_chart(
            canvas_obj,
            x=inner_x,
            y=inner_y + detail_height + 6,
            width=inner_width,
            height=chart_height,
            items=stats["severity_items"],
            total=stats["total"],
            color=ACCENT,
        )

        detail_y = inner_y + 2
        canvas_obj.setFont(self.config.body_font, 8.6)
        canvas_obj.setFillColor(TEXT)
        injury_text = _build_injury_text(stats["injury_totals"])
        if injury_text:
            canvas_obj.drawString(inner_x, detail_y + detail_height - 10, injury_text)

        condition_text = _build_condition_text(stats["conditions"])
        if condition_text:
            canvas_obj.setFillColor(MUTED)
            canvas_obj.setFont(self.config.body_font, 8.4)
            canvas_obj.drawString(inner_x, detail_y + 4, condition_text)

    def _draw_factors_panel(
        self,
        canvas_obj: canvas.Canvas,
        *,
        x: float,
        y: float,
        width: float,
        height: float,
        stats: dict[str, Any],
    ) -> None:
        title = stats.get("factor_title") or "Top Factors"
        self._draw_panel(canvas_obj, x, y, width, height, title)
        padding = 14
        title_space = 22
        inner_x = x + padding
        inner_y = y + padding
        inner_width = width - (padding * 2)
        inner_height = height - (padding * 2) - title_space
        self._draw_bar_chart(
            canvas_obj,
            x=inner_x,
            y=inner_y,
            width=inner_width,
            height=inner_height,
            items=stats["factor_items"],
            total=stats["factor_total"],
            color=colors.Color(0.2, 0.55, 0.35),
        )

    def _draw_time_panel(
        self,
        canvas_obj: canvas.Canvas,
        *,
        x: float,
        y: float,
        width: float,
        height: float,
        stats: dict[str, Any],
    ) -> None:
        title = stats.get("time_title") or "Time of Day"
        self._draw_panel(canvas_obj, x, y, width, height, title)
        padding = 14
        title_space = 22
        inner_x = x + padding
        inner_y = y + padding
        inner_width = width - (padding * 2)
        inner_height = height - (padding * 2) - title_space
        self._draw_bar_chart(
            canvas_obj,
            x=inner_x,
            y=inner_y,
            width=inner_width,
            height=inner_height,
            items=stats["time_items"],
            total=stats["time_total"],
            color=colors.Color(0.33, 0.45, 0.68),
        )

    def _draw_location_panel(
        self,
        canvas_obj: canvas.Canvas,
        *,
        x: float,
        y: float,
        width: float,
        height: float,
        stats: dict[str, Any],
    ) -> None:
        title = stats.get("location_title") or "Top Locations"
        self._draw_panel(canvas_obj, x, y, width, height, title)
        padding = 14
        title_space = 22
        inner_x = x + padding
        inner_y = y + padding
        inner_width = width - (padding * 2)
        inner_height = height - (padding * 2) - title_space
        self._draw_bar_chart(
            canvas_obj,
            x=inner_x,
            y=inner_y,
            width=inner_width,
            height=inner_height,
            items=stats["location_items"],
            total=stats["location_total"],
            color=colors.Color(0.55, 0.42, 0.22),
        )

    def _draw_panel(
        self,
        canvas_obj: canvas.Canvas,
        x: float,
        y: float,
        width: float,
        height: float,
        title: str,
    ) -> None:
        self._draw_card(canvas_obj, x, y, width, height, radius=12)
        canvas_obj.setFillColor(ACCENT_SOFT)
        canvas_obj.roundRect(x, y + height - 28, width, 28, 12, fill=1, stroke=0)
        canvas_obj.setFillColor(TEXT)
        canvas_obj.setFont(self.config.header_font, self.config.panel_title_size)
        canvas_obj.drawString(x + 14, y + height - 20, title)

    def _draw_bar_chart(
        self,
        canvas_obj: canvas.Canvas,
        *,
        x: float,
        y: float,
        width: float,
        height: float,
        items: Sequence[tuple[str, int]],
        total: int,
        color: colors.Color,
    ) -> None:
        if not items:
            canvas_obj.setFillColor(MUTED)
            canvas_obj.setFont(self.config.body_font, 9)
            canvas_obj.drawString(x, y + height / 2, "No data available")
            return

        max_value = max((value for _label, value in items), default=0)
        if max_value <= 0:
            canvas_obj.setFillColor(MUTED)
            canvas_obj.setFont(self.config.body_font, 9)
            canvas_obj.drawString(x, y + height / 2, "No data available")
            return

        label_width = min(max(width * 0.42, 90), width * 0.55)
        value_width = 46
        bar_x = x + label_width
        bar_width = max(width - label_width - value_width - 6, 40)
        row_height = height / max(len(items), 1)
        bar_height = max(min(row_height * 0.36, 12), 6)

        canvas_obj.setFont(self.config.body_font, 8.8)
        for index, (label, value) in enumerate(items):
            row_top = y + height - (index * row_height)
            label_y = row_top - (row_height * 0.65)
            bar_y = row_top - (row_height * 0.86)

            canvas_obj.setFillColor(TEXT)
            trimmed = _truncate_to_width(label, label_width - 6, self.config.body_font, 8.8)
            canvas_obj.drawString(x, label_y, trimmed)

            ratio = value / max_value if max_value else 0
            filled = bar_width * ratio
            canvas_obj.setFillColor(CARD_BORDER)
            canvas_obj.rect(bar_x, bar_y, bar_width, bar_height, stroke=0, fill=1)
            canvas_obj.setFillColor(color)
            canvas_obj.rect(bar_x, bar_y, filled, bar_height, stroke=0, fill=1)

            percent = _format_percent(value, total)
            value_text = f"{_format_int(value)} {percent}"
            canvas_obj.setFillColor(MUTED)
            canvas_obj.drawRightString(bar_x + bar_width + value_width, label_y, value_text)

    def _draw_card(
        self,
        canvas_obj: canvas.Canvas,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        radius: float,
    ) -> None:
        canvas_obj.setFillColor(CARD_SHADOW)
        canvas_obj.roundRect(x + 2.5, y - 2.5, width, height, radius, fill=1, stroke=0)
        canvas_obj.setFillColor(CARD_BG)
        canvas_obj.roundRect(x, y, width, height, radius, fill=1, stroke=0)
        canvas_obj.setStrokeColor(CARD_BORDER)
        canvas_obj.roundRect(x, y, width, height, radius, fill=0, stroke=1)


def _analyze_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    latitude_column: str | None,
    longitude_column: str | None,
) -> dict[str, Any]:
    normalized_rows = [_normalize_row(row) for row in rows]
    total = len(normalized_rows)

    severity_counts = Counter()
    for row in normalized_rows:
        text = _first_value(row, SEVERITY_FIELDS)
        if not text:
            continue
        severity_counts[_classify_severity(text)] += 1

    injury_totals = {label: 0 for label, _keys in INJURY_COUNT_FIELDS}
    for row in normalized_rows:
        for label, keys in INJURY_COUNT_FIELDS:
            value = _first_value(row, keys, allow_zero=True)
            number = _coerce_number(value)
            if number is None:
                continue
            injury_totals[label] += int(round(number))

    factor_title, factor_counts = _select_group_counts(
        normalized_rows,
        [
            ("Primary Factors", PRIMARY_FACTOR_FIELDS),
            ("Collision Types", COLLISION_FIELDS),
            ("Contributing Factors", CONTRIBUTING_FACTOR_FIELDS),
        ],
    )

    location_title, location_counts = _select_group_counts(
        normalized_rows,
        [
            ("Roadway", LOCATION_FIELDS),
        ],
    )

    conditions = {}
    for label, keys in CONDITION_FIELDS:
        counts = _count_values(normalized_rows, keys)
        top = _top_item(counts)
        if top:
            conditions[label] = top

    date_values: list[date] = []
    weekday_counts = Counter()
    time_bins = Counter()
    for row in normalized_rows:
        date_value = _extract_date(row)
        if date_value:
            date_values.append(date_value)
            weekday_counts[date_value.strftime("%a")] += 1
        time_value = _extract_time(row)
        if time_value:
            time_bins[_time_bin_label(time_value)] += 1

    time_items: list[tuple[str, int]]
    time_title = "Time of Day"
    if time_bins:
        time_items = [(label, time_bins.get(label, 0)) for label in _time_bin_labels()]
        time_total = sum(time_bins.values())
    elif weekday_counts:
        time_title = "Day of Week"
        order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        time_items = [(label, weekday_counts.get(label, 0)) for label in order]
        time_total = sum(weekday_counts.values())
    else:
        time_items = []
        time_total = 0

    date_range = _format_date_range(date_values)
    severity_items = _ordered_severity(severity_counts)
    factor_items = _top_items(factor_counts, limit=6)
    location_items = _top_items(location_counts, limit=6)

    return {
        "total": total,
        "date_range": date_range,
        "severity_items": severity_items,
        "factor_items": factor_items,
        "factor_total": sum(factor_counts.values()),
        "factor_title": factor_title,
        "location_items": location_items,
        "location_total": sum(location_counts.values()),
        "location_title": location_title,
        "conditions": conditions,
        "injury_totals": injury_totals,
        "time_items": time_items,
        "time_total": time_total,
        "time_title": time_title,
    }


def _normalize_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {_normalize_header(key): value for key, value in row.items()}


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
    return " ".join(text.split())


def _is_skippable(text: str) -> bool:
    return text.strip().lower() in SKIP_TEXT_VALUES


def _coerce_number(text: Any) -> float | None:
    if text is None:
        return None
    cleaned = str(text).replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _first_value(row: Mapping[str, Any], keys: Sequence[str], *, allow_zero: bool = False) -> str:
    for key in keys:
        text = _stringify(row.get(key))
        if not text or _is_skippable(text):
            continue
        if not allow_zero and _is_zeroish(text):
            continue
        return _pretty_text(text)
    return ""


def _pretty_text(text: str) -> str:
    cleaned = " ".join(text.split())
    if cleaned.isupper() and len(cleaned) > 3:
        return cleaned.title()
    return cleaned


def _count_values(rows: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in rows:
        text = _first_value(row, keys)
        if text:
            counts[text] += 1
    return counts


def _select_group_counts(
    rows: Sequence[Mapping[str, Any]],
    groups: Sequence[tuple[str, Sequence[str]]],
) -> tuple[str, Counter[str]]:
    best_title = ""
    best_counts: Counter[str] = Counter()
    best_total = 0
    for title, keys in groups:
        counts = _count_values(rows, keys)
        total = sum(counts.values())
        if total > best_total:
            best_title = title
            best_counts = counts
            best_total = total
    return best_title, best_counts


def _top_items(counts: Counter[str], *, limit: int) -> list[tuple[str, int]]:
    items = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return items[:limit]


def _top_item(counts: Counter[str]) -> tuple[str, int] | None:
    if not counts:
        return None
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0]


def _ordered_severity(counts: Counter[str]) -> list[tuple[str, int]]:
    order = ["Fatal", "Serious", "Minor", "Possible", "Property Damage", "Other/Unknown"]
    items = [(label, counts.get(label, 0)) for label in order if counts.get(label, 0) > 0]
    if not items and counts:
        items = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return items


def _classify_severity(text: str) -> str:
    lowered = text.lower()
    if "fatal" in lowered:
        return "Fatal"
    if "serious" in lowered or "incapac" in lowered:
        return "Serious"
    if "minor" in lowered or "non-incapac" in lowered or "non incapac" in lowered:
        return "Minor"
    if "possible" in lowered:
        return "Possible"
    if "property" in lowered or "pdo" in lowered or "no injury" in lowered:
        return "Property Damage"
    return "Other/Unknown"


def _parse_datetime_value(value: Any) -> tuple[datetime | None, bool]:
    if value is None:
        return None, False
    if isinstance(value, datetime):
        has_time = value.time() != time(0, 0)
        return value, has_time
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime.combine(value, time(0, 0)), False
    text = _stringify(value)
    if not text:
        return None, False
    cleaned = text.replace("T", " ")
    cleaned = re.split(r"[Zz]|[+-]\d{2}:?\d{2}$", cleaned)[0]
    cleaned = cleaned.split(".")[0].strip()
    date_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %I:%M %p",
        "%Y-%m-%d %I:%M:%S %p",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y %I:%M %p",
        "%m/%d/%Y %I:%M:%S %p",
    ]
    for fmt in date_formats:
        try:
            return datetime.strptime(cleaned, fmt), True
        except ValueError:
            continue
    date_only = _parse_date_text(cleaned)
    if date_only:
        return datetime.combine(date_only, time(0, 0)), False
    return None, False


def _parse_date_text(text: str) -> date | None:
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _parse_time_text(text: str) -> time | None:
    if not text:
        return None
    cleaned = text.split(".")[0].strip()
    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M:%S %p"):
        try:
            return datetime.strptime(cleaned, fmt).time()
        except ValueError:
            continue
    return None


def _extract_date(row: Mapping[str, Any]) -> date | None:
    for key in DATE_TIME_FIELDS:
        value = row.get(key)
        dt, _has_time = _parse_datetime_value(value)
        if dt:
            return dt.date()
    for key in DATE_FIELDS:
        value = row.get(key)
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        text = _stringify(value)
        parsed = _parse_date_text(text)
        if parsed:
            return parsed
    return None


def _extract_time(row: Mapping[str, Any]) -> time | None:
    for key in DATE_TIME_FIELDS:
        value = row.get(key)
        dt, has_time = _parse_datetime_value(value)
        if dt and has_time:
            return dt.time()
    for key in TIME_FIELDS:
        value = row.get(key)
        if isinstance(value, time):
            return value
        if isinstance(value, datetime):
            return value.time() if value.time() != time(0, 0) else None
        text = _stringify(value)
        parsed = _parse_time_text(text)
        if parsed:
            return parsed
    return None


def _time_bin_label(time_value: time) -> str:
    hour = time_value.hour
    if 0 <= hour < 4:
        return "12a-4a"
    if 4 <= hour < 8:
        return "4a-8a"
    if 8 <= hour < 12:
        return "8a-12p"
    if 12 <= hour < 16:
        return "12p-4p"
    if 16 <= hour < 20:
        return "4p-8p"
    return "8p-12a"


def _time_bin_labels() -> list[str]:
    return ["12a-4a", "4a-8a", "8a-12p", "12p-4p", "4p-8p", "8p-12a"]


def _is_zeroish(text: str) -> bool:
    number = _coerce_number(text)
    return number is not None and abs(number) < 1e-9


def _format_date_range(dates: Sequence[date]) -> str:
    if not dates:
        return "Date range unavailable"
    start = min(dates)
    end = max(dates)
    if start == end:
        return start.strftime("%Y-%m-%d")
    return f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}"


def _build_key_metrics(stats: Mapping[str, Any]) -> list[dict[str, str]]:
    metrics = []
    total = stats.get("total", 0)
    metrics.append({
        "label": "Included crashes",
        "value": _format_int(total),
        "detail": "Within relevance boundary",
    })

    metrics.append({
        "label": "Date range",
        "value": stats.get("date_range") or "Date range unavailable",
        "detail": "",
    })

    top_severity = _top_item(Counter(dict(stats.get("severity_items", []))))
    if top_severity:
        label, value = top_severity
        metrics.append({
            "label": "Top severity",
            "value": f"{label} {_format_percent(value, total)}".strip(),
            "detail": "Most common severity",
        })
    else:
        metrics.append({
            "label": "Top severity",
            "value": "Not available",
            "detail": "Severity data missing",
        })

    peak_label = _peak_time_label(stats.get("time_items") or [])
    if peak_label:
        metrics.append({
            "label": "Peak period",
            "value": peak_label,
            "detail": "Highest crash volume",
        })
    else:
        metrics.append({
            "label": "Peak period",
            "value": "Not available",
            "detail": "Time data missing",
        })

    return metrics[:4]


def _peak_time_label(items: Sequence[tuple[str, int]]) -> str:
    if not items:
        return ""
    label, value = max(items, key=lambda item: item[1])
    if value <= 0:
        return ""
    return label


def _build_injury_text(injury_totals: Mapping[str, int]) -> str:
    parts = []
    for label in ("Fatal", "Serious", "Minor", "Possible"):
        count = injury_totals.get(label, 0)
        if count:
            parts.append(f"{label} {count}")
    if not parts:
        return "Injury counts not reported."
    return "Injury totals: " + " | ".join(parts)


def _build_condition_text(conditions: Mapping[str, tuple[str, int]]) -> str:
    if not conditions:
        return ""
    parts = []
    for label, (value, _count) in conditions.items():
        parts.append(f"{label}: {value}")
    return "Conditions: " + " | ".join(parts)


def _build_boundary_text(report: BoundaryFilterReport | None, total: int) -> str:
    if report:
        return (
            f"Rows scanned: {_format_int(report.total_rows)} | "
            f"Included: {_format_int(report.included_rows)} | "
            f"Excluded: {_format_int(report.excluded_rows)} | "
            f"Invalid: {_format_int(report.invalid_rows)}"
        )
    if total:
        return f"Included crashes: {_format_int(total)}"
    return ""


def _format_int(value: int | float | None) -> str:
    if value is None:
        return "0"
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return "0"
    return f"{number:,}"


def _format_percent(value: int, total: int) -> str:
    if total <= 0:
        return ""
    percent = (value / total) * 100
    return f"({percent:.0f}%)"


def _truncate_to_width(text: str, max_width: float, font_name: str, font_size: float) -> str:
    if pdfmetrics.stringWidth(text, font_name, font_size) <= max_width:
        return text
    shortened = text
    while shortened and pdfmetrics.stringWidth(shortened + "...", font_name, font_size) > max_width:
        shortened = shortened[:-1]
    return shortened + "..." if shortened else text[:1]
