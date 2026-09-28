from pathlib import Path

import pytest

from ifc_qa.checks.f2_ifc_validation import IfcFileValidationCheck
from ifc_qa.config import AppSettings
from ifc_qa.core.models import CheckContext, CheckStatus

MINIMAL_IFC = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('minimal.ifc','2020-01-01T00:00:00',('Author'),('Org'),'Python','IfcQA','');
FILE_SCHEMA(('IFC2X3'));
ENDSEC;
DATA;
ENDSEC;
END-ISO-10303-21;
"""

IFC4_HEADER = MINIMAL_IFC.replace("IFC2X3", "IFC4")

NO_SCHEMA = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('minimal.ifc','2020-01-01T00:00:00',('Author'),('Org'),'Python','IfcQA','');
ENDSEC;
DATA;
ENDSEC;
END-ISO-10303-21;
"""

NO_ISO = """HEADER;
FILE_SCHEMA(('IFC2X3'));
ENDSEC;
DATA;
ENDSEC;
"""


def _write(tmp_path: Path, content: str, name: str = "model.ifc") -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def _ctx(path: Path | None, **kwargs) -> CheckContext:
    settings = kwargs.pop("settings", AppSettings())
    size = kwargs.pop("file_size", path.stat().st_size if path and path.exists() else 0)
    return CheckContext(
        file_name=path.name if path else "",
        file_path=path,
        file_size=size,
        selected_check_ids=["F2"],
        settings=settings,
        **kwargs,
    )


@pytest.fixture
def check() -> IfcFileValidationCheck:
    return IfcFileValidationCheck()


def test_v21_missing_file(check: IfcFileValidationCheck) -> None:
    result = check.run(_ctx(None))
    assert result.status == CheckStatus.FAIL
    assert result.findings[0].code == "V2.1"


def test_v22_wrong_extension(tmp_path: Path, check: IfcFileValidationCheck) -> None:
    path = _write(tmp_path, MINIMAL_IFC, "model.txt")
    result = check.run(_ctx(path))
    assert result.status == CheckStatus.FAIL
    assert result.findings[0].code == "V2.2"


def test_v23_too_small(tmp_path: Path, check: IfcFileValidationCheck) -> None:
    path = _write(tmp_path, "tiny", "tiny.ifc")
    result = check.run(_ctx(path))
    assert result.status == CheckStatus.FAIL
    assert result.findings[0].code == "V2.3"


def test_v23_too_large(tmp_path: Path, check: IfcFileValidationCheck) -> None:
    path = _write(tmp_path, MINIMAL_IFC)
    result = check.run(_ctx(path, file_size=51 * 1024 * 1024))
    assert result.status == CheckStatus.FAIL
    assert result.findings[0].code == "V2.3"


def test_v24_missing_iso(tmp_path: Path, check: IfcFileValidationCheck) -> None:
    path = _write(tmp_path, NO_ISO)
    result = check.run(_ctx(path))
    assert result.status == CheckStatus.FAIL
    assert result.findings[0].code == "V2.4"


def test_v25_missing_file_schema(tmp_path: Path, check: IfcFileValidationCheck) -> None:
    path = _write(tmp_path, NO_SCHEMA)
    result = check.run(_ctx(path))
    assert result.status == CheckStatus.FAIL
    assert result.findings[0].code == "V2.5"


def test_v26_ifcopenshell_opens(tmp_path: Path, check: IfcFileValidationCheck) -> None:
    pytest.importorskip("ifcopenshell")
    path = _write(tmp_path, MINIMAL_IFC)
    result = check.run(_ctx(path))
    assert result.status == CheckStatus.PASS
    assert result.stats.get("schema") == "IFC2X3"


def test_schema_warn_for_ifc4(tmp_path: Path, check: IfcFileValidationCheck) -> None:
    pytest.importorskip("ifcopenshell")
    path = _write(tmp_path, IFC4_HEADER)
    result = check.run(_ctx(path))
    assert result.status == CheckStatus.WARN
    assert result.findings[0].code == "SCHEMA"


def test_schema_fail_policy(tmp_path: Path, check: IfcFileValidationCheck) -> None:
    pytest.importorskip("ifcopenshell")
    path = _write(tmp_path, IFC4_HEADER)
    settings = AppSettings(unknown_schema_policy="fail")
    result = check.run(_ctx(path, settings=settings))
    assert result.status == CheckStatus.FAIL
    assert result.findings[0].code == "SCHEMA"
