from __future__ import annotations

from pathlib import Path

from ifc_qa.checks.base import BaseCheck
from ifc_qa.core.models import CheckContext, CheckResult, CheckStatus, Finding
from ifc_qa.core.registry import register_check
from ifc_qa.io.ifc_loader import IfcLoadError, load_ifc, peek_text, read_header_section, schema_of

ISO_MARK = "ISO-10303-21"
SCHEMA_MARK = "FILE_SCHEMA"


@register_check
class IfcFileValidationCheck(BaseCheck):
    id = "F2"
    name = "Wczytanie i podstawowa walidacja modelu IFC"
    group = "wejście"
    required = True

    def run(self, ctx: CheckContext) -> CheckResult:
        findings: list[Finding] = []
        stats: dict = {}

        v21 = self._v21_file_selected(ctx)
        if v21:
            return self._failed(v21)

        assert ctx.file_path is not None
        path = ctx.file_path

        v22 = self._v22_extension(path)
        if v22:
            return self._failed(v22)

        v23 = self._v23_size(ctx)
        if v23:
            return self._failed(v23)
        stats["file_size_bytes"] = ctx.file_size

        v24 = self._v24_iso_header(path, ctx)
        if v24:
            return self._failed(v24)

        v25 = self._v25_file_schema(path, ctx)
        if v25:
            return self._failed(v25)

        v26 = self._v26_open(path, ctx)
        if v26:
            return self._failed(v26)

        stats["schema"] = ctx.schema_name
        findings.extend(self._schema_policy(ctx))

        if any(f.severity == CheckStatus.FAIL for f in findings):
            status = CheckStatus.FAIL
            summary = findings[-1].message
        elif any(f.severity == CheckStatus.WARN for f in findings):
            status = CheckStatus.WARN
            summary = "Plik wczytany; schemat różni się od wersji demonstracyjnej IFC2X3."
        else:
            status = CheckStatus.PASS
            summary = "Plik IFC wczytany poprawnie."
        return CheckResult(
            check_id=self.id,
            name=self.name,
            status=status,
            summary=summary,
            findings=findings,
            stats=stats,
        )

    def _failed(self, finding: Finding) -> CheckResult:
        return CheckResult(
            check_id=self.id,
            name=self.name,
            status=CheckStatus.FAIL,
            summary=finding.message,
            findings=[finding],
        )

    def _v21_file_selected(self, ctx: CheckContext) -> Finding | None:
        if ctx.file_path is None or not Path(ctx.file_path).is_file():
            return Finding(
                code="V2.1",
                severity=CheckStatus.FAIL,
                message="Nie wybrano pliku IFC. Wgraj plik zawierający model do weryfikacji.",
            )
        return None

    def _v22_extension(self, path: Path) -> Finding | None:
        if path.suffix.lower() != ".ifc":
            return Finding(
                code="V2.2",
                severity=CheckStatus.FAIL,
                message=f"Nieprawidłowe rozszerzenie pliku: '{path.suffix or '(brak)'}'. Wymagane jest *.ifc.",
                details=str(path.name),
            )
        return None

    def _v23_size(self, ctx: CheckContext) -> Finding | None:
        settings = ctx.settings
        size = ctx.file_size
        if size < settings.min_file_size_bytes or size > settings.max_file_size_bytes:
            return Finding(
                code="V2.3",
                severity=CheckStatus.FAIL,
                message=(
                    f"Rozmiar pliku {size} B jest poza zakresem "
                    f"{settings.min_file_size_bytes} B – {settings.max_file_size_bytes} B (50 MiB)."
                ),
            )
        return None

    def _v24_iso_header(self, path: Path, ctx: CheckContext) -> Finding | None:
        text = peek_text(path, ctx.settings.header_peek_bytes)
        if ISO_MARK not in text:
            return Finding(
                code="V2.4",
                severity=CheckStatus.FAIL,
                message="Nagłówek pliku nie zawiera ISO-10303-21. To nie jest poprawny plik STEP/IFC.",
            )
        return None

    def _v25_file_schema(self, path: Path, ctx: CheckContext) -> Finding | None:
        header = read_header_section(path, ctx.settings.header_scan_bytes)
        if SCHEMA_MARK not in header:
            return Finding(
                code="V2.5",
                severity=CheckStatus.FAIL,
                message="W nagłówku pliku brakuje deklaracji FILE_SCHEMA.",
            )
        return None

    def _v26_open(self, path: Path, ctx: CheckContext) -> Finding | None:
        try:
            model = load_ifc(path)
        except IfcLoadError as exc:
            return Finding(
                code="V2.6",
                severity=CheckStatus.FAIL,
                message=f"IfcOpenShell nie otworzył pliku: {exc}",
            )
        ctx.model = model
        ctx.schema_name = schema_of(model)
        return None

    def _schema_policy(self, ctx: CheckContext) -> list[Finding]:
        expected = ctx.settings.expected_schema.upper()
        actual = (ctx.schema_name or "").upper()
        if actual == expected:
            return []
        message = (
            f"Wersja demonstracyjna obsługuje {expected}, wykryto '{ctx.schema_name or 'nieznany'}'."
        )
        if ctx.settings.unknown_schema_policy == "fail":
            return [Finding(code="SCHEMA", severity=CheckStatus.FAIL, message=message)]
        return [Finding(code="SCHEMA", severity=CheckStatus.WARN, message=message)]
