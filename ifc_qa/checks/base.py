from __future__ import annotations

from abc import ABC, abstractmethod

from ifc_qa.core.models import CheckContext, CheckResult, CheckStatus, Finding


class BaseCheck(ABC):
    id: str
    name: str
    group: str = "ogólne"
    required: bool = False
    requires_attachments: tuple[str, ...] = ()

    @abstractmethod
    def run(self, ctx: CheckContext) -> CheckResult:
        raise NotImplementedError

    def stub_result(self, summary: str | None = None) -> CheckResult:
        return CheckResult(
            check_id=self.id,
            name=self.name,
            status=CheckStatus.STUB,
            summary=summary or "Niezaimplementowane — iteracja 2",
            findings=[],
            stats={"implemented": False},
        )

    def fail(self, code: str, message: str, **kwargs) -> CheckResult:
        return CheckResult(
            check_id=self.id,
            name=self.name,
            status=CheckStatus.FAIL,
            summary=message,
            findings=[Finding(code=code, severity=CheckStatus.FAIL, message=message, **kwargs)],
        )
