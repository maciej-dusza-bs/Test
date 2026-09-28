from pathlib import Path

import yaml
from pydantic import BaseModel


class AppSettings(BaseModel):
    min_file_size_bytes: int = 10
    max_file_size_bytes: int = 50 * 1024 * 1024
    header_peek_bytes: int = 4096
    header_scan_bytes: int = 65536
    expected_schema: str = "IFC2X3"
    unknown_schema_policy: str = "warn"


def load_settings(path: Path | None = None) -> AppSettings:
    settings_path = path or Path(__file__).with_name("settings.yaml")
    if not settings_path.exists():
        return AppSettings()
    data = yaml.safe_load(settings_path.read_text(encoding="utf-8")) or {}
    return AppSettings.model_validate(data)


DEFAULT_SETTINGS = load_settings()
