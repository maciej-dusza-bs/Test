from __future__ import annotations

import time
import traceback

from ifc_qa.core.models import CheckContext, CheckResult, CheckStatus, Finding
from ifc_qa.core.registry import registry
from ifc_qa.core.result_store import ResultStore

GATE_CHECK_ID = "F2"


class CheckPipeline:
    def __init__(self, gate_check_id: str = GATE_CHECK_ID) -> None:
        self.gate_check_id = gate_check_id

    def run(self, ctx: CheckContext) -> ResultStore:
        store = ResultStore()
        gate = registry.get(self.gate_check_id)
        store.add(self._execute(gate, ctx))

        gate_result = store.get(self.gate_check_id)
        if gate_result is None or gate_result.status == CheckStatus.FAIL:
            return store
        if gate_result.status == CheckStatus.ERROR:
            return store

        for check in registry.items():
            if check.id == self.gate_check_id:
                continue
            if check.id not in ctx.selected_check_ids:
                continue
            store.add(self._execute(check, ctx))
        return store

    def _execute(self, check, ctx: CheckContext) -> CheckResult:
        started = time.perf_counter()
        try:
            result = check.run(ctx)
        except Exception as exc:
            result = CheckResult(
                check_id=check.id,
                name=check.name,
                status=CheckStatus.ERROR,
                summary=f"Nieoczekiwany błąd: {exc}",
                findings=[
                    Finding(
                        code="INTERNAL",
                        severity=CheckStatus.ERROR,
                        message=str(exc),
                        details=traceback.format_exc(),
                    )
                ],
            )
        result.duration_ms = round((time.perf_counter() - started) * 1000, 2)
        return result
