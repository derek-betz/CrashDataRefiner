# CrashDataRefiner

CrashDataRefiner converts messy crash exports into consistent, analysis-ready
outputs. It is designed as a web-first internal application for engineering
teams, with a hosted web interface, a REST API, and a CLI for scripted use.

## Architecture

```text
crash_data_refiner/
|-- normalize.py      # Public header-normalization and column-inference helpers
|-- refiner.py        # Core CrashDataRefiner pipeline
|-- services.py       # Stable facade over shared orchestration helpers
|-- pipeline.py       # Refinement / relabel / PDF orchestration
|-- labeling.py       # KMZ label-direction detection and row ordering
|-- output_paths.py   # Canonical output-path helpers
|-- run_contract.py   # Shared run-summary contract for web and API consumers
|-- web_state.py      # Flask run-state registry and snapshot model
|-- web_summary.py    # Flask summary adapters
|-- web_review.py     # Flask coordinate-review parsing and queue helpers
|-- webapp.py         # Flask web application (primary interface)
|-- api.py            # Compatibility FastAPI surface
|-- cli.py            # Command-line interface
|-- geo.py            # KMZ/polygon geospatial utilities
|-- kmz_report.py     # KMZ crash output generation
|-- map_report.py     # HTML map report generation
|-- pdf_report.py     # PDF full-report generation
`-- spreadsheets.py   # CSV/Excel read-write helpers
```

## Features

- Header normalization converts source column names to `snake_case` so they can
  be consumed reliably by downstream tooling.
- Flexible type coercion parses dates, converts numeric fields, and maps
  boolean columns while gracefully handling blanks and malformed values.
- Relevance boundary filtering keeps only crash points within a KMZ polygon
  (single polygon required) and reports excluded and invalid coordinates.
- Same-project coordinate recovery auto-fills high-confidence missing
  coordinates from repeated roadway, intersection, and mile-marker patterns in
  the same dataset, then writes a coordinate-review workbook for unresolved
  rows.
- Coordinate review roundtrip uploads an edited coordinate-review workbook with
  approved locations and reruns refinement on the original crash data and KMZ.
- Browser review wizard lets the user review unresolved crashes directly in the
  web app, confirm a suggested point, place the crash on the map, or exclude
  it from the project.
- KMZ crash output generates a Google Earth-ready KMZ using the standard crash
  data template, including the click-preview narrative.
- HTML map report generates an interactive map showing the boundary polygon and
  included crash points with counts.
- PDF full report generates a tabular PDF report of refined crash rows.
- Duplicate detection drops repeated records by specified identifying columns.
- Gap filling injects default values for missing columns before export.

## Installation

```bash
pip install -e .
```

## Web Application

Start the web server:

```bash
crash-data-refiner-web --host 0.0.0.0 --port 8081
```

Open `http://<server-host>:8081` in a browser. Upload crash data (CSV or Excel)
and a KMZ boundary file, confirm latitude and longitude columns, then run
refinement. Outputs are stored under `outputs/web_runs/<run_id>/`, including a
coordinate review workbook when missing lat/long rows need manual follow-up.
You can either resolve those crashes in the browser review wizard or edit the
workbook and upload it back through the web UI to apply approved coordinates
and generate a fresh refined run.

## Local Test Checklist

For a quick local test on Windows, start the app with the bundled launcher:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_web.ps1 -OpenBrowser
```

Use these sample files for the first pass:

- `tests/refiner_inputs/2101166_Crash-Data.xlsx`
- `tests/refiner_inputs/2101166_Relevance Boundary.kmz`

Recommended happy-path test:

1. Run refinement and confirm the refined workbook, invalid-coordinate
   workbook, coordinate-review workbook, and KMZ output all appear.
2. Exclude one likely crash in the browser review wizard and apply the reviewed
   decisions.
3. Generate the PDF full report and confirm the progress log advances while the
   report is rendering.
4. Regenerate KMZ labels from the Results stage and confirm the numbering
   direction updates without rerunning manual review.

Repeatable browser smoke test:

1. Start the web app on `http://127.0.0.1:8090`
2. Install the optional browser QC dependency once:

```bash
npm install
npx playwright install chromium
```

3. Run the browser smoke test:

```bash
npm run qc:web
```

The smoke script exercises the representative `2101166` workflow end to end:

- refine
- hard refresh restore into `Review`
- exclude one crash
- apply browser review
- hard refresh restore into `Results`
- relabel from automatic south-to-north to west-to-east

Screenshots are written to `outputs/qc_browser_smoke/`.

## CLI-First Playwright UI Audit

For interactive browser QA, prefer the Playwright skill wrapper over checked-in
Playwright specs. This keeps UI debugging fast while still saving artifacts in
the repo.

Start the Flask app locally:

```bash
.venv/bin/python -m crash_data_refiner.webapp --host 127.0.0.1 --port 8081
```

Use the bundled Playwright helper script from a second terminal:

```bash
scripts/playwright_skill_audit.sh open
scripts/playwright_skill_audit.sh desktop
scripts/playwright_skill_audit.sh capture initial-load
```

Recommended fixture set:

- `tests/refiner_inputs/2101166_Crash-Data.xlsx`
- `tests/refiner_inputs/2101166_Relevance Boundary.kmz`

Representative manual flow:

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export PWCLI="$CODEX_HOME/skills/playwright/scripts/playwright_cli.sh"

scripts/playwright_skill_audit.sh open
"$PWCLI" --session default snapshot
"$PWCLI" --session default click eX
"$PWCLI" --session default upload "/absolute/path/to/tests/refiner_inputs/2101166_Crash-Data.xlsx"
"$PWCLI" --session default snapshot
"$PWCLI" --session default click eY
"$PWCLI" --session default upload "/absolute/path/to/tests/refiner_inputs/2101166_Relevance Boundary.kmz"
"$PWCLI" --session default snapshot
"$PWCLI" --session default click eZ
scripts/playwright_skill_audit.sh capture review-stage
scripts/playwright_skill_audit.sh mobile
scripts/playwright_skill_audit.sh capture mobile-review
```

Replace `eX`, `eY`, and `eZ` with the current snapshot refs for the crash-data
picker, the KMZ picker, and the action you want to exercise next. Re-snapshot
after each major UI transition so refs stay current.

Artifacts are written under `output/playwright/`:

- `snapshot.md`
- `screenshot.png`
- `console-error.txt`
- `network.txt`
- copied `.playwright-cli/` session artifacts for traces and command history

Suggested audit checkpoints:

1. Initial load and favicon/static asset requests are clean.
2. Column inference, preview map, and refine are available once inputs load.
3. Review-stage decisions, map placement, and apply-review flows stay in sync.
4. Results-stage relabel, open-map, report generation, and session restore work
   on both desktop and mobile widths.

Reference-dataset QC:

```bash
npm run qc:datasets
```

This runs the shared service pipeline against the four committed reference
projects under `raw-crash-data-for-reference/`:

- `20H00010H`
- `2100235`
- `2100238`
- `2101166`

For each dataset it runs:

- refinement with automatic label ordering
- one row-level exclusion rerun when review items exist
- relabeling to the opposite direction
- PDF generation

The `2101166` reference boundary is the official source of truth, and the test
fixture in `tests/refiner_inputs/` is kept aligned to that file.

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

By default the API listens on port 9005. Set `HOST` and `PORT` environment
variables to override. The `POST /refine` endpoint accepts a crash data file
and an optional KMZ boundary file and returns a JSON summary. Supply
`coordinate_review_file` along with `lat_column` and `lon_column` to apply an
edited coordinate review workbook during the refinement call.

Treat this API surface as a compatibility layer. The Flask web app remains the
primary product interface and receives the most complete workflow coverage.

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
from pathlib import Path

from crash_data_refiner import CrashDataRefiner, RefinementConfig
from crash_data_refiner.services import run_refinement_pipeline

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

result = run_refinement_pipeline(
    data_path=Path("crashes.csv"),
    kmz_path=Path("boundary.kmz"),
    run_dir=Path("outputs/run_001"),
    lat_column="Latitude",
    lon_column="Longitude",
)
print(report)
print(result.log)
```

## Development

Install development dependencies and run the test suite:

```bash
pip install -e .[dev]
python -m pytest tests/
```

Run the browser smoke gate against a running local web server:

```bash
npm run qc:web
```

## Secrets

The `API_KEY/` directory is intentionally excluded from version control.
Create it locally on each machine to store secrets.
