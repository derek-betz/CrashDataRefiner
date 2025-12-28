"""Generate a lightweight HTML map report for refined crash data."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Sequence, Tuple

from .geo import PolygonBoundary


def write_map_report(
    path: str,
    *,
    polygon: PolygonBoundary,
    points: Iterable[Tuple[float, float]],
    included_count: int,
    excluded_count: int,
    invalid_count: int,
) -> None:
    polygon_coords = _polygon_to_leaflet(polygon)
    point_list = [[lat, lon] for lat, lon in points]

    payload = {
        "polygon": polygon_coords,
        "points": point_list,
        "counts": {
            "included": included_count,
            "excluded": excluded_count,
            "invalid": invalid_count,
        },
    }

    html = _render_html(payload)
    Path(path).write_text(html, encoding="utf-8")


def _polygon_to_leaflet(polygon: PolygonBoundary) -> Sequence[Sequence[Sequence[float]]]:
    outer = [[lat, lon] for lon, lat in polygon.outer]
    holes = [[[lat, lon] for lon, lat in ring] for ring in polygon.holes]
    if holes:
        return [outer, *holes]
    return [outer]


def _render_html(payload: dict) -> str:
    data = json.dumps(payload)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Crash Data Refiner Map Report</title>
  <link
    rel="stylesheet"
    href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
    integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
    crossorigin=""
  >
  <style>
    :root {{
      --bg: #0d1117;
      --panel: #111827;
      --text: #e6edf3;
      --muted: #9aa7b2;
      --accent: #58a6ff;
      --accent-soft: #0c2d50;
      --success: #2ea043;
    }}
    html, body {{
      margin: 0;
      height: 100%;
      background: var(--bg);
      font-family: "Segoe UI", sans-serif;
      color: var(--text);
    }}
    .header {{
      padding: 18px 24px;
      background: var(--panel);
      border-bottom: 1px solid #24384b;
    }}
    .title {{
      font-size: 20px;
      font-weight: 600;
      margin: 0 0 8px;
    }}
    .summary {{
      display: flex;
      gap: 18px;
      font-size: 14px;
      color: var(--muted);
      flex-wrap: wrap;
    }}
    .summary span {{
      background: var(--accent-soft);
      color: var(--accent);
      padding: 4px 10px;
      border-radius: 999px;
    }}
    #map {{
      height: calc(100% - 82px);
    }}
  </style>
</head>
<body>
  <div class="header">
    <div class="title">Crash Data Refiner - Map Report</div>
    <div class="summary">
      <span>Included: <strong id="included-count"></strong></span>
      <span>Excluded: <strong id="excluded-count"></strong></span>
      <span>Invalid Lat/Long: <strong id="invalid-count"></strong></span>
    </div>
  </div>
  <div id="map"></div>
  <script
    src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
    integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
    crossorigin=""
  ></script>
  <script>
    const payload = {data};
    document.getElementById("included-count").textContent = payload.counts.included;
    document.getElementById("excluded-count").textContent = payload.counts.excluded;
    document.getElementById("invalid-count").textContent = payload.counts.invalid;

    const map = L.map("map", {{
      zoomControl: true,
      attributionControl: true,
    }});

    const streets = L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors",
    }});

    const imagery = L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}",
      {{
        maxZoom: 19,
        attribution: "Tiles &copy; Esri",
      }}
    );

    streets.addTo(map);

    const boundary = L.polygon(payload.polygon, {{
      color: "#58a6ff",
      weight: 3,
      fillColor: "#0c2d50",
      fillOpacity: 0.2,
    }}).addTo(map);

    const markers = L.layerGroup();
    payload.points.forEach((point) => {{
      L.circleMarker(point, {{
        radius: 3,
        color: "#2ea043",
        fillColor: "#2ea043",
        fillOpacity: 0.8,
        weight: 1,
      }}).addTo(markers);
    }});
    markers.addTo(map);

    L.control.layers({{"Streets": streets, "Imagery": imagery}}, {{"Included Crashes": markers}}).addTo(map);
    map.fitBounds(boundary.getBounds(), {{ padding: [20, 20] }});
  </script>
</body>
</html>
"""
