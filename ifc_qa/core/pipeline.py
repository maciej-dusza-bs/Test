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

    def run_one(self, ctx: CheckContext, check_id: str) -> CheckResult:
        return self._execute(registry.get(check_id), ctx)

    def run(self, ctx: CheckContext) -> ResultStore:
        store = ResultStore()
        gate_result = self.run_one(ctx, self.gate_check_id)
        store.add(gate_result)
        if gate_result.status in {CheckStatus.FAIL, CheckStatus.ERROR}:
            return store

        for check in registry.items():
            if check.id == self.gate_check_id:
                continue
            if check.id not in ctx.selected_check_ids:
                continue
            store.add(self.run_one(ctx, check.id))
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
