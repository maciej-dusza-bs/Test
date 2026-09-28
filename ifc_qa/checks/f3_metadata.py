from ifc_qa.checks.base import BaseCheck
from ifc_qa.core.models import CheckContext, CheckResult
from ifc_qa.core.registry import register_check


@register_check
class MetadataVerificationCheck(BaseCheck):
    id = "F3"
    name = "Weryfikacja metadanych modelu"
    group = "model"

    def run(self, ctx: CheckContext) -> CheckResult:
        return self.stub_result()
