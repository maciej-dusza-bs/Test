from ifc_qa.checks.base import BaseCheck
from ifc_qa.core.models import CheckContext, CheckResult
from ifc_qa.core.registry import register_check


@register_check
class AllowedIfcClassesCheck(BaseCheck):
    id = "F4"
    name = "Weryfikacja dopuszczalnych klas IFC"
    group = "model"
    requires_attachments = ("xlsx",)

    def run(self, ctx: CheckContext) -> CheckResult:
        return self.stub_result()
