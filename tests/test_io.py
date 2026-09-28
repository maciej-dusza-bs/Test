from io import BytesIO
from pathlib import Path

from openpyxl import Workbook, load_workbook

from ifc_qa.core.models import CheckContext, CheckResult, CheckStatus, Finding
from ifc_qa.core.result_store import ResultStore
from ifc_qa.io.docx_adapter import load_docx
from ifc_qa.io.report_xlsx import build_report_bytes
from ifc_qa.io.xlsx_adapter import load_xlsx


def test_xlsx_adapter(tmp_path: Path) -> None:
    path = tmp_path / "rules.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["IfcClass", "Allowed"])
    ws.append(["IfcWall", "yes"])
    wb.save(path)
    rows = load_xlsx(path)
    assert rows == [{"IfcClass": "IfcWall", "Allowed": "yes"}]


def test_docx_adapter(tmp_path: Path) -> None:
    from docx import Document

    path = tmp_path / "notes.docx"
    doc = Document()
    doc.add_paragraph("Reguła testowa")
    doc.save(path)
    parsed = load_docx(path)
    assert "Reguła testowa" in parsed["text"]


def test_report_has_summary_and_per_check_sheets() -> None:
    store = ResultStore()
    store.add(
        CheckResult(
            check_id="F2",
            name="Walidacja",
            status=CheckStatus.PASS,
            summary="ok",
            findings=[Finding(code="V2.6", severity=CheckStatus.PASS, message="otwarto")],
        )
    )
    store.add(
        CheckResult(
            check_id="F3",
            name="Metadane",
            status=CheckStatus.STUB,
            summary="Niezaimplementowane — iteracja 2",
        )
    )
    ctx = CheckContext(file_name="demo.ifc", file_size=123, schema_name="IFC2X3")
    data = build_report_bytes(store, ctx)
    wb = load_workbook(BytesIO(data))
    assert "Podsumowanie" in wb.sheetnames
    assert "F2" in wb.sheetnames
    assert "F3" in wb.sheetnames
    assert wb["Podsumowanie"]["B4"].value == "IFC2X3"
