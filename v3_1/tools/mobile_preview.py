from __future__ import annotations

import signal
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from millonario_v3.participation.service import ParticipationService  # noqa: E402


def main() -> int:
    service = ParticipationService(
        static_dir=PROJECT_ROOT / "mobile",
        runtime_dir=PROJECT_ROOT / "data" / "runtime",
    )
    network = service.start(
        session_id="ses_preview",
        room_code="4827",
        max_participants=30,
        preferred_port=18888,
    )
    print(f"http://127.0.0.1:{network.port}/", flush=True)
    running = True

    def stop(*_args) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        while running:
            time.sleep(0.2)
    finally:
        service.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
