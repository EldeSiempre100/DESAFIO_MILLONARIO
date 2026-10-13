from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from time import perf_counter


AVATAR_CATALOG: tuple[dict[str, str], ...] = (
    {"id": "explorer", "symbol": "🤠", "label": "Explorador"},
    {"id": "strategist", "symbol": "🤓", "label": "Estratega"},
    {"id": "creative", "symbol": "😎", "label": "Creativo"},
    {"id": "curious", "symbol": "🧐", "label": "Curioso"},
    {"id": "scientist", "symbol": "😄", "label": "Optimista"},
    {"id": "digital", "symbol": "🙂", "label": "Sereno"},
    {"id": "adventurer", "symbol": "🥳", "label": "Entusiasta"},
    {"id": "star", "symbol": "🤩", "label": "Estrella"},
)
AVATAR_BY_ID = {item["id"]: item for item in AVATAR_CATALOG}
DEFAULT_AVATAR_ID = "explorer"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class RoomStatus(StrEnum):
    OPEN = "open"
    LOCKED = "locked"
    CLOSED = "closed"


class OpeningStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class SubmissionStatus(StrEnum):
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    LATE = "late"
    INVALID = "invalid"
    FORBIDDEN = "forbidden"


@dataclass(slots=True)
class Participant:
    participant_id: str
    alias: str
    token_hash: str
    device_id: str
    avatar: str = DEFAULT_AVATAR_ID
    role: str = "audience"
    joined_at: str = field(default_factory=utc_now)
    last_seen: str = field(default_factory=utc_now)
    connected: bool = False
    removed: bool = False

    def public_dict(self) -> dict[str, object]:
        avatar = AVATAR_BY_ID.get(self.avatar, AVATAR_BY_ID[DEFAULT_AVATAR_ID])
        return {
            "participant_id": self.participant_id,
            "alias": self.alias,
            "avatar": avatar["id"],
            "avatar_symbol": avatar["symbol"],
            "avatar_label": avatar["label"],
            "role": self.role,
            "connected": self.connected,
        }


@dataclass(frozen=True, slots=True)
class RemoteResponse:
    opening_id: str
    participant_id: str
    answer: str
    received_at: str
    elapsed_ms: int
    sequence_no: int


@dataclass(slots=True)
class RemoteOpening:
    opening_id: str
    opening_type: str
    question_id: str
    duration_ms: int
    eligible_ids: frozenset[str]
    opened_at: str = field(default_factory=utc_now)
    opened_perf: float = field(default_factory=perf_counter)
    status: OpeningStatus = OpeningStatus.OPEN
    responses: dict[str, RemoteResponse] = field(default_factory=dict)

    @property
    def closes_perf(self) -> float:
        return self.opened_perf + (self.duration_ms / 1000)

    def public_dict(self) -> dict[str, object]:
        return {
            "opening_id": self.opening_id,
            "type": self.opening_type,
            "duration_ms": self.duration_ms,
            "opened_at": self.opened_at,
            "status": self.status.value,
            "allowed_answers": ["A", "B", "C", "D"],
            "display_mode": "keys_only",
        }
