from __future__ import annotations

from datetime import datetime, timezone

from ifc_qa.core.models import CheckResult, CheckStatus


class ResultStore:
    def __init__(self) -> None:
        self.results: list[CheckResult] = []
        self.started_at = datetime.now(timezone.utc)

    def add(self, result: CheckResult) -> None:
        self.results.append(result)

    def upsert(self, result: CheckResult) -> None:
        for index, existing in enumerate(self.results):
            if existing.check_id == result.check_id:
                self.results[index] = result
                return
        self.add(result)

    def drop_from(self, check_ids: set[str]) -> None:
        self.results = [item for item in self.results if item.check_id not in check_ids]

    def overall_status(self) -> CheckStatus:
        statuses = {r.status for r in self.results}
        if CheckStatus.FAIL in statuses or CheckStatus.ERROR in statuses:
            return CheckStatus.FAIL
        if CheckStatus.WARN in statuses:
            return CheckStatus.WARN
        if statuses and statuses <= {CheckStatus.STUB, CheckStatus.SKIP}:
            return CheckStatus.STUB
        if CheckStatus.PASS in statuses:
            return CheckStatus.PASS
        return CheckStatus.SKIP

    def get(self, check_id: str) -> CheckResult | None:
        for result in self.results:
            if result.check_id == check_id:
                return result
        return None
