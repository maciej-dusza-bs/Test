from __future__ import annotations

from pathlib import Path
from typing import Any


def load_docx(path: Path) -> dict[str, Any]:
    """Parsuje DOCX do tekstu i listy akapitów. Logika sprawdzeń nie czyta pliku bezpośrednio."""
    from docx import Document

    document = Document(str(path))
    paragraphs = [p.text for p in document.paragraphs]
    return {
        "paragraphs": paragraphs,
        "text": "\n".join(paragraphs),
    }
