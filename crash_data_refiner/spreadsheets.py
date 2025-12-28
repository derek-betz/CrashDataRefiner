"""Spreadsheet IO helpers for CSV and Excel files."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import csv


@dataclass
class SpreadsheetData:
    headers: List[str]
    rows: List[Dict[str, Any]]


def read_spreadsheet(path: str) -> SpreadsheetData:
    ext = Path(path).suffix.lower()
    if ext in {".csv"}:
        return _read_csv(path)
    if ext in {".xlsx", ".xlsm"}:
        return _read_xlsx(path)
    raise ValueError(f"Unsupported file type: {ext}")


def read_spreadsheet_headers(path: str) -> List[str]:
    ext = Path(path).suffix.lower()
    if ext in {".csv"}:
        with open(path, "r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            return [str(item).strip() if item is not None else "" for item in next(reader, [])]
    if ext in {".xlsx", ".xlsm"}:
        from openpyxl import load_workbook

        workbook = load_workbook(path, read_only=True, data_only=True)
        sheet = workbook.active
        row = next(sheet.iter_rows(values_only=True), None)
        if not row:
            return []
        return [str(item).strip() if item is not None else "" for item in row]
    raise ValueError(f"Unsupported file type: {ext}")


def write_spreadsheet(path: str, rows: Sequence[Mapping[str, Any]], headers: Sequence[str] | None = None) -> None:
    ext = Path(path).suffix.lower()
    if ext in {".csv"}:
        _write_csv(path, rows, headers=headers)
        return
    if ext in {".xlsx", ".xlsm"}:
        _write_xlsx(path, rows, headers=headers)
        return
    raise ValueError(f"Unsupported file type: {ext}")


def _read_csv(path: str) -> SpreadsheetData:
    with open(path, "r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    return SpreadsheetData(headers=headers, rows=rows)


def _write_csv(path: str, rows: Sequence[Mapping[str, Any]], headers: Sequence[str] | None = None) -> None:
    header_list = _resolve_headers(rows, headers)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header_list)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header) for header in header_list})


def _read_xlsx(path: str) -> SpreadsheetData:
    from openpyxl import load_workbook

    workbook = load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.active
    rows_iter = sheet.iter_rows(values_only=True)
    header_row = next(rows_iter, None)
    headers = [str(item).strip() if item is not None else "" for item in (header_row or [])]
    rows: List[Dict[str, Any]] = []
    for row in rows_iter:
        if row is None:
            continue
        row_dict: Dict[str, Any] = {}
        for idx, header in enumerate(headers):
            if not header:
                continue
            if idx < len(row):
                row_dict[header] = row[idx]
        if row_dict:
            rows.append(row_dict)
    return SpreadsheetData(headers=headers, rows=rows)


def _write_xlsx(path: str, rows: Sequence[Mapping[str, Any]], headers: Sequence[str] | None = None) -> None:
    from openpyxl import Workbook

    header_list = _resolve_headers(rows, headers)
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(list(header_list))
    for row in rows:
        sheet.append([row.get(header) for header in header_list])
    workbook.save(path)


def _resolve_headers(rows: Sequence[Mapping[str, Any]], headers: Sequence[str] | None) -> List[str]:
    if headers:
        return list(headers)
    header_set = set()
    for row in rows:
        header_set.update(row.keys())
    return sorted(header_set)
