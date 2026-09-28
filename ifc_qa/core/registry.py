from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ifc_qa.checks.base import BaseCheck


class CheckRegistry:
    """Rejestr niezależnych sprawdzeń. UI i raport czytają wyłącznie stąd."""

    def __init__(self) -> None:
        self._checks: dict[str, BaseCheck] = {}

    def register(self, check: BaseCheck) -> None:
        if check.id in self._checks:
            raise ValueError(f"Duplikat identyfikatora sprawdzenia: {check.id}")
        self._checks[check.id] = check

    def get(self, check_id: str) -> BaseCheck:
        return self._checks[check_id]

    def items(self) -> list[BaseCheck]:
        return list(self._checks.values())

    def optional_items(self) -> list[BaseCheck]:
        return [c for c in self._checks.values() if not c.required]


registry = CheckRegistry()


def register_check(cls: type[BaseCheck]) -> type[BaseCheck]:
    registry.register(cls())
    return cls
