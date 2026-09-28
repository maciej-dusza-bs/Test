from pathlib import Path

import pytest

import ifc_qa.checks  # noqa: F401
from ifc_qa.config import AppSettings
from ifc_qa.core.models import CheckContext, CheckStatus
from ifc_qa.core.pipeline import CheckPipeline
from ifc_qa.core.registry import registry

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


def test_registry_contains_f2_to_f5() -> None:
    ids = {c.id for c in registry.items()}
    assert ids == {"F2", "F3", "F4", "F5"}


def test_pipeline_stops_on_f2_fail(tmp_path: Path) -> None:
    path = tmp_path / "bad.ifc"
    path.write_text("not-ifc-content-xx", encoding="utf-8")
    ctx = CheckContext(
        file_name=path.name,
        file_path=path,
        file_size=path.stat().st_size,
        selected_check_ids=["F2", "F3", "F4", "F5"],
        settings=AppSettings(),
    )
    store = CheckPipeline().run(ctx)
    assert [r.check_id for r in store.results] == ["F2"]
    assert store.results[0].status == CheckStatus.FAIL


def test_pipeline_runs_stubs_after_pass(tmp_path: Path) -> None:
    pytest.importorskip("ifcopenshell")
    path = tmp_path / "model.ifc"
    path.write_text(MINIMAL_IFC, encoding="utf-8")
    ctx = CheckContext(
        file_name=path.name,
        file_path=path,
        file_size=path.stat().st_size,
        selected_check_ids=["F2", "F3", "F4", "F5"],
        settings=AppSettings(),
    )
    store = CheckPipeline().run(ctx)
    assert [r.check_id for r in store.results] == ["F2", "F3", "F4", "F5"]
    assert store.results[0].status == CheckStatus.PASS
    assert all(r.status == CheckStatus.STUB for r in store.results[1:])


def test_unselected_optional_checks_are_skipped(tmp_path: Path) -> None:
    pytest.importorskip("ifcopenshell")
    path = tmp_path / "model.ifc"
    path.write_text(MINIMAL_IFC, encoding="utf-8")
    ctx = CheckContext(
        file_name=path.name,
        file_path=path,
        file_size=path.stat().st_size,
        selected_check_ids=["F2", "F3"],
        settings=AppSettings(),
    )
    store = CheckPipeline().run(ctx)
    assert [r.check_id for r in store.results] == ["F2", "F3"]
