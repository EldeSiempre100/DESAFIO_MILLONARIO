from __future__ import annotations

import hashlib
import re
import secrets
import threading
from dataclasses import dataclass
from time import perf_counter
from typing import Iterable

from .models import (
    AVATAR_BY_ID,
    DEFAULT_AVATAR_ID,
    OpeningStatus,
    Participant,
    RemoteOpening,
    RemoteResponse,
    RoomStatus,
    SubmissionStatus,
    utc_now,
)


ALIAS_PATTERN = re.compile(r"^[\w .áéíóúÁÉÍÓÚñÑüÜ-]{2,24}$", re.UNICODE)


class RoomError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class JoinResult:
    participant: Participant
    token: str


@dataclass(frozen=True, slots=True)
class SubmissionResult:
    status: SubmissionStatus
    response: RemoteResponse | None
    message: str

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": self.status.value,
            "message": self.message,
        }
        if self.response is not None:
            payload.update(
                {
                    "opening_id": self.response.opening_id,
                    "alternative": self.response.answer,
                    "received_at": self.response.received_at,
                    "elapsed_ms": self.response.elapsed_ms,
                }
            )
        return payload


class RoomManager:
    """Fuente de verdad thread-safe para sala, identidad y respuestas."""

    def __init__(
        self,
        *,
        session_id: str,
        room_code: str,
        max_participants: int = 30,
    ) -> None:
        self.session_id = session_id
        self.room_code = room_code
        self.max_participants = max(1, min(30, int(max_participants)))
        self.status = RoomStatus.OPEN
        self.participants: dict[str, Participant] = {}
        self._token_index: dict[str, str] = {}
        self._device_index: dict[str, str] = {}
        self.current_opening: RemoteOpening | None = None
        self._sequence = 0
        self._lock = threading.RLock()

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_alias(alias: str) -> str:
        return " ".join(str(alias).strip().split())

    @staticmethod
    def _normalize_avatar(avatar: str) -> str:
        clean_avatar = str(avatar).strip().casefold()
        return clean_avatar if clean_avatar in AVATAR_BY_ID else DEFAULT_AVATAR_ID

    def join(
        self,
        alias: str,
        device_id: str,
        avatar: str = DEFAULT_AVATAR_ID,
    ) -> JoinResult:
        normalized_alias = self._normalize_alias(alias)
        normalized_avatar = self._normalize_avatar(avatar)
        clean_device_id = str(device_id).strip()[:80]
        with self._lock:
            if self.status is not RoomStatus.OPEN:
                raise RoomError("room_locked", "La sala ya está cerrada.")
            if not ALIAS_PATTERN.fullmatch(normalized_alias):
                raise RoomError(
                    "invalid_alias",
                    "Usa un alias de 2 a 24 caracteres sin símbolos especiales.",
                )
            if not clean_device_id:
                raise RoomError("invalid_device", "El dispositivo no tiene identidad.")
            previous_id = self._device_index.get(clean_device_id)
            previous = self.participants.get(previous_id or "")
            if previous is not None and not previous.removed:
                if any(
                    participant.participant_id != previous.participant_id
                    and participant.alias.casefold() == normalized_alias.casefold()
                    and not participant.removed
                    for participant in self.participants.values()
                ):
                    raise RoomError("alias_taken", "Ese alias ya está en uso.")
                # Recuperación simple si el navegador perdió su token: se
                # conserva el participante y se reemplaza su credencial.
                self._token_index.pop(previous.token_hash, None)
                token = secrets.token_urlsafe(32)
                previous.token_hash = self._token_hash(token)
                previous.alias = normalized_alias
                previous.avatar = normalized_avatar
                previous.last_seen = utc_now()
                previous.connected = True
                self._token_index[previous.token_hash] = previous.participant_id
                return JoinResult(previous, token)

            if any(
                participant.alias.casefold() == normalized_alias.casefold()
                and not participant.removed
                for participant in self.participants.values()
            ):
                raise RoomError("alias_taken", "Ese alias ya está en uso.")
            active = [
                participant
                for participant in self.participants.values()
                if not participant.removed
            ]
            if len(active) >= self.max_participants:
                raise RoomError("room_full", "La sala alcanzó su capacidad máxima.")

            participant_id = f"par_{secrets.token_hex(8)}"
            token = secrets.token_urlsafe(32)
            token_hash = self._token_hash(token)
            participant = Participant(
                participant_id=participant_id,
                alias=normalized_alias,
                token_hash=token_hash,
                device_id=clean_device_id,
                avatar=normalized_avatar,
            )
            self.participants[participant_id] = participant
            self._token_index[token_hash] = participant_id
            self._device_index[clean_device_id] = participant_id
            return JoinResult(participant, token)

    def authenticate(self, token: str) -> Participant:
        token_hash = self._token_hash(str(token))
        with self._lock:
            participant_id = self._token_index.get(token_hash)
            participant = self.participants.get(participant_id or "")
            if participant is None or participant.removed:
                raise RoomError("invalid_token", "La identidad de la sala no es válida.")
            return participant

    def reconnect(self, token: str) -> Participant:
        participant = self.authenticate(token)
        with self._lock:
            participant.last_seen = utc_now()
            participant.connected = True
            return participant

    def set_connected(self, participant_id: str, connected: bool) -> None:
        with self._lock:
            participant = self.participants.get(participant_id)
            if participant is None or participant.removed:
                return
            participant.connected = connected
            participant.last_seen = utc_now()

    def heartbeat(self, token: str) -> Participant:
        participant = self.authenticate(token)
        with self._lock:
            participant.last_seen = utc_now()
            participant.connected = True
            return participant

    def remove(self, participant_id: str) -> None:
        with self._lock:
            participant = self.participants.get(participant_id)
            if participant is None:
                raise RoomError("not_found", "El participante no existe.")
            participant.removed = True
            participant.connected = False

    def lock(self) -> None:
        with self._lock:
            if self.status is not RoomStatus.OPEN:
                raise RoomError("invalid_state", "La sala no está abierta.")
            self.status = RoomStatus.LOCKED

    def close(self) -> None:
        with self._lock:
            self.status = RoomStatus.CLOSED
            if self.current_opening is not None:
                self.current_opening.status = OpeningStatus.CLOSED

    def set_selected(self, participant_ids: Iterable[str]) -> None:
        selected = set(participant_ids)
        with self._lock:
            if len(selected) != 2:
                raise RoomError("invalid_selection", "Debes seleccionar dos personas.")
            if not selected.issubset(self.participants):
                raise RoomError("invalid_selection", "La selección contiene un alias inválido.")
            for participant in self.participants.values():
                if participant.removed:
                    continue
                participant.role = (
                    "selected" if participant.participant_id in selected else "audience"
                )

    def open_remote(
        self,
        *,
        opening_type: str,
        question_id: str,
        duration_ms: int,
        eligible_ids: Iterable[str] | None = None,
    ) -> RemoteOpening:
        with self._lock:
            if self.current_opening is not None:
                self.current_opening.status = OpeningStatus.CLOSED
            if eligible_ids is None:
                eligible = {
                    participant.participant_id
                    for participant in self.participants.values()
                    if not participant.removed
                }
            else:
                eligible = {
                    participant_id
                    for participant_id in eligible_ids
                    if participant_id in self.participants
                    and not self.participants[participant_id].removed
                }
            opening = RemoteOpening(
                opening_id=f"open_{opening_type}_{secrets.token_hex(5)}",
                opening_type=opening_type,
                question_id=question_id,
                duration_ms=max(1000, int(duration_ms)),
                eligible_ids=frozenset(eligible),
            )
            self.current_opening = opening
            return opening

    def submit_answer(
        self,
        *,
        token: str,
        opening_id: str,
        answer: str,
    ) -> SubmissionResult:
        participant = self.authenticate(token)
        normalized_answer = str(answer).strip().upper()
        with self._lock:
            opening = self.current_opening
            if normalized_answer not in {"A", "B", "C", "D"}:
                return SubmissionResult(
                    SubmissionStatus.INVALID,
                    None,
                    "La alternativa debe estar entre A y D.",
                )
            if opening is None or opening.opening_id != opening_id:
                return SubmissionResult(
                    SubmissionStatus.LATE,
                    None,
                    "La votación ya no está disponible.",
                )
            if participant.participant_id not in opening.eligible_ids:
                return SubmissionResult(
                    SubmissionStatus.FORBIDDEN,
                    None,
                    "Tu dispositivo no está habilitado para esta votación.",
                )
            existing = opening.responses.get(participant.participant_id)
            if existing is not None:
                return SubmissionResult(
                    SubmissionStatus.DUPLICATE,
                    existing,
                    "La primera respuesta ya quedó registrada.",
                )
            now_perf = perf_counter()
            if opening.status is not OpeningStatus.OPEN or now_perf > opening.closes_perf:
                return SubmissionResult(
                    SubmissionStatus.LATE,
                    None,
                    "La respuesta llegó después del cierre.",
                )
            self._sequence += 1
            response = RemoteResponse(
                opening_id=opening.opening_id,
                participant_id=participant.participant_id,
                answer=normalized_answer,
                received_at=utc_now(),
                elapsed_ms=max(0, int((now_perf - opening.opened_perf) * 1000)),
                sequence_no=self._sequence,
            )
            opening.responses[participant.participant_id] = response
            participant.last_seen = utc_now()
            return SubmissionResult(
                SubmissionStatus.ACCEPTED,
                response,
                "Respuesta recibida.",
            )

    def close_opening(self, *, correct_index: int | None = None) -> dict[str, object]:
        with self._lock:
            opening = self.current_opening
            if opening is None:
                raise RoomError("no_opening", "No existe una votación activa.")
            opening.status = OpeningStatus.CLOSED
            counts = [0, 0, 0, 0]
            ordered = sorted(
                opening.responses.values(),
                key=lambda item: (item.elapsed_ms, item.sequence_no, item.participant_id),
            )
            for response in ordered:
                counts["ABCD".index(response.answer)] += 1
            total = sum(counts)
            percentages = [
                round((count / total) * 100) if total else 0 for count in counts
            ]
            candidates: list[dict[str, object]] = []
            if correct_index is not None and 0 <= correct_index <= 3:
                correct_letter = "ABCD"[correct_index]
                for response in ordered:
                    if response.answer != correct_letter:
                        continue
                    participant = self.participants.get(response.participant_id)
                    if participant is None or participant.removed:
                        continue
                    candidates.append(
                        {
                            "participant_id": participant.participant_id,
                            "alias": participant.alias,
                            "avatar": participant.public_dict()["avatar"],
                            "avatar_symbol": participant.public_dict()["avatar_symbol"],
                            "elapsed_ms": response.elapsed_ms,
                            "alternative": response.answer,
                        }
                    )
                    if len(candidates) == 2:
                        break
            return {
                "opening_id": opening.opening_id,
                "type": opening.opening_type,
                "counts": counts,
                "percentages": percentages,
                "total": total,
                "candidates": candidates,
            }

    def public_snapshot(self, participant_id: str | None = None) -> dict[str, object]:
        with self._lock:
            active = [
                participant
                for participant in self.participants.values()
                if not participant.removed
            ]
            me = self.participants.get(participant_id or "")
            opening = self.current_opening
            public_opening: dict[str, object] | None = None
            if (
                opening is not None
                and opening.status is OpeningStatus.OPEN
                and participant_id in opening.eligible_ids
            ):
                public_opening = opening.public_dict()
            return {
                "session_id": self.session_id,
                "room_code": self.room_code,
                "status": self.status.value,
                "capacity": self.max_participants,
                "connected": sum(item.connected for item in active),
                "enrolled": len(active),
                "participants": [item.public_dict() for item in active],
                "me": me.public_dict() if me is not None and not me.removed else None,
                "opening": public_opening,
            }

    def host_snapshot(self) -> dict[str, object]:
        snapshot = self.public_snapshot()
        with self._lock:
            opening = self.current_opening
            snapshot["answers_received"] = (
                len(opening.responses) if opening is not None else 0
            )
            snapshot["opening_eligible"] = (
                len(opening.eligible_ids) if opening is not None else 0
            )
        return snapshot

    def reset_for_replay(self, *, session_id: str) -> None:
        """Reabre la misma sala conservando teléfonos y credenciales."""
        with self._lock:
            self.session_id = str(session_id)
            self.status = RoomStatus.OPEN
            self.current_opening = None
            self._sequence = 0
            for participant in self.participants.values():
                if participant.removed:
                    continue
                participant.role = "audience"
                participant.last_seen = utc_now()
