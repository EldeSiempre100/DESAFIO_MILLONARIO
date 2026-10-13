from __future__ import annotations

import hmac
import secrets
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True, slots=True)
class AdminSession:
    token: str
    expires_at: datetime


class AdminSessions:
    def __init__(self, password: str, *, lifetime_hours: int = 12) -> None:
        self._password = password
        self._lifetime = timedelta(hours=max(1, lifetime_hours))
        self._sessions: dict[str, AdminSession] = {}
        self._lock = threading.RLock()

    def login(self, password: str) -> AdminSession | None:
        if not hmac.compare_digest(str(password), self._password):
            return None
        session = AdminSession(
            token=secrets.token_urlsafe(32),
            expires_at=datetime.now(UTC) + self._lifetime,
        )
        with self._lock:
            self._remove_expired()
            self._sessions[session.token] = session
        return session

    def valid(self, token: str | None) -> bool:
        if not token:
            return False
        with self._lock:
            self._remove_expired()
            return token in self._sessions

    def logout(self, token: str | None) -> None:
        if not token:
            return
        with self._lock:
            self._sessions.pop(token, None)

    def _remove_expired(self) -> None:
        now = datetime.now(UTC)
        expired = [
            token
            for token, session in self._sessions.items()
            if session.expires_at <= now
        ]
        for token in expired:
            self._sessions.pop(token, None)
