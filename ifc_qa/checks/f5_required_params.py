from ifc_qa.checks.base import BaseCheck
from ifc_qa.core.models import CheckContext, CheckResult
from ifc_qa.core.registry import register_check


@register_check
class RequiredParametersCheck(BaseCheck):
    id = "F5"
    name = "Weryfikacja wypełnienia wymaganych parametrów dla wybranej klasy IFC"
    group = "model"
    requires_attachments = ("xlsx",)

    def run(self, ctx: CheckContext) -> CheckResult:
        return self.stub_result()
