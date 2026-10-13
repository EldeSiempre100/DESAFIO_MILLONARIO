from __future__ import annotations

import random
import secrets
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from millonario_v3.engine import GameSession
from millonario_v3.model import Project
from millonario_v3.participation.models import RoomStatus, utc_now
from millonario_v3.participation.room import RoomError, RoomManager
from millonario_v3.session import SessionError, SessionState
from millonario_v3.storage import load_project

from .session import OnlineSessionOrchestrator


QUALIFIER_DURATION_MS = 30_000
QUESTION_DURATION_MS = 45_000
LIFELINE_DURATION_MS = 15_000
LETTERS = "ABCD"


def _invalid_state(error: Exception) -> RoomError:
    return RoomError("invalid_state", str(error))


@dataclass(slots=True)
class OnlineRoom:
    """Fuente autoritativa del flujo web completo de la experiencia."""

    game_id: str
    room_code: str
    project: Project
    manager: RoomManager
    orchestrator: OnlineSessionOrchestrator
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    qualifier_results_data: dict[str, Any] | None = None
    selection_pool: list[dict[str, Any]] = field(default_factory=list)
    preselected_ids: list[str] = field(default_factory=list)
    question_session: GameSession | None = None
    question_opening_id: str = ""
    question_opened_at: str = ""
    question_started_perf: float = 0.0
    question_remaining_ms: int = QUESTION_DURATION_MS
    question_elapsed_ms: int = 0
    question_response: dict[str, Any] | None = None
    question_result: dict[str, Any] | None = None
    active_lifeline: str | None = None
    lifeline_opening_id: str = ""
    lifeline_opened_at: str = ""
    audience_results: dict[str, Any] | None = None
    event_sequence: int = 0
    last_event: dict[str, Any] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    @property
    def state(self) -> SessionState:
        return self.orchestrator.state

    @property
    def plan_ids(self) -> tuple[str, ...]:
        return self.orchestrator.plan.all_ids if self.orchestrator.plan else ()

    @property
    def qualifier_question(self):
        return self.orchestrator.plan.qualifier if self.orchestrator.plan else None

    @property
    def active_player_id(self) -> str:
        return self.orchestrator.active_participant_id

    @property
    def questions_per_round(self) -> int:
        return self.orchestrator.questions_per_round

    def configure_questions_per_round(self, value: int) -> dict[str, int]:
        with self._lock:
            try:
                configured = self.orchestrator.configure_questions_per_round(value)
            except SessionError as error:
                raise _invalid_state(error) from error
            self._emit("settings_updated", questions_per_round=configured)
            return {"questions_per_round": configured}

    def _emit(self, name: str, **payload: Any) -> None:
        self.event_sequence += 1
        self.last_event = {"id": self.event_sequence, "name": name, **payload}

    def _participants(self) -> list[Any]:
        return [item for item in self.manager.participants.values() if not item.removed]

    def _participant_public(self, participant_id: str) -> dict[str, Any] | None:
        participant = self.manager.participants.get(participant_id)
        if participant is None or participant.removed:
            return None
        return participant.public_dict()

    def start_qualifier(self, *, duration_ms: int = QUALIFIER_DURATION_MS) -> dict[str, Any]:
        with self._lock:
            if self.state is not SessionState.LOBBY_OPEN:
                raise RoomError("invalid_state", "La sala no está disponible para iniciar.")
            if len(self._participants()) < 2:
                raise RoomError(
                    "not_enough_participants",
                    "Se necesitan al menos dos participantes para iniciar.",
                )
            try:
                self.manager.lock()
                self.orchestrator.lock_lobby()
                self.orchestrator.prepare_qualifier()
                self.orchestrator.open_qualifier()
            except (SessionError, RuntimeError, ValueError) as error:
                raise _invalid_state(error) from error
            planned = self.qualifier_question
            assert planned is not None
            opening = self.manager.open_remote(
                opening_type="qualifier",
                question_id=planned.question_id,
                duration_ms=duration_ms,
            )
            self.qualifier_results_data = None
            self.selection_pool.clear()
            self.preselected_ids.clear()
            self._emit("qualifier_started", opening_id=opening.opening_id)
            return self.qualifier_payload(include_correct=False) or {}

    def qualifier_payload(self, *, include_correct: bool) -> dict[str, Any] | None:
        planned = self.qualifier_question
        opening = self.manager.current_opening
        if planned is None or opening is None or opening.opening_type != "qualifier":
            return None
        payload: dict[str, Any] = {
            "question_id": planned.question_id,
            "prompt": planned.question.prompt,
            "answers": list(planned.question.answers),
            "opening": opening.public_dict(),
        }
        if include_correct:
            payload["correct_index"] = planned.question.correct_index
        return payload

    def close_qualifier(self, *, expected_opening_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            if self.state is SessionState.QUALIFIER_RESULTS:
                return self.qualifier_results_data or {}
            if self.state is not SessionState.QUALIFIER_OPEN:
                raise RoomError("invalid_state", "La clasificatoria no está abierta.")
            planned = self.qualifier_question
            opening = self.manager.current_opening
            if planned is None or opening is None:
                raise RoomError("no_opening", "La clasificatoria no está disponible.")
            if expected_opening_id and opening.opening_id != expected_opening_id:
                raise RoomError("stale_timer", "El temporizador ya no corresponde a esta fase.")
            result = self.manager.close_opening(correct_index=planned.question.correct_index)
            ordered = sorted(
                opening.responses.values(),
                key=lambda item: (item.elapsed_ms, item.sequence_no, item.participant_id),
            )
            correct_letter = LETTERS[planned.question.correct_index]
            response_rows: list[dict[str, Any]] = []
            correct_ranking: list[dict[str, Any]] = []
            for response in ordered:
                participant = self._participant_public(response.participant_id)
                if participant is None:
                    continue
                row = {
                    "participant_id": response.participant_id,
                    "alias": participant["alias"],
                    "avatar": participant["avatar"],
                    "avatar_symbol": participant["avatar_symbol"],
                    "alternative": response.answer,
                    "correct": response.answer == correct_letter,
                    "received_at": response.received_at,
                    "elapsed_ms": response.elapsed_ms,
                }
                response_rows.append(row)
                if row["correct"]:
                    correct_ranking.append({**row, "rank": len(correct_ranking) + 1})
            self.qualifier_results_data = {
                **result,
                "correct_index": planned.question.correct_index,
                "responses": response_rows,
                "ranking": correct_ranking,
            }
            try:
                self.orchestrator.qualifier_results()
            except SessionError as error:
                raise _invalid_state(error) from error
            self._build_selection_pool(correct_ranking)
            self._emit("qualifier_finished", correct_count=len(correct_ranking))
            return self.qualifier_results_data

    def _build_selection_pool(self, correct_ranking: list[dict[str, Any]]) -> None:
        ranked_ids = {item["participant_id"] for item in correct_ranking}
        self.selection_pool = [
            {**item, "selection_source": "qualifier"} for item in correct_ranking
        ]
        for participant in self._participants():
            if participant.participant_id in ranked_ids:
                continue
            public = participant.public_dict()
            self.selection_pool.append(
                {
                    "participant_id": participant.participant_id,
                    "alias": public["alias"],
                    "avatar": public["avatar"],
                    "avatar_symbol": public["avatar_symbol"],
                    "elapsed_ms": None,
                    "rank": None,
                    "selection_source": "available",
                }
            )
        self.preselected_ids = [item["participant_id"] for item in self.selection_pool[:2]]

    def begin_player_selection(self) -> dict[str, Any]:
        with self._lock:
            if self.state is SessionState.PLAYER_SELECTION:
                return self.selection_payload()
            try:
                self.orchestrator.begin_player_selection()
            except SessionError as error:
                raise _invalid_state(error) from error
            self._emit("player_selection_started")
            return self.selection_payload()

    def selection_payload(self) -> dict[str, Any]:
        return {
            "participants": list(self.selection_pool),
            "preselected_ids": list(self.preselected_ids),
        }

    def confirm_players(self, participant_ids: list[str]) -> dict[str, Any]:
        with self._lock:
            selected = list(dict.fromkeys(str(item) for item in participant_ids))
            available = {item.participant_id for item in self._participants()}
            if len(selected) != 2 or not set(selected).issubset(available):
                raise RoomError("invalid_selection", "Debes confirmar dos participantes válidos.")
            try:
                self.orchestrator.select_players(selected)
                self.manager.set_selected(selected)
            except (SessionError, RuntimeError, ValueError) as error:
                raise _invalid_state(error) from error
            self.preselected_ids = selected
            self._clear_question()
            self._emit("players_confirmed", participant_ids=selected)
            return self.round_payload()

    def round_payload(self) -> dict[str, Any]:
        return {
            "round_number": self.orchestrator.round_index + 1,
            "question_total": self.orchestrator.round_question_total,
            "active_player": self._participant_public(self.active_player_id),
            "scores": list(self.orchestrator.scores),
            "lifelines": self.lifeline_payload(),
        }

    def start_round(self, *, duration_ms: int = QUESTION_DURATION_MS) -> dict[str, Any]:
        with self._lock:
            if self.state is not SessionState.ROUND_INTRO:
                raise RoomError("invalid_state", "La ronda no está lista para comenzar.")
            return self._open_round_question(duration_ms=duration_ms)

    def _open_round_question(self, *, duration_ms: int = QUESTION_DURATION_MS) -> dict[str, Any]:
        try:
            planned = self.orchestrator.start_round_question()
        except SessionError as error:
            raise _invalid_state(error) from error
        seed = (self.orchestrator.plan.seed if self.orchestrator.plan else 0)
        seed += (self.orchestrator.round_index * 100) + self.orchestrator.question_index
        self.question_session = GameSession(planned.question, random.Random(seed))
        self.question_session.start()
        self.question_opening_id = f"open_question_{secrets.token_hex(6)}"
        self.question_opened_at = utc_now()
        self.question_started_perf = perf_counter()
        self.question_remaining_ms = max(1_000, int(duration_ms))
        self.question_elapsed_ms = 0
        self.question_response = None
        self.question_result = None
        self.active_lifeline = None
        self.lifeline_opening_id = ""
        self.lifeline_opened_at = ""
        self.audience_results = None
        self._emit(
            "question_started",
            opening_id=self.question_opening_id,
            round_number=self.orchestrator.round_index + 1,
            question_number=self.orchestrator.question_index + 1,
        )
        return self.regular_question_payload(include_correct=False) or {}

    def _question_opening(self) -> dict[str, Any] | None:
        if not self.question_opening_id or self.state not in {
            SessionState.QUESTION_ACTIVE,
            SessionState.LIFELINE_ACTIVE,
        }:
            return None
        hidden_indices = self.question_session.hidden_indices if self.question_session else set()
        return {
            "opening_id": self.question_opening_id,
            "type": "question",
            "duration_ms": self.question_remaining_ms,
            "opened_at": self.question_opened_at,
            "status": "open" if self.state is SessionState.QUESTION_ACTIVE else "paused",
            "allowed_answers": [
                letter for index, letter in enumerate(LETTERS) if index not in hidden_indices
            ],
            "display_mode": "keys_only",
        }

    def regular_question_payload(self, *, include_correct: bool) -> dict[str, Any] | None:
        if self.question_session is None or self.state not in {
            SessionState.QUESTION_ACTIVE,
            SessionState.LIFELINE_ACTIVE,
            SessionState.ANSWER_REVEALED,
        }:
            return None
        payload: dict[str, Any] = {
            "question_id": self.orchestrator.current_question.question_id,
            "question_number": self.orchestrator.question_index + 1,
            "question_total": self.orchestrator.round_question_total,
            "round_number": self.orchestrator.round_index + 1,
            "prompt": self.question_session.question.prompt,
            "answers": list(self.question_session.question.answers),
            "hidden_indices": sorted(self.question_session.hidden_indices),
            "opening": self._question_opening(),
            "response": self.question_response,
            "result": self.question_result,
        }
        if include_correct:
            payload["correct_index"] = self.question_session.question.correct_index
        return payload

    def _question_late(self) -> bool:
        return (
            self.question_started_perf <= 0
            or (perf_counter() - self.question_started_perf) * 1000 > self.question_remaining_ms
        )

    def submit_regular_answer(
        self, *, token: str, opening_id: str, answer: str
    ) -> tuple[dict[str, Any], bool]:
        participant = self.manager.authenticate(token)
        alternative = str(answer).strip().upper()
        with self._lock:
            if alternative not in set(LETTERS):
                return {"status": "invalid", "message": "La alternativa debe estar entre A y D."}, False
            if opening_id != self.question_opening_id or self.state is not SessionState.QUESTION_ACTIVE:
                return {"status": "late", "message": "La pregunta ya no está disponible."}, False
            if participant.participant_id != self.active_player_id:
                return {"status": "forbidden", "message": "Este turno pertenece al jugador activo."}, False
            if self.question_response is not None:
                return {"status": "duplicate", "message": "La primera respuesta ya quedó registrada."}, False
            if self._question_late():
                return {"status": "late", "message": "La respuesta llegó después del cierre."}, False
            assert self.question_session is not None
            selected_index = LETTERS.index(alternative)
            if selected_index in self.question_session.hidden_indices:
                return {"status": "forbidden", "message": "Esa alternativa fue eliminada por el 50:50."}, False
            elapsed_ms = self.question_elapsed_ms + max(
                0, int((perf_counter() - self.question_started_perf) * 1000)
            )
            try:
                correct = self.question_session.answer(selected_index)
                self.orchestrator.reveal_answer(correct=correct)
            except (SessionError, RuntimeError, ValueError) as error:
                raise _invalid_state(error) from error
            self.question_response = {
                "participant_id": participant.participant_id,
                "alternative": alternative,
                "received_at": utc_now(),
                "elapsed_ms": elapsed_ms,
                "correct": correct,
            }
            self.question_result = {
                "opening_id": self.question_opening_id,
                "selected_index": selected_index,
                "correct_index": self.question_session.question.correct_index,
                "correct": correct,
                "timed_out": False,
                "active_player": self._participant_public(participant.participant_id),
            }
            self._emit("answer_revealed", correct=correct, opening_id=self.question_opening_id)
            return {
                "status": "accepted",
                "message": "Respuesta recibida.",
                "opening_id": self.question_opening_id,
                "alternative": alternative,
                "received_at": self.question_response["received_at"],
                "elapsed_ms": elapsed_ms,
            }, True

    def timeout_question(self, *, expected_opening_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            if self.state is SessionState.ANSWER_REVEALED:
                return self.question_result or {}
            if self.state is not SessionState.QUESTION_ACTIVE:
                raise RoomError("invalid_state", "La pregunta no está activa.")
            if expected_opening_id and expected_opening_id != self.question_opening_id:
                raise RoomError("stale_timer", "El temporizador ya no corresponde a esta pregunta.")
            assert self.question_session is not None
            try:
                self.orchestrator.reveal_answer(correct=False)
            except SessionError as error:
                raise _invalid_state(error) from error
            self.question_result = {
                "opening_id": self.question_opening_id,
                "selected_index": -1,
                "correct_index": self.question_session.question.correct_index,
                "correct": False,
                "timed_out": True,
                "active_player": self._participant_public(self.active_player_id),
            }
            self._emit("answer_revealed", correct=False, timed_out=True, opening_id=self.question_opening_id)
            return self.question_result

    def advance_after_answer(self) -> dict[str, Any]:
        with self._lock:
            try:
                round_complete = self.orchestrator.advance_after_answer()
            except SessionError as error:
                raise _invalid_state(error) from error
            if round_complete:
                self._emit("round_finished", round_number=self.orchestrator.round_index + 1)
                return self.round_payload()
            return self._open_round_question()

    def advance_after_round(self) -> dict[str, Any]:
        with self._lock:
            try:
                session_complete = self.orchestrator.advance_after_round()
            except SessionError as error:
                raise _invalid_state(error) from error
            self._clear_question()
            self._emit("session_finished" if session_complete else "round_intro")
            return self.summary_payload() if session_complete else self.round_payload()

    def _pause_question(self) -> None:
        elapsed = max(0, int((perf_counter() - self.question_started_perf) * 1000))
        self.question_elapsed_ms += min(elapsed, self.question_remaining_ms)
        self.question_remaining_ms = max(1_000, self.question_remaining_ms - elapsed)
        self.question_started_perf = 0.0

    def _resume_question(self) -> None:
        self.question_opened_at = utc_now()
        self.question_started_perf = perf_counter()

    def use_fifty(self) -> dict[str, Any]:
        with self._lock:
            if self.question_session is None:
                raise RoomError("invalid_state", "No hay una pregunta activa.")
            try:
                use_number = self.orchestrator.use_lifeline("fifty")
                removed = self.question_session.use_fifty_fifty()
                self.orchestrator.finish_lifeline()
            except (SessionError, RuntimeError, ValueError) as error:
                raise _invalid_state(error) from error
            self._emit("lifeline_fifty", removed=list(removed), use_number=use_number)
            return {"removed": list(removed), "use_number": use_number}

    def start_timed_lifeline(self, name: str) -> dict[str, Any]:
        with self._lock:
            if name not in {"phone", "audience"}:
                raise RoomError("invalid_lifeline", "El comodín no existe.")
            if self.question_session is None:
                raise RoomError("invalid_state", "No hay una pregunta activa.")
            try:
                use_number = self.orchestrator.use_lifeline(name)
                self.question_session.use_timed_lifeline(name)
            except (SessionError, RuntimeError, ValueError) as error:
                raise _invalid_state(error) from error
            self._pause_question()
            self.active_lifeline = name
            self.lifeline_opened_at = utc_now()
            self.audience_results = None
            if name == "audience":
                eligible = [
                    item.participant_id
                    for item in self._participants()
                    if item.role == "audience"
                ]
                opening = self.manager.open_remote(
                    opening_type="audience",
                    question_id=self.orchestrator.current_question.question_id,
                    duration_ms=LIFELINE_DURATION_MS,
                    eligible_ids=eligible,
                )
                self.lifeline_opening_id = opening.opening_id
            else:
                self.lifeline_opening_id = f"open_phone_{secrets.token_hex(5)}"
            self._emit(
                "lifeline_started",
                lifeline=name,
                opening_id=self.lifeline_opening_id,
                use_number=use_number,
            )
            return self.lifeline_payload()

    def finish_timed_lifeline(self, *, expected_opening_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            if self.state is not SessionState.LIFELINE_ACTIVE or self.active_lifeline not in {"phone", "audience"}:
                raise RoomError("invalid_state", "No hay un comodín temporizado activo.")
            if expected_opening_id and expected_opening_id != self.lifeline_opening_id:
                raise RoomError("stale_timer", "El temporizador ya no corresponde a este comodín.")
            name = self.active_lifeline
            if name == "audience":
                self.audience_results = {
                    **self.manager.close_opening(),
                    "question_id": self.orchestrator.current_question.question_id,
                }
            try:
                self.orchestrator.finish_lifeline()
            except SessionError as error:
                raise _invalid_state(error) from error
            self.active_lifeline = None
            self._resume_question()
            self._emit("lifeline_finished", lifeline=name)
            return {
                "lifeline": name,
                "audience_results": self.audience_results,
                "question_remaining_ms": self.question_remaining_ms,
            }

    def lifeline_payload(self) -> dict[str, Any]:
        round_index = min(self.orchestrator.round_index, 1)
        used = self.orchestrator.lifeline_uses[round_index]
        payload: dict[str, Any] = {
            "active": self.active_lifeline,
            "used": dict(used),
            "remaining": {name: max(0, 3 - used[name]) for name in ("fifty", "phone", "audience")},
            "question_used": sorted(self.orchestrator.question_lifelines),
            "audience_results": self.audience_results,
        }
        if self.active_lifeline:
            payload["opening"] = {
                "opening_id": self.lifeline_opening_id,
                "type": self.active_lifeline,
                "duration_ms": LIFELINE_DURATION_MS,
                "opened_at": self.lifeline_opened_at,
                "status": "open",
                "allowed_answers": list(LETTERS),
                "display_mode": "keys_only",
            }
        return payload

    def summary_payload(self) -> dict[str, Any]:
        players: list[dict[str, Any]] = []
        for index, participant_id in enumerate(self.orchestrator.selected_participants):
            participant = self._participant_public(participant_id)
            if participant:
                players.append({**participant, "round_number": index + 1, "score": self.orchestrator.scores[index]})
        return {"players": players, "scores": list(self.orchestrator.scores)}

    def repeat(self) -> dict[str, Any]:
        with self._lock:
            if self.state is not SessionState.SESSION_SUMMARY:
                raise RoomError("invalid_state", "La experiencia aún no ha finalizado.")
            try:
                self.orchestrator.begin(self.project)
                self.orchestrator.room_code = self.room_code
                self.manager.reset_for_replay(session_id=self.orchestrator.session_id)
                self.orchestrator.lobby_opened()
            except (SessionError, RuntimeError, ValueError) as error:
                raise _invalid_state(error) from error
            self.game_id = self.orchestrator.session_id
            self.qualifier_results_data = None
            self.selection_pool.clear()
            self.preselected_ids.clear()
            self._clear_question()
            self._emit("session_restarted")
            return self.host_snapshot()

    def _clear_question(self) -> None:
        self.question_session = None
        self.question_opening_id = ""
        self.question_opened_at = ""
        self.question_started_perf = 0.0
        self.question_remaining_ms = QUESTION_DURATION_MS
        self.question_elapsed_ms = 0
        self.question_response = None
        self.question_result = None
        self.active_lifeline = None
        self.lifeline_opening_id = ""
        self.lifeline_opened_at = ""
        self.audience_results = None

    def close(self) -> None:
        with self._lock:
            self.manager.close()
            self._emit("game_finished")

    def _answers_received(self) -> int:
        opening = self.manager.current_opening
        if self.state in {SessionState.QUALIFIER_OPEN, SessionState.LIFELINE_ACTIVE} and opening:
            return len(opening.responses)
        return 1 if self.question_response else 0

    def host_snapshot(self) -> dict[str, Any]:
        with self._lock:
            snapshot = self.manager.host_snapshot()
            state = self.state
            return {
                "game_id": self.game_id,
                "room_code": self.room_code,
                "bank_name": "Preguntas del desafío",
                "created_at": self.created_at,
                "status": snapshot["status"],
                "state": state.value,
                "capacity": snapshot["capacity"],
                "connected": snapshot["connected"],
                "enrolled": snapshot["enrolled"],
                "participants": snapshot["participants"],
                "answers_received": self._answers_received(),
                "settings": {"questions_per_round": self.questions_per_round},
                "plan": {"question_count": len(self.plan_ids), "ids": list(self.plan_ids)},
                "qualifier": self.qualifier_payload(
                    include_correct=state in {SessionState.QUALIFIER_RESULTS, SessionState.PLAYER_SELECTION}
                ),
                "qualifier_results": self.qualifier_results_data,
                "selection": self.selection_payload(),
                "round": self.round_payload() if len(self.orchestrator.selected_participants) == 2 else None,
                "question": self.regular_question_payload(include_correct=state is SessionState.ANSWER_REVEALED),
                "lifelines": self.lifeline_payload(),
                "summary": self.summary_payload(),
                "last_event": dict(self.last_event),
            }

    def _mobile_opening(self, participant_id: str) -> tuple[dict[str, Any] | None, bool]:
        opening = self.manager.current_opening
        if self.state is SessionState.QUALIFIER_OPEN and opening and participant_id in opening.eligible_ids:
            return opening.public_dict(), participant_id in opening.responses
        if self.state is SessionState.QUESTION_ACTIVE and participant_id == self.active_player_id:
            return self._question_opening(), self.question_response is not None
        if (
            self.state is SessionState.LIFELINE_ACTIVE
            and self.active_lifeline == "audience"
            and opening
            and participant_id in opening.eligible_ids
        ):
            return opening.public_dict(), participant_id in opening.responses
        return None, False

    def _waiting_copy(self, participant_id: str, role: str) -> tuple[str, str]:
        state = self.state
        if self.manager.status is RoomStatus.CLOSED:
            return "Partida finalizada", "Gracias por participar."
        if state is SessionState.LOBBY_OPEN:
            return "Esperando inicio", "Tu lugar está registrado. La clasificatoria comenzará pronto."
        if state is SessionState.QUALIFIER_OPEN:
            opening = self.manager.current_opening
            if opening and participant_id in opening.responses:
                return "Respuesta registrada", "Espera el cierre de la clasificatoria."
            return "Clasificatoria en curso", "Elige una alternativa."
        if state in {SessionState.QUALIFIER_RESULTS, SessionState.PLAYER_SELECTION}:
            return "Resultados en pantalla", "El moderador confirmará a los dos jugadores."
        if state is SessionState.ROUND_INTRO:
            if participant_id == self.active_player_id:
                return (
                    "Tu ronda está por comenzar",
                    f"Prepárate para responder {self.questions_per_round} "
                    f"{'pregunta' if self.questions_per_round == 1 else 'preguntas'}.",
                )
            if role == "selected":
                return "Espera tu ronda", "Sigues en juego. Tu turno llegará después."
            return "Eres parte del público", "Permanece conectado para la consulta al público."
        if state is SessionState.QUESTION_ACTIVE:
            if role == "selected":
                return "Ronda en curso", "Espera tu turno o la siguiente pregunta."
            return "Eres parte del público", "Permanece conectado; podrías ser consultado."
        if state is SessionState.LIFELINE_ACTIVE:
            if self.active_lifeline == "audience" and role == "audience":
                return "Consulta al público", "Elige una alternativa."
            return "Comodín en curso", "La pregunta se reanudará en unos segundos."
        if state is SessionState.ANSWER_REVEALED:
            if participant_id == self.active_player_id and self.question_result:
                return (
                    "¡Respuesta correcta!" if self.question_result["correct"] else "Respuesta revelada",
                    "Prepárate para la siguiente pregunta.",
                )
            return "Respuesta revelada", "La experiencia continúa en la pantalla principal."
        if state is SessionState.ROUND_SUMMARY:
            return "Ronda finalizada", "Espera la siguiente etapa."
        if state is SessionState.SESSION_SUMMARY:
            return "Experiencia finalizada", "Mantente conectado si el moderador decide repetir el juego."
        return "Espera un momento", "La experiencia continuará en la pantalla principal."

    def player_snapshot(self, participant_id: str) -> dict[str, Any]:
        with self._lock:
            snapshot = self.manager.public_snapshot(participant_id)
            me = snapshot["me"] or {}
            role = str(me.get("role", "audience"))
            opening, answered = self._mobile_opening(participant_id)
            title, message = self._waiting_copy(participant_id, role)
            return {
                "room_code": self.room_code,
                "status": snapshot["status"],
                "state": self.state.value,
                "me": me,
                "game_role": "player" if role == "selected" else "audience",
                "is_active_player": participant_id == self.active_player_id,
                "question": {"opening": opening, "answered": answered} if opening else None,
                "waiting": {"title": title, "message": message},
                "last_event": dict(self.last_event),
            }


class RoomRegistry:
    def __init__(self, project_path: str | Path, *, max_participants: int = 30) -> None:
        self.project_path = Path(project_path)
        self.max_participants = max(2, int(max_participants))
        self._rooms_by_code: dict[str, OnlineRoom] = {}
        self._lock = threading.RLock()

    def banks(self) -> list[dict[str, Any]]:
        project = load_project(self.project_path)
        return [{"id": "main", "name": "Preguntas del desafío", "question_count": len(project.questions)}]

    def create(self, bank_id: str = "main", *, seed: int | None = None) -> OnlineRoom:
        if bank_id != "main":
            raise RoomError("bank_not_found", "El banco seleccionado no existe.")
        project = load_project(self.project_path)
        orchestrator = OnlineSessionOrchestrator()
        try:
            orchestrator.begin(project, seed=seed)
            orchestrator.lobby_opened()
        except SessionError as error:
            raise RoomError("invalid_bank", str(error)) from error
        with self._lock:
            room_code = self._new_room_code()
            orchestrator.room_code = room_code
            game_id = orchestrator.session_id
            room = OnlineRoom(
                game_id=game_id,
                room_code=room_code,
                project=project,
                manager=RoomManager(
                    session_id=game_id,
                    room_code=room_code,
                    max_participants=self.max_participants,
                ),
                orchestrator=orchestrator,
            )
            room._emit("lobby_opened")
            self._rooms_by_code[room_code] = room
            return room

    def get(self, room_code: str) -> OnlineRoom:
        with self._lock:
            room = self._rooms_by_code.get(str(room_code).strip())
        if room is None:
            raise RoomError("not_found", "La sala no existe o ya finalizó.")
        return room

    def active_count(self) -> int:
        with self._lock:
            return sum(room.manager.status is not RoomStatus.CLOSED for room in self._rooms_by_code.values())

    def _new_room_code(self) -> str:
        for _ in range(100):
            code = f"{secrets.randbelow(1_000_000):06d}"
            if code not in self._rooms_by_code:
                return code
        raise RuntimeError("No fue posible generar un código de sala único.")
