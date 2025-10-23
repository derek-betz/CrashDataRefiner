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
pip install -e .
pip install pytest
pytest
```

Feel free to adapt the pipeline to match the quirks of your crash dataset.
