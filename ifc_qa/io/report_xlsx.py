from __future__ import annotations

import re
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from ifc_qa.core.models import CheckContext, CheckResult
from ifc_qa.core.result_store import ResultStore


def _sheet_name(check_id: str) -> str:
    cleaned = re.sub(r"[\[\]\*\/\\?:]", "_", check_id)[:31]
    return cleaned or "check"


def build_report_bytes(store: ResultStore, ctx: CheckContext) -> bytes:
    workbook = Workbook()
    summary = workbook.active
    summary.title = "Podsumowanie"

    header_font = Font(bold=True)
    meta_rows = [
        ("Plik IFC", ctx.file_name),
        ("Rozmiar (B)", ctx.file_size),
        ("Schema", ctx.schema_name or "—"),
        ("Czas raportu (UTC)", datetime.now(timezone.utc).isoformat(timespec="seconds")),
        ("Start kontroli (UTC)", store.started_at.isoformat(timespec="seconds")),
        ("Status zbiorczy", store.overall_status().value),
    ]
    summary["A1"] = "Metadane uruchomienia"
    summary["A1"].font = header_font
    for index, (key, value) in enumerate(meta_rows, start=2):
        summary[f"A{index}"] = key
        summary[f"B{index}"] = value

    start = 10
    headers = ["check_id", "nazwa", "status", "liczba_findings", "czas_ms", "podsumowanie"]
    for col, title in enumerate(headers, start=1):
        cell = summary.cell(row=start, column=col, value=title)
        cell.font = header_font

    for row_offset, result in enumerate(store.results, start=1):
        row = start + row_offset
        summary.cell(row=row, column=1, value=result.check_id)
        summary.cell(row=row, column=2, value=result.name)
        summary.cell(row=row, column=3, value=result.status.value)
        summary.cell(row=row, column=4, value=len(result.findings))
        summary.cell(row=row, column=5, value=result.duration_ms)
        summary.cell(row=row, column=6, value=result.summary)

    _autosize(summary)

    used_names: set[str] = {"Podsumowanie"}
    for result in store.results:
        sheet_title = _unique_name(_sheet_name(result.check_id), used_names)
        used_names.add(sheet_title)
        sheet = workbook.create_sheet(sheet_title)
        _write_findings_sheet(sheet, result, header_font)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def write_report(path: Path, store: ResultStore, ctx: CheckContext) -> None:
    path.write_bytes(build_report_bytes(store, ctx))


def _write_findings_sheet(sheet, result: CheckResult, header_font: Font) -> None:
    sheet["A1"] = result.check_id
    sheet["A1"].font = header_font
    sheet["B1"] = result.name
    sheet["A2"] = "Status"
    sheet["B2"] = result.status.value
    sheet["A3"] = "Podsumowanie"
    sheet["B3"] = result.summary

    headers = ["code", "severity", "message", "ifc_guid", "ifc_class", "details"]
    for col, title in enumerate(headers, start=1):
        cell = sheet.cell(row=5, column=col, value=title)
        cell.font = header_font

    if not result.findings:
        sheet.cell(row=6, column=1, value="—")
        sheet.cell(row=6, column=3, value="Brak findings")
    else:
        for index, finding in enumerate(result.findings, start=6):
            sheet.cell(row=index, column=1, value=finding.code)
            sheet.cell(row=index, column=2, value=finding.severity.value)
            sheet.cell(row=index, column=3, value=finding.message)
            sheet.cell(row=index, column=4, value=finding.ifc_guid)
            sheet.cell(row=index, column=5, value=finding.ifc_class)
            sheet.cell(row=index, column=6, value=finding.details)
    _autosize(sheet)


def _unique_name(name: str, used: set[str]) -> str:
    if name not in used:
        return name
    suffix = 2
    while True:
        candidate = f"{name[:28]}_{suffix}"
        if candidate not in used:
            return candidate
        suffix += 1


def _autosize(sheet) -> None:
    for column_cells in sheet.columns:
        letter = get_column_letter(column_cells[0].column)
        length = max((len(str(cell.value)) if cell.value is not None else 0) for cell in column_cells)
        sheet.column_dimensions[letter].width = min(max(length + 2, 12), 60)
