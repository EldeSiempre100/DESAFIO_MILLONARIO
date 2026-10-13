from __future__ import annotations

import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
for source in (REPOSITORY_ROOT / "online" / "src", REPOSITORY_ROOT / "v3_1" / "src"):
    source_text = str(source)
    if source_text not in sys.path:
        sys.path.insert(0, source_text)
