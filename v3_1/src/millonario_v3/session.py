from __future__ import annotations

import random
import secrets
from dataclasses import dataclass, field
from enum import StrEnum

from .model import Project, Question
from .rounds import question_fingerprint


class SessionError(RuntimeError):
    """La operación no es válida para el estado actual de la experiencia."""


class SessionState(StrEnum):
    HOME = "home"
    PREFLIGHT = "preflight"
    LOBBY_OPEN = "lobby_open"
    LOBBY_LOCKED = "lobby_locked"
    QUALIFIER_READY = "qualifier_ready"
    QUALIFIER_OPEN = "qualifier_open"
    QUALIFIER_RESULTS = "qualifier_results"
    PLAYER_SELECTION = "player_selection"
    ROUND_INTRO = "round_intro"
    QUESTION_ACTIVE = "question_active"
    LIFELINE_ACTIVE = "lifeline_active"
    ANSWER_REVEALED = "answer_revealed"
    ROUND_SUMMARY = "round_summary"
    SESSION_SUMMARY = "session_summary"
    ERROR_SAFE = "error_safe"


@dataclass(frozen=True, slots=True)
class PlannedQuestion:
    question_id: str
    question: Question


@dataclass(frozen=True, slots=True)
class QuestionPlan:
    qualifier: PlannedQuestion
    round_one: tuple[PlannedQuestion, ...]
    round_two: tuple[PlannedQuestion, ...]
    reserve: PlannedQuestion
    seed: int

    @classmethod
    def create(
        cls,
        project: Project,
        *,
        seed: int | None = None,
    ) -> "QuestionPlan":
        project.validate()
        if len(project.questions) != 12:
            raise SessionError(
                "La experiencia participativa requiere exactamente 12 preguntas "
                "activas: 1 clasificatoria, 5+5 de ronda y 1 de reserva."
            )
        plan_seed = secrets.randbits(63) if seed is None else int(seed)
        rng = random.Random(plan_seed)
        questions = list(project.questions)
        rng.shuffle(questions)
        planned = [
            PlannedQuestion(question_fingerprint(question), question)
            for question in questions
        ]
        return cls(
            qualifier=planned[0],
            round_one=tuple(planned[1:6]),
            round_two=tuple(planned[6:11]),
            reserve=planned[11],
            seed=plan_seed,
        )

    @property
    def all_ids(self) -> tuple[str, ...]:
        return (
            self.qualifier.question_id,
            *(item.question_id for item in self.round_one),
            *(item.question_id for item in self.round_two),
            self.reserve.question_id,
        )


@dataclass(slots=True)
class SessionOrchestrator:
    state: SessionState = SessionState.HOME
    session_id: str = ""
    room_code: str = ""
    plan: QuestionPlan | None = None
    selected_participants: tuple[str, str] | tuple[()] = ()
    round_index: int = 0
    question_index: int = 0
    scores: list[int] = field(default_factory=lambda: [0, 0])
    lifeline_uses: list[dict[str, int]] = field(
        default_factory=lambda: [
            {"fifty": 0, "phone": 0, "audience": 0},
            {"fifty": 0, "phone": 0, "audience": 0},
        ]
    )
    question_lifelines: set[str] = field(default_factory=set)

    def begin(self, project: Project, *, seed: int | None = None) -> QuestionPlan:
        if self.state not in {
            SessionState.HOME,
            SessionState.SESSION_SUMMARY,
            SessionState.ERROR_SAFE,
        }:
            raise SessionError("Ya existe una experiencia en curso.")
        self.state = SessionState.PREFLIGHT
        self.plan = QuestionPlan.create(project, seed=seed)
        self.session_id = f"ses_{secrets.token_hex(8)}"
        self.room_code = f"{secrets.randbelow(10_000):04d}"
        self.selected_participants = ()
        self.round_index = 0
        self.question_index = 0
        self.scores = [0, 0]
        self.lifeline_uses = [
            {"fifty": 0, "phone": 0, "audience": 0},
            {"fifty": 0, "phone": 0, "audience": 0},
        ]
        self.question_lifelines.clear()
        return self.plan

    def lobby_opened(self) -> None:
        self._require(SessionState.PREFLIGHT)
        self.state = SessionState.LOBBY_OPEN

    def lock_lobby(self) -> None:
        self._require(SessionState.LOBBY_OPEN)
        self.state = SessionState.LOBBY_LOCKED

    def prepare_qualifier(self) -> None:
        self._require(SessionState.LOBBY_LOCKED)
        self.state = SessionState.QUALIFIER_READY

    def open_qualifier(self) -> None:
        self._require(SessionState.QUALIFIER_READY)
        self.state = SessionState.QUALIFIER_OPEN

    def qualifier_results(self) -> None:
        self._require(SessionState.QUALIFIER_OPEN)
        self.state = SessionState.QUALIFIER_RESULTS

    def prepare_reserve_qualifier(self) -> None:
        if self.state not in {
            SessionState.QUALIFIER_RESULTS,
            SessionState.PLAYER_SELECTION,
        }:
            raise SessionError("La pregunta de reserva no está disponible.")
        self.state = SessionState.QUALIFIER_READY

    def begin_player_selection(self) -> None:
        self._require(SessionState.QUALIFIER_RESULTS)
        self.state = SessionState.PLAYER_SELECTION

    def select_players(self, participant_ids: list[str] | tuple[str, ...]) -> None:
        self._require(SessionState.PLAYER_SELECTION)
        unique = tuple(dict.fromkeys(str(item) for item in participant_ids))
        if len(unique) != 2:
            raise SessionError("Debes seleccionar exactamente dos participantes.")
        self.selected_participants = (unique[0], unique[1])
        self.round_index = 0
        self.question_index = 0
        self.state = SessionState.ROUND_INTRO

    @property
    def current_questions(self) -> tuple[PlannedQuestion, ...]:
        if self.plan is None:
            return ()
        return self.plan.round_one if self.round_index == 0 else self.plan.round_two

    @property
    def current_question(self) -> PlannedQuestion:
        questions = self.current_questions
        if not questions:
            raise SessionError("La sesión no tiene un plan de preguntas.")
        return questions[self.question_index]

    @property
    def active_participant_id(self) -> str:
        if len(self.selected_participants) != 2:
            return ""
        return self.selected_participants[self.round_index]

    def start_round_question(self) -> PlannedQuestion:
        if self.state not in {SessionState.ROUND_INTRO, SessionState.ANSWER_REVEALED}:
            raise SessionError("La ronda no está preparada para abrir una pregunta.")
        self.question_lifelines.clear()
        self.state = SessionState.QUESTION_ACTIVE
        return self.current_question

    def use_lifeline(self, name: str) -> int:
        self._require(SessionState.QUESTION_ACTIVE)
        if name not in {"fifty", "phone", "audience"}:
            raise SessionError("Comodín desconocido.")
        if name in self.question_lifelines:
            raise SessionError("Este comodín ya se utilizó en la pregunta actual.")
        count = self.lifeline_uses[self.round_index][name]
        if count >= 3:
            raise SessionError("Se alcanzó el máximo de tres usos en esta ronda.")
        self.lifeline_uses[self.round_index][name] = count + 1
        self.question_lifelines.add(name)
        self.state = SessionState.LIFELINE_ACTIVE
        return count + 1

    def finish_lifeline(self) -> None:
        self._require(SessionState.LIFELINE_ACTIVE)
        self.state = SessionState.QUESTION_ACTIVE

    def reveal_answer(self, *, correct: bool) -> None:
        if self.state not in {
            SessionState.QUESTION_ACTIVE,
            SessionState.LIFELINE_ACTIVE,
        }:
            raise SessionError("No existe una pregunta activa para revelar.")
        if correct:
            self.scores[self.round_index] += 1
        self.state = SessionState.ANSWER_REVEALED

    def advance_after_answer(self) -> bool:
        self._require(SessionState.ANSWER_REVEALED)
        if self.question_index < 4:
            self.question_index += 1
            return False
        self.state = SessionState.ROUND_SUMMARY
        return True

    def advance_after_round(self) -> bool:
        self._require(SessionState.ROUND_SUMMARY)
        if self.round_index == 0:
            self.round_index = 1
            self.question_index = 0
            self.state = SessionState.ROUND_INTRO
            return False
        self.state = SessionState.SESSION_SUMMARY
        return True

    def fail_safe(self) -> None:
        self.state = SessionState.ERROR_SAFE

    def reset(self) -> None:
        self.state = SessionState.HOME
        self.plan = None
        self.session_id = ""
        self.room_code = ""

    def _require(self, expected: SessionState) -> None:
        if self.state is not expected:
            raise SessionError(
                f"Estado inválido: se esperaba {expected.value} y se recibió "
                f"{self.state.value}."
            )
