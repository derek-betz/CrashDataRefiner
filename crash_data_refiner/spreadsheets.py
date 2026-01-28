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
        rows = [dict(row) for row in reader if not _is_blank_row(row)]
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
        if row_dict and not _is_blank_row(row_dict):
            rows.append(row_dict)
    return SpreadsheetData(headers=headers, rows=rows)


def _write_xlsx(path: str, rows: Sequence[Mapping[str, Any]], headers: Sequence[str] | None = None) -> None:
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.table import Table, TableStyleInfo
    from openpyxl import Workbook

    header_list = _resolve_headers(rows, headers)
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(list(header_list))
    for row in rows:
        sheet.append([row.get(header) for header in header_list])

    if header_list:
        max_row = sheet.max_row
        max_col = len(header_list)
        end_cell = f"{get_column_letter(max_col)}{max_row}"
        table = Table(displayName="Table1", ref=f"A1:{end_cell}")
        table_style = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        table.tableStyleInfo = table_style
        sheet.add_table(table)
        _autosize_columns(sheet, max_col)

    workbook.save(path)


def _autosize_columns(sheet: Any, max_col: int) -> None:
    from openpyxl.utils import get_column_letter

    for col_idx in range(1, max_col + 1):
        max_length = 0
        for cell in sheet.iter_rows(min_row=1, max_row=sheet.max_row, min_col=col_idx, max_col=col_idx):
            value = cell[0].value
            if value is None:
                continue
            text = str(value)
            if len(text) > max_length:
                max_length = len(text)
        width = min(max(max_length + 2, 10), 60)
        sheet.column_dimensions[get_column_letter(col_idx)].width = width


def _resolve_headers(rows: Sequence[Mapping[str, Any]], headers: Sequence[str] | None) -> List[str]:
    if headers:
        return list(headers)
    header_set = set()
    for row in rows:
        header_set.update(row.keys())
    header_list = sorted(header_set)
    if "kmz_label" in header_list:
        header_list.remove("kmz_label")
        header_list.insert(0, "kmz_label")
    return header_list


def _is_blank_row(row: Mapping[str, Any]) -> bool:
    if not row:
        return True
    return all(_is_blank_value(value) for value in row.values())


def _is_blank_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple)):
        return all(_is_blank_value(item) for item in value)
    return False
