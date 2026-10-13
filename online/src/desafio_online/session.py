from __future__ import annotations

from dataclasses import dataclass

from millonario_v3.session import (
    PlannedQuestion,
    SessionError,
    SessionOrchestrator,
    SessionState,
)


ALLOWED_QUESTIONS_PER_ROUND = (1, 3, 5)


@dataclass(slots=True)
class OnlineSessionOrchestrator(SessionOrchestrator):
    """Adaptador web del orquestador V3 sin modificar el canon V3.1.4.

    El plan canónico sigue naciendo desde las 12 preguntas de V3
    (clasificatoria + 5 + 5 + reserva). V4 puede consumir sólo las primeras
    1, 3 o 5 preguntas de cada bloque de ronda, según la selección previa del
    moderador.
    """

    questions_per_round: int = 5

    def configure_questions_per_round(self, value: int) -> int:
        requested = int(value)
        if requested not in ALLOWED_QUESTIONS_PER_ROUND:
            raise SessionError("Las preguntas por jugador deben ser 1, 3 o 5.")
        if self.state not in {
            SessionState.HOME,
            SessionState.PREFLIGHT,
            SessionState.LOBBY_OPEN,
        }:
            raise SessionError(
                "La cantidad de preguntas sólo puede cambiarse antes de iniciar la clasificatoria."
            )
        self.questions_per_round = requested
        return requested

    @property
    def current_questions(self) -> tuple[PlannedQuestion, ...]:
        if self.plan is None:
            return ()
        source = self.plan.round_one if self.round_index == 0 else self.plan.round_two
        return source[: self.questions_per_round]

    @property
    def round_question_total(self) -> int:
        return len(self.current_questions)

    def advance_after_answer(self) -> bool:
        self._require(SessionState.ANSWER_REVEALED)
        if self.question_index + 1 < self.round_question_total:
            self.question_index += 1
            return False
        self.state = SessionState.ROUND_SUMMARY
        return True
