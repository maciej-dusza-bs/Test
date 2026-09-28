from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from ifc_qa.checks import f2_ifc_validation  # noqa: F401  — rejestracja
from ifc_qa.checks import f3_metadata  # noqa: F401
from ifc_qa.checks import f4_allowed_classes  # noqa: F401
from ifc_qa.checks import f5_required_params  # noqa: F401
from ifc_qa.config import DEFAULT_SETTINGS
from ifc_qa.core.models import CheckContext, CheckResult, CheckStatus
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

OK_STATUSES = {CheckStatus.PASS, CheckStatus.WARN, CheckStatus.STUB}


def _init_state() -> None:
    st.session_state.setdefault("store", ResultStore())
    st.session_state.setdefault("ctx", None)
    st.session_state.setdefault("work_dir", None)
    st.session_state.setdefault("unlocked_index", 0)
    st.session_state.setdefault("report_bytes", None)
    st.session_state.setdefault("notice", None)


def _work_dir() -> Path:
    if not st.session_state.work_dir:
        st.session_state.work_dir = tempfile.mkdtemp(prefix="ifc_qa_")
    return Path(st.session_state.work_dir)


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


def _selected_checks() -> list:
    chosen: list = []
    for check in registry.items():
        if check.required:
            chosen.append(check)
            continue
        if st.session_state.get(f"chk_{check.id}", True):
            chosen.append(check)
    return chosen


def _reset_flow() -> None:
    st.session_state.store = ResultStore()
    st.session_state.ctx = None
    st.session_state.unlocked_index = 0
    st.session_state.report_bytes = None
    st.session_state.notice = None


def _refresh_report() -> None:
    ctx = st.session_state.ctx
    if ctx is None:
        return
    st.session_state.report_bytes = build_report_bytes(st.session_state.store, ctx)


def _apply_result(checks: list, index: int, result: CheckResult) -> None:
    store: ResultStore = st.session_state.store
    store.upsert(result)
    later_ids = {item.id for item in checks[index + 1 :]}
    if result.status not in OK_STATUSES:
        st.session_state.unlocked_index = index
        store.drop_from(later_ids)
    else:
        st.session_state.unlocked_index = max(st.session_state.unlocked_index, index + 1)
    _refresh_report()


def _render_result(result: CheckResult) -> None:
    color = STATUS_COLORS.get(result.status, "gray")
    st.markdown(f":{color}[**{result.status.value}**] — {result.summary}")
    st.caption(f"Czas: {result.duration_ms} ms")
    if result.findings:
        st.markdown("**Szczegółowe uwagi**")
        st.table(
            [
                {
                    "kod": finding.code,
                    "status": finding.severity.value,
                    "komunikat": finding.message,
                }
                for finding in result.findings
            ]
        )
    elif result.status == CheckStatus.STUB:
        st.info(
            "Brak szczegółowych uwag: ten etap jest na razie szkicem (demo) "
            "i nie wypisuje jeszcze pojedynczych błędów ani pozycji z modelu."
        )
    elif result.status in {CheckStatus.PASS, CheckStatus.WARN}:
        st.info(
            "Brak szczegółowych uwag: walidacja nie wykazała pojedynczych błędów "
            "do wypisania na liście (np. GUID elementu, brakujący parametr)."
        )
    else:
        st.write("Brak szczegółowych uwag do tego etapu.")


def render() -> None:
    st.set_page_config(page_title="Kontrola IFC", layout="wide")
    _init_state()
    st.title("Kontrola modelu IFC")
    st.caption("Aplikacja lokalna — demo IFC2X3, plik do 50 MiB. Każdy etap ma osobną zakładkę.")

    with st.sidebar:
        st.subheader("Etapy kontroli")
        for check in registry.items():
            if check.required:
                st.checkbox(f"{check.id} — {check.name}", value=True, disabled=True)
            else:
                st.checkbox(f"{check.id} — {check.name}", value=True, key=f"chk_{check.id}")
        if st.button("Resetuj przebieg"):
            _reset_flow()
            st.rerun()

    checks = _selected_checks()
    labels = [check.id for check in checks] + ["Raport"]
    tabs = st.tabs(labels)
    unlocked = st.session_state.unlocked_index

    pipeline = CheckPipeline()
    for index, (tab, check) in enumerate(zip(tabs[:-1], checks)):
        with tab:
            _render_check_tab(pipeline, checks, index, check, unlocked)

    with tabs[-1]:
        _render_report_tab(checks, unlocked)


def _render_check_tab(pipeline: CheckPipeline, checks: list, index: int, check, unlocked: int) -> None:
    st.subheader(f"{check.id} — {check.name}")
    notice = st.session_state.get("notice")
    if notice and notice.get("check_id") == check.id:
        if notice.get("kind") == "error":
            st.error(notice["text"])
        else:
            st.success(notice["text"])
        st.session_state.notice = None
    if index > unlocked:
        previous = checks[index - 1]
        st.warning(f"Najpierw zakończ pomyślnie etap {previous.id} ({previous.name}).")
        return

    if check.id == "F2":
        st.markdown("Wgraj plik IFC i uruchom walidację wejściową.")
        ifc_upload = st.file_uploader(
            "Plik IFC (maks. 50 MB)",
            type=None,
            key="ifc_file",
            help="Aplikacja przyjmuje jeden plik IFC o rozmiarze od 10 B do 50 MB.",
        )
        can_run = ifc_upload is not None
    else:
        if st.session_state.ctx is None:
            st.warning("Brak wczytanego modelu IFC. Wróć do zakładki F2.")
            return
        st.caption("Ten etap korzysta z modelu IFC wczytanego w F2.")
        can_run = True
        if check.requires_attachments:
            st.markdown("Wgraj pliki wymagane przez to sprawdzenie.")
            for kind in check.requires_attachments:
                ext = "xlsx" if kind == "xlsx" else "docx"
                uploaded = st.file_uploader(
                    f"{check.id}: {kind.upper()} (maks. 50 MB)",
                    type=[ext],
                    key=f"att_{check.id}_{kind}",
                    help="Limit wczytywania pliku: 50 MB.",
                )
                if uploaded is not None:
                    saved = _save_upload(uploaded, f".{ext}", _work_dir())
                    ctx: CheckContext = st.session_state.ctx
                    attachments = dict(ctx.attachments)
                    per_check = dict(attachments.get(check.id, {}))
                    per_check[kind] = _parse_attachment(kind, saved)
                    attachments[check.id] = per_check
                    ctx.attachments = attachments
        else:
            st.info("Ten etap nie wymaga dodatkowych plików.")

    run = st.button(f"Uruchom {check.id}", type="primary", disabled=not can_run, key=f"run_{check.id}")
    if run:
        if check.id == "F2":
            _prepare_ifc_context(ifc_upload, [item.id for item in checks])
        ctx = st.session_state.ctx
        ctx.selected_check_ids = [item.id for item in checks]
        result = pipeline.run_one(ctx, check.id)
        _apply_result(checks, index, result)
        if result.status in OK_STATUSES:
            if index + 1 < len(checks):
                message = f"Etap {check.id} zakończony. Przejdź do zakładki {checks[index + 1].id}."
            else:
                message = f"Etap {check.id} zakończony. Przejdź do zakładki Raport."
            st.session_state.notice = {"check_id": check.id, "text": message, "kind": "success"}
        else:
            st.session_state.notice = {
                "check_id": check.id,
                "text": (
                    f"Etap {check.id} niezaliczony. Popraw dane i uruchom ponownie "
                    "— dalsze zakładki są zablokowane."
                ),
                "kind": "error",
            }
        st.rerun()

    existing = st.session_state.store.get(check.id)
    if existing:
        st.divider()
        st.markdown("**Wynik etapu**")
        _render_result(existing)


def _prepare_ifc_context(ifc_upload, selected_ids: list[str]) -> None:
    directory = _work_dir()
    ifc_path = directory / Path(ifc_upload.name).name
    ifc_path.write_bytes(ifc_upload.getvalue())
    st.session_state.ctx = CheckContext(
        file_name=ifc_upload.name,
        file_path=ifc_path,
        file_size=ifc_path.stat().st_size,
        selected_check_ids=selected_ids,
        attachments={},
        settings=DEFAULT_SETTINGS,
    )


def _render_report_tab(checks: list, unlocked: int) -> None:
    st.subheader("Raport Kontroli")
    if unlocked < len(checks):
        current = checks[min(unlocked, len(checks) - 1)]
        st.warning(f"Raport będzie dostępny po zakończeniu wszystkich wybranych etapów. Teraz: {current.id}.")
        return

    store: ResultStore = st.session_state.store
    if not store.results:
        st.info("Brak wyników.")
        return

    st.write(f"Status zbiorczy: **{store.overall_status().value}**")
    for result in store.results:
        with st.expander(f"{result.check_id} — {result.name} [{result.status.value}]", expanded=False):
            _render_result(result)

    report_bytes = st.session_state.get("report_bytes")
    if report_bytes:
        st.download_button(
            "Pobierz Raport Kontroli (XLSX)",
            data=report_bytes,
            file_name="raport_kontroli.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
