from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ifc_qa.config import AppSettings, DEFAULT_SETTINGS


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"
    ERROR = "ERROR"
    STUB = "STUB"


class Finding(BaseModel):
    code: str
    severity: CheckStatus
    message: str
    ifc_guid: str | None = None
    ifc_class: str | None = None
    details: str | None = None


class CheckResult(BaseModel):
    check_id: str
    name: str
    status: CheckStatus
    summary: str
    findings: list[Finding] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)
    duration_ms: float = 0.0


class CheckContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    file_name: str
    file_path: Path | None = None
    file_size: int = 0
    selected_check_ids: list[str] = Field(default_factory=list)
    model: Any = None
    schema_name: str | None = None
    attachments: dict[str, Any] = Field(default_factory=dict)
    settings: AppSettings = Field(default_factory=lambda: DEFAULT_SETTINGS)
