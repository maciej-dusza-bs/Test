from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import streamlit as st

from ifc_qa.checks import f2_ifc_validation  # noqa: F401  — rejestracja
from ifc_qa.checks import f3_metadata  # noqa: F401
from ifc_qa.checks import f4_allowed_classes  # noqa: F401
from ifc_qa.checks import f5_required_params  # noqa: F401
from ifc_qa.config import DEFAULT_SETTINGS
from ifc_qa.core.models import CheckContext, CheckStatus
from ifc_qa.core.pipeline import CheckPipeline
from ifc_qa.core.registry import registry
from ifc_qa.core.result_store import ResultStore
from ifc_qa.io.docx_adapter import load_docx
from ifc_qa.io.report_xlsx import build_report_bytes
from ifc_qa.io.xlsx_adapter import load_xlsx

STATUS_COLORS = {
    CheckStatus.PASS: "green",
    CheckStatus.FAIL: "red",
    CheckStatus.WARN: "orange",
    CheckStatus.STUB: "gray",
    CheckStatus.SKIP: "gray",
    CheckStatus.ERROR: "red",
}


def _init_state() -> None:
    st.session_state.setdefault("store", None)
    st.session_state.setdefault("report_bytes", None)
    st.session_state.setdefault("last_error", None)


def _save_upload(upload, suffix: str, directory: Path) -> Path:
    safe_name = Path(upload.name).name
    target = directory / safe_name
    if target.suffix.lower() != suffix.lower():
        target = directory / f"{target.stem}{suffix}"
    target.write_bytes(upload.getvalue())
    return target


def _parse_attachment(kind: str, path: Path):
    if kind == "xlsx":
        return load_xlsx(path)
    if kind == "docx":
        return load_docx(path)
    return {"path": str(path)}


def render() -> None:
    st.set_page_config(page_title="Kontrola IFC", layout="wide")
    _init_state()
    st.title("Kontrola modelu IFC")
    st.caption("Aplikacja lokalna — demo IFC2X3, plik do 50 MiB.")

    with st.sidebar:
        st.subheader("1. Wybór sprawdzeń")
        selected: list[str] = []
        for check in registry.items():
            if check.required:
                st.checkbox(f"{check.id} — {check.name}", value=True, disabled=True)
                selected.append(check.id)
            else:
                if st.checkbox(f"{check.id} — {check.name}", value=True, key=f"chk_{check.id}"):
                    selected.append(check.id)

    st.subheader("2. Wczytanie pliku IFC")
    ifc_upload = st.file_uploader("Wybierz plik IFC", type=None, key="ifc_file")

    st.subheader("3. Załączniki (opcjonalnie)")
    st.caption("F4 i F5 w tej iteracji są stubami — pliki zostaną sparsowane, ale nie wpływają na reguły.")
    attachment_uploads: dict[str, dict[str, object]] = {}
    optional = [c for c in registry.items() if c.id in selected and c.requires_attachments]
    if optional:
        cols = st.columns(max(len(optional), 1))
        for column, check in zip(cols, optional):
            with column:
                st.markdown(f"**{check.id}**")
                for kind in check.requires_attachments:
                    ext = "xlsx" if kind == "xlsx" else "docx"
                    uploaded = st.file_uploader(
                        f"{check.id}: {kind.upper()}",
                        type=[ext],
                        key=f"att_{check.id}_{kind}",
                    )
                    if uploaded is not None:
                        attachment_uploads.setdefault(check.id, {})[kind] = uploaded
    else:
        st.info("Wybrane sprawdzenia nie wymagają załączników.")

    run = st.button("Uruchom kontrolę", type="primary", disabled=ifc_upload is None)

    if run:
        _run_pipeline(ifc_upload, selected, attachment_uploads)

    store: ResultStore | None = st.session_state.get("store")
    if store is None:
        return

    st.subheader("4. Wyniki")
    gate = store.get("F2")
    if gate and gate.status == CheckStatus.FAIL:
        st.error(gate.summary)
        st.warning("Wgraj poprawny plik IFC i uruchom kontrolę ponownie.")

    for result in store.results:
        color = STATUS_COLORS.get(result.status, "gray")
        with st.expander(f"{result.check_id} — {result.name}  [{result.status.value}]", expanded=True):
            st.markdown(f":{color}[**{result.status.value}**] — {result.summary}")
            st.caption(f"Czas: {result.duration_ms} ms")
            if result.findings:
                st.table(
                    [
                        {
                            "kod": f.code,
                            "status": f.severity.value,
                            "komunikat": f.message,
                        }
                        for f in result.findings
                    ]
                )
            else:
                st.write("Brak szczegółowych findings.")

    report_bytes = st.session_state.get("report_bytes")
    if report_bytes:
        st.download_button(
            "Pobierz Raport Kontroli (XLSX)",
            data=report_bytes,
            file_name="raport_kontroli.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


def _run_pipeline(ifc_upload, selected: list[str], attachment_uploads: dict) -> None:
    with TemporaryDirectory(prefix="ifc_qa_") as tmp:
        tmp_path = Path(tmp)
        ifc_path = tmp_path / ifc_upload.name
        ifc_path.write_bytes(ifc_upload.getvalue())

        attachments: dict = {}
        for check_id, files in attachment_uploads.items():
            parsed: dict = {}
            for kind, upload in files.items():
                suffix = ".xlsx" if kind == "xlsx" else ".docx"
                saved = _save_upload(upload, suffix, tmp_path)
                parsed[kind] = _parse_attachment(kind, saved)
            attachments[check_id] = parsed

        ctx = CheckContext(
            file_name=ifc_upload.name,
            file_path=ifc_path,
            file_size=ifc_path.stat().st_size,
            selected_check_ids=selected,
            attachments=attachments,
            settings=DEFAULT_SETTINGS,
        )
        store = CheckPipeline().run(ctx)
        st.session_state.store = store
        st.session_state.report_bytes = build_report_bytes(store, ctx)

        if store.get("F2") and store.get("F2").status == CheckStatus.FAIL:
            st.session_state.last_error = store.get("F2").summary
        else:
            st.session_state.last_error = None
