"""Backend y superficies web de Desafío Millonario."""

from __future__ import annotations

import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
V3_SOURCE = REPOSITORY_ROOT / "v3_1" / "src"
if str(V3_SOURCE) not in sys.path:
    sys.path.insert(0, str(V3_SOURCE))
