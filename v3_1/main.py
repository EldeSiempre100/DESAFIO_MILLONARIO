from __future__ import annotations

import sys
import traceback
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _write_startup_error() -> None:
    """Conserva un diagnóstico legible también en la versión sin consola."""
    try:
        log_dir = PROJECT_ROOT / "data" / "runtime"
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "startup_error.log").write_text(
            traceback.format_exc(),
            encoding="utf-8",
        )
    except OSError:
        pass


if __name__ == "__main__":
    try:
        from millonario_v3.app import run

        raise SystemExit(run(PROJECT_ROOT))
    except SystemExit:
        raise
    except BaseException:
        _write_startup_error()
        raise
