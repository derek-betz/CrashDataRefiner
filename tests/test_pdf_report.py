from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from crash_data_refiner import webapp
from crash_data_refiner.pdf_report import AerialTileRenderer, generate_pdf_report
from crash_data_refiner.webapp import RunState


def test_aerial_tile_renderer_reuses_cached_tiles() -> None:
    renderer = AerialTileRenderer(overlay_urls=[], cache_size=4)
    fetch_calls: list[tuple[str, int, int, int, str]] = []

    def fake_fetch_tile_layer(
        url_template: str,
        x: int,
        y: int,
        z: int,
        *,
        convert_mode: str,
    ) -> Image.Image:
        fetch_calls.append((url_template, x, y, z, convert_mode))
        color = (12, 16, 23, 255) if convert_mode == "RGBA" else (12, 16, 23)
        return Image.new(convert_mode, (256, 256), color)

    renderer._fetch_tile_layer = fake_fetch_tile_layer  # type: ignore[method-assign]

    first = renderer._fetch_tile(12, 34, 16)
    second = renderer._fetch_tile(12, 34, 16)

    assert first.size == (256, 256)
    assert second.size == (256, 256)
    assert len(fetch_calls) == 1


def test_generate_pdf_report_reports_page_progress(tmp_path: Path, monkeypatch) -> None:
    progress_events: list[tuple[int, int]] = []

    def fake_render(self: AerialTileRenderer, *args: object, **kwargs: object) -> Image.Image:
        return Image.new("RGB", (320, 320), (255, 255, 255))

    monkeypatch.setattr(AerialTileRenderer, "render", fake_render)

    output_path = tmp_path / "report.pdf"
    rows = [
        {"lat": 40.0, "lon": -86.0, "kmz_label": 1, "crash_id": "1"},
        {"lat": 40.1, "lon": -86.1, "kmz_label": 2, "crash_id": "2"},
        {"lat": 40.2, "lon": -86.2, "kmz_label": 3, "crash_id": "3"},
    ]

    generate_pdf_report(
        str(output_path),
        rows=rows,
        latitude_column="lat",
        longitude_column="lon",
        progress_callback=lambda current, total: progress_events.append((current, total)),
    )

    assert output_path.exists()
    assert progress_events == [(0, 3), (1, 3), (2, 3), (3, 3)]


def test_run_report_job_logs_progress_updates(tmp_path: Path, monkeypatch) -> None:
    state = RunState(run_id="report-progress", created_at=datetime.now(timezone.utc))
    state.output_dir = tmp_path
    source_path = tmp_path / "refined.xlsx"
    source_path.write_text("placeholder", encoding="utf-8")
    output_path = tmp_path / "report.pdf"

    def fake_run_pdf_report(
        *,
        source_path: Path,
        output_path: Path,
        lat_column: str,
        lon_column: str,
        progress_callback=None,
    ) -> None:
        assert source_path.name == "refined.xlsx"
        assert output_path.name == "report.pdf"
        assert lat_column == "Lat"
        assert lon_column == "Lon"
        if progress_callback is not None:
            progress_callback(0, 12)
            progress_callback(1, 12)
            progress_callback(10, 12)
            progress_callback(12, 12)
        output_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(webapp, "run_pdf_report", fake_run_pdf_report)

    webapp._run_report_job(state, source_path, output_path, "Lat", "Lon")

    log_lines = [entry["text"] for entry in state.log_entries]

    assert state.status == "success"
    assert state.message == "PDF report generated."
    assert any("Rendered PDF page 1 of 12." in line for line in log_lines)
    assert any("Rendered PDF page 10 of 12." in line for line in log_lines)
    assert any("Rendered PDF page 12 of 12." in line for line in log_lines)
    assert any(item["name"] == "report.pdf" for item in state.outputs)
