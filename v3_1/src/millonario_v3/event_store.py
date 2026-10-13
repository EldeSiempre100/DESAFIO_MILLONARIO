from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class EventStore:
    """Registro local y snapshot recuperable de una sesión V3.1."""

    def __init__(self, sessions_dir: str | Path, session_id: str) -> None:
        self.sessions_dir = Path(sessions_dir)
        self.session_id = session_id
        self.events_path = self.sessions_dir / f"{session_id}.jsonl"
        self.snapshot_path = self.sessions_dir / f"{session_id}.snapshot.json"
        self._lock = threading.RLock()
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def append(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        record = {
            "event_id": f"evt_{datetime.now(UTC).timestamp():.6f}",
            "session_id": self.session_id,
            "event_type": event_type,
            "issued_at": datetime.now(UTC).isoformat(),
            "payload": payload or {},
        }
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        with self._lock:
            with self.events_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line + "\n")

    def snapshot(self, payload: dict[str, Any]) -> None:
        document = {
            "version": 1,
            "session_id": self.session_id,
            "updated_at": datetime.now(UTC).isoformat(),
            **payload,
        }
        serialized = json.dumps(document, ensure_ascii=False, indent=2)
        temporary_path: Path | None = None
        with self._lock:
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    prefix=f".{self.session_id}.",
                    suffix=".tmp",
                    dir=self.sessions_dir,
                    delete=False,
                ) as temporary:
                    temporary.write(serialized)
                    temporary_path = Path(temporary.name)
                os.replace(temporary_path, self.snapshot_path)
                temporary_path = None
            finally:
                if temporary_path is not None:
                    temporary_path.unlink(missing_ok=True)
