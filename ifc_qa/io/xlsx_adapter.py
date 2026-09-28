from __future__ import annotations

from pathlib import Path
from typing import Any


def load_xlsx(path: Path) -> list[dict[str, Any]]:
    """Parsuje pierwszy arkusz XLSX do listy słowników. Logika sprawdzeń nie czyta pliku bezpośrednio."""
    from openpyxl import load_workbook

    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
    finally:
        workbook.close()

    if not rows:
        return []

    headers = [str(cell) if cell is not None else f"col_{index}" for index, cell in enumerate(rows[0])]
    records: list[dict[str, Any]] = []
    for row in rows[1:]:
        values = list(row) if row is not None else []
        if len(values) < len(headers):
            values.extend([None] * (len(headers) - len(values)))
        records.append(dict(zip(headers, values)))
    return records
