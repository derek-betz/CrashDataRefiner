# CrashDataRefiner

CrashDataRefiner is a lightweight toolkit for converting messy roadway crash
exports into consistent, analysis-ready CSV files. It provides a configurable
refinement pipeline and a convenient command line interface so analysts can
quickly normalize disparate data sources.

## Features

- **Header normalization** - converts source column names to `snake_case` so
  they can be consumed reliably by downstream tooling.
- **Flexible type coercion** - parse dates, convert numeric fields, and map
  boolean columns while gracefully handling blanks and malformed values.
- **Relevance boundary filtering** - keep only crash points within a KMZ
  polygon (single polygon required) and report excluded/invalid coordinates.
- **KMZ crash output** - generate a Google Earth-ready KMZ using the standard
  crash data template, including the click preview (the bubble shown when a
  crash is clicked).
- **Duplicate detection** - drop repeated records by specifying identifying
  columns.
- **Gap filling** - inject default values for missing columns before exporting.
- **Actionable reporting** - receive a summary of how many rows were kept,
  dropped, or coerced during the refinement process.

## Installation

The project is distributed as a standard Python package. You can install it in
a virtual environment directly from the repository:

```bash
pip install -e .
```

## Windows bootstrap

Install Python 3.12, development dependencies, and run tests:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1
```

## Usage

Refine a crash dataset using the CLI:

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

After processing, a JSON-formatted summary describing dropped or modified rows
is printed to the console.

## Desktop GUI

Launch the native desktop app:

```bash
crash-data-refiner-gui
```

Or double-click `launch_gui.pyw` on Windows. The GUI expects:

- One crash data file (CSV or Excel).
- One KMZ file containing **exactly one polygon** used as the relevance boundary.
- Latitude and longitude columns (auto-detected, but adjustable).

Outputs include:

- The refined crash data (inside the polygon) saved under `outputs/`.
- `Crashes Without Valid Lat-Long Data` saved next to the refined output.
- A KMZ crash file (`*_Crash Data.kmz`) formatted like the standard output with
  the crash narrative in the click preview bubble.
- A map report HTML file showing the polygon and included crashes, plus counts.

The GUI also shows a reference map preview automatically once the crash data
file and KMZ boundary are loaded.

## Web UI

Run the web application to share CrashDataRefiner over a network:

```bash
crash-data-refiner-web --host 0.0.0.0 --port 8081
```

Open `http://<server-host>:8081` in a browser. The web interface mirrors the GUI
workflow: upload crash data and a KMZ boundary, confirm latitude and longitude
columns, then run refinement. Outputs are stored under `outputs/web_runs/<run_id>/`.

## Python API

```python
from crash_data_refiner.refiner import CrashDataRefiner, RefinementConfig

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

## Development

Install development dependencies and run the test suite with:

```bash
pip install -e .[dev]
python scripts/run_tests.py
```

Feel free to adapt the pipeline to match the quirks of your crash dataset.
