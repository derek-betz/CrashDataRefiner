# CrashDataRefiner

CrashDataRefiner converts messy crash exports into consistent, analysis-ready
outputs. It is designed as a **web-first internal application** for engineering
teams, with a hosted web interface, a REST API, and a CLI for scripted use.

## Architecture

```
crash_data_refiner/
├── normalize.py      # Public header-normalization & column-inference helpers
├── refiner.py        # Core CrashDataRefiner pipeline
├── services.py       # Shared orchestration layer (pipeline, path helpers, PDF)
├── webapp.py         # Flask web application (primary interface)
├── api.py            # FastAPI REST API
├── cli.py            # Command-line interface
├── geo.py            # KMZ/polygon geospatial utilities
├── kmz_report.py     # KMZ crash output generation
├── map_report.py     # HTML map report generation
├── pdf_report.py     # PDF full-report generation
└── spreadsheets.py   # CSV/Excel read-write helpers
```

## Features

- **Header normalization** – converts source column names to `snake_case` so
  they can be consumed reliably by downstream tooling.
- **Flexible type coercion** – parse dates, convert numeric fields, and map
  boolean columns while gracefully handling blanks and malformed values.
- **Relevance boundary filtering** – keep only crash points within a KMZ
  polygon (single polygon required) and report excluded/invalid coordinates.
- **Same-project coordinate recovery** – auto-fill high-confidence missing
  coordinates from repeated roadway/intersection/mile-marker patterns in the
  same dataset, then write a coordinate-review workbook for unresolved rows.
- **Coordinate review roundtrip** – upload an edited coordinate-review workbook
  with approved grouped locations and rerun refinement on the original crash
  data/KMZ inputs.
- **Browser review queue** – review unresolved coordinate groups directly in the
  web app, approve suggested points or enter custom coordinates, and rerun the
  pipeline without leaving the browser.
- **KMZ crash output** – generate a Google Earth-ready KMZ using the standard
  crash data template, including the click preview narrative.
- **HTML map report** – interactive map showing the boundary polygon and
  included crash points with counts.
- **PDF full report** – tabular PDF report of refined crash rows.
- **Duplicate detection** – drop repeated records by specifying identifying
  columns.
- **Gap filling** – inject default values for missing columns before exporting.

## Installation

```bash
pip install -e .
```

## Web Application (primary interface)

Start the web server:

```bash
crash-data-refiner-web --host 0.0.0.0 --port 8081
```

Open `http://<server-host>:8081` in a browser. Upload crash data (CSV or Excel)
and a KMZ boundary file, confirm latitude and longitude columns, then run
refinement. Outputs are stored under `outputs/web_runs/<run_id>/`, including a
coordinate review workbook when missing lat/long rows need manual follow-up.
You can either resolve those groups in the browser-native review queue or edit
the workbook and upload it back through the web UI to apply approved
coordinates and generate a fresh refined run.

## Local Test Checklist

For a quick local test on Windows, start the app with the bundled launcher:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_web.ps1 -OpenBrowser
```

Use these sample files for the first pass:

- `tests/refiner_inputs/2101166_Crash-Data.xlsx`
- `tests/refiner_inputs/2101166_Relevance Boundary.kmz`

Recommended happy-path test:

1. Run refinement and confirm the refined workbook, invalid-coordinate workbook,
   review workbook, and KMZ output all appear.
2. Approve one grouped item in the browser review queue and apply it.
3. Generate the PDF full report and confirm the progress log advances while the
   report is rendering.

Notes:

- Outputs are written to `outputs/web_runs/<run_id>/`.
- The map preview and PDF aerial tiles need network access.
- Use `python -m pytest tests/ -W error::DeprecationWarning` before shipping
  changes so package deprecations fail fast.

## REST API

Start the FastAPI server:

```bash
crash-data-refiner-api
```

By default the API listens on port 9005.  Set `HOST` and `PORT` environment
variables to override. The `POST /refine` endpoint accepts a crash data file
and an optional KMZ boundary file and returns a JSON summary. Supply
`coordinate_review_file` along with `lat_column` and `lon_column` to apply an
edited coordinate review workbook during the refinement call.

## CLI

Refine a crash dataset from the command line:

```bash
crash-data-refiner raw_crashes.csv refined_crashes.csv \
  --required-columns "Crash ID,Crash Date" \
  --date-columns "Crash Date" \
  --integer-columns "Fatalities" \
  --float-columns "Serious Injuries" \
  --boolean-columns "Hit and Run" \
  --dedupe-on "Crash ID" \
  --fill-defaults '{"City": "Unknown"}'
```

A JSON summary describing dropped or modified rows is printed to the console.

## Python API

```python
from crash_data_refiner import CrashDataRefiner, RefinementConfig

config = RefinementConfig(
    required_columns=["Crash ID", "Crash Date"],
    date_columns=["Crash Date"],
    integer_columns=["Fatalities"],
    float_columns=["Serious Injuries"],
    boolean_columns=["Hit and Run"],
    dedupe_on=["Crash ID"],
    fill_defaults={"City": "Unknown"},
)

refiner = CrashDataRefiner(config)
rows, report = refiner.refine_rows(csv_rows)
```

The returned `rows` list contains normalized dictionaries ready for loading
into analytics platforms, and `report` captures overall data hygiene metrics.

Use the shared services layer for the full pipeline:

```python
from pathlib import Path
from crash_data_refiner.services import run_refinement_pipeline

result = run_refinement_pipeline(
    data_path=Path("crashes.csv"),
    kmz_path=Path("boundary.kmz"),
    run_dir=Path("outputs/run_001"),
    lat_column="Latitude",
    lon_column="Longitude",
)
print(result.log)
```

## Development

Install development dependencies and run the test suite:

```bash
pip install -e .[dev]
python -m pytest tests/
```

## Secrets

The `API_KEY/` directory is intentionally excluded from version control.
Create it locally on each machine to store secrets.

