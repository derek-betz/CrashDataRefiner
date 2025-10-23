"""Command line interface for CrashDataRefiner."""
from __future__ import annotations

import argparse
import json
from typing import Any, Dict, Sequence

from .refiner import CrashDataRefiner, RefinementConfig


def _parse_mapping(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(
            "Expected a JSON object for --fill-defaults"
        ) from exc


def _parse_list(text: str) -> Sequence[str]:
    if not text:
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize crash data exports")
    parser.add_argument("input", help="Path to the raw crash data CSV file")
    parser.add_argument("output", help="Where the refined CSV should be written")

    parser.add_argument(
        "--required-columns",
        type=_parse_list,
        default=[],
        help="Comma separated list of columns that must be present for a row to be kept",
    )
    parser.add_argument(
        "--date-columns",
        type=_parse_list,
        default=[],
        help="Comma separated list of columns that should be parsed as dates",
    )
    parser.add_argument(
        "--integer-columns",
        type=_parse_list,
        default=[],
        help="Comma separated list of columns that should be converted to integers",
    )
    parser.add_argument(
        "--float-columns",
        type=_parse_list,
        default=[],
        help="Comma separated list of columns that should be converted to floats",
    )
    parser.add_argument(
        "--boolean-columns",
        type=_parse_list,
        default=[],
        help="Comma separated list of columns that should be converted to booleans",
    )
    parser.add_argument(
        "--dedupe-on",
        type=_parse_list,
        default=[],
        help="Columns used to identify duplicate rows",
    )
    parser.add_argument(
        "--fill-defaults",
        type=_parse_mapping,
        default={},
        help="JSON object describing default values to inject into missing columns",
    )

    return parser


def main(args: Sequence[str] | None = None) -> int:
    parser = build_parser()
    parsed = parser.parse_args(args=args)

    config = RefinementConfig(
        required_columns=parsed.required_columns,
        date_columns=parsed.date_columns,
        integer_columns=parsed.integer_columns,
        float_columns=parsed.float_columns,
        boolean_columns=parsed.boolean_columns,
        dedupe_on=parsed.dedupe_on,
        fill_defaults=parsed.fill_defaults,
    )

    refiner = CrashDataRefiner(config)
    report = refiner.refine_file(parsed.input, parsed.output)

    print(json.dumps(report.__dict__, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
