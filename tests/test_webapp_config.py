from __future__ import annotations

import importlib
from pathlib import Path


def test_webapp_uses_programdata_friendly_env_overrides(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CDR_OUTPUT_ROOT", str(tmp_path / "web_runs"))
    monkeypatch.setenv("CDR_PREVIEW_ROOT", str(tmp_path / "preview"))
    monkeypatch.setenv("CDR_MAX_UPLOAD_BYTES", "1048576")

    import crash_data_refiner.webapp as webapp_module

    reloaded = importlib.reload(webapp_module)
    try:
        assert reloaded.OUTPUT_ROOT == tmp_path / "web_runs"
        assert reloaded.PREVIEW_ROOT == tmp_path / "preview"
        assert reloaded.app.config["MAX_CONTENT_LENGTH"] == 1048576
    finally:
        monkeypatch.delenv("CDR_OUTPUT_ROOT")
        monkeypatch.delenv("CDR_PREVIEW_ROOT")
        monkeypatch.delenv("CDR_MAX_UPLOAD_BYTES")
        importlib.reload(reloaded)
