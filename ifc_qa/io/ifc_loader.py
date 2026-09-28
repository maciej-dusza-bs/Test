from __future__ import annotations

from pathlib import Path


class IfcLoadError(Exception):
    pass


def peek_text(path: Path, max_bytes: int) -> str:
    with path.open("rb") as handle:
        raw = handle.read(max_bytes)
    return raw.decode("utf-8", errors="replace")


def read_header_section(path: Path, max_bytes: int) -> str:
    """Czyta początek pliku aż do ENDSEC nagłówka albo limitu bajtów."""
    text = peek_text(path, max_bytes)
    marker = "ENDSEC"
    idx = text.upper().find(marker)
    if idx >= 0:
        return text[: idx + len(marker)]
    return text


def load_ifc(path: Path):
    try:
        import ifcopenshell
    except ImportError as exc:
        raise IfcLoadError("Brak biblioteki ifcopenshell. Zainstaluj zależności z requirements.txt.") from exc
    try:
        model = ifcopenshell.open(str(path))
    except Exception as exc:
        raise IfcLoadError(str(exc)) from exc
    if model is None:
        raise IfcLoadError("IfcOpenShell zwróciło pusty model.")
    return model


def schema_of(model) -> str | None:
    schema = getattr(model, "schema", None)
    if schema is None:
        return None
    return str(schema).upper()
