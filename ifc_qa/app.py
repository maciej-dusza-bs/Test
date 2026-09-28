"""Punkt wejścia Streamlit: streamlit run ifc_qa/app.py"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ifc_qa.ui.wizard import render

render()
