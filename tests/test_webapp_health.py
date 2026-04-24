from __future__ import annotations

from crash_data_refiner.webapp import app


def test_health_reports_hosted_roots() -> None:
    client = app.test_client()

    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert "outputRoot" in payload
    assert "previewRoot" in payload
