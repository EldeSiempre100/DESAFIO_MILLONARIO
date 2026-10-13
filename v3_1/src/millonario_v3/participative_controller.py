from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QTimer, QUrl, Signal, Slot

from .controller import GameController
from .engine import GameSession, GameState
from .event_store import EventStore
from .participation import ParticipationService, RoomError
from .session import SessionError, SessionOrchestrator, SessionState


class ParticipativeController(GameController):
    """Extiende el controlador V2 sin modificar su editor ni sus recursos."""

    participationChanged = Signal()

    def __init__(self, project_root: Path, parent=None) -> None:
        super().__init__(project_root, parent)
        self.orchestrator = SessionOrchestrator()
        self.participation = ParticipationService(
            static_dir=project_root / "mobile",
            runtime_dir=project_root / "data" / "runtime",
        )
        self._screen = "home"
        self._server_status = "Servidor detenido"
        self._network_warning = ""
        self._room_snapshot: dict[str, Any] = {}
        self._snapshot_signature: tuple[Any, ...] = ()
        self._qualifier_results: dict[str, Any] = {
            "counts": [0, 0, 0, 0],
            "percentages": [0, 0, 0, 0],
            "total": 0,
        }
        self._candidate_map: dict[str, dict[str, Any]] = {}
        self._selected_candidate_ids: set[str] = set()
        self._using_reserve = False
        self._reserve_used = False
        self._timer_mode = ""
        self._question_remaining = 45
        self._session_started_perf = 0.0
        self._global_elapsed = 0
        self._event_store: EventStore | None = None

        self.room_poll_timer = QTimer(self)
        self.room_poll_timer.setInterval(500)
        self.room_poll_timer.timeout.connect(self._poll_room)

    def _refresh(self) -> None:
        super()._refresh()
        self.participationChanged.emit()

    @Property(str, notify=participationChanged)
    def screen(self) -> str:
        return self._screen

    @Property(str, notify=participationChanged)
    def serverStatus(self) -> str:
        return self._server_status

    @Property(str, notify=participationChanged)
    def networkWarning(self) -> str:
        return self._network_warning

    @Property(str, notify=participationChanged)
    def roomCode(self) -> str:
        return self.orchestrator.room_code

    @Property(str, notify=participationChanged)
    def roomUrl(self) -> str:
        return self.participation.room_url

    @Property(str, notify=participationChanged)
    def qrUrl(self) -> str:
        path = self.participation.qr_path
        return QUrl.fromLocalFile(str(path)).toString() if path is not None else ""

    @Property(int, notify=participationChanged)
    def connectedCount(self) -> int:
        return int(self._room_snapshot.get("connected", 0))

    @Property(int, notify=participationChanged)
    def enrolledCount(self) -> int:
        return int(self._room_snapshot.get("enrolled", 0))

    @Property(int, notify=participationChanged)
    def remoteAnswerCount(self) -> int:
        return int(self._room_snapshot.get("answers_received", 0))

    @Property(int, notify=participationChanged)
    def remoteEligibleCount(self) -> int:
        return int(self._room_snapshot.get("opening_eligible", 0))

    @Property("QVariantList", notify=participationChanged)
    def participantItems(self) -> list[dict[str, object]]:
        return list(self._room_snapshot.get("participants", []))

    @Property("QVariantList", notify=participationChanged)
    def qualifierPercentages(self) -> list[int]:
        return list(self._qualifier_results.get("percentages", [0, 0, 0, 0]))

    @Property("QVariantList", notify=participationChanged)
    def qualifierCounts(self) -> list[int]:
        return list(self._qualifier_results.get("counts", [0, 0, 0, 0]))

    @Property(int, notify=participationChanged)
    def qualifierTotal(self) -> int:
        return int(self._qualifier_results.get("total", 0))

    @Property("QVariantList", notify=participationChanged)
    def candidateItems(self) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        for candidate in self._candidate_map.values():
            item = dict(candidate)
            item["selected"] = candidate["participant_id"] in self._selected_candidate_ids
            items.append(item)
        return items

    @Property(int, notify=participationChanged)
    def selectedCandidateCount(self) -> int:
        return len(self._selected_candidate_ids)

    @Property(bool, notify=participationChanged)
    def canUseReserve(self) -> bool:
        return False

    @Property(str, notify=participationChanged)
    def qualifierLabel(self) -> str:
        return "Pregunta de reserva" if self._using_reserve else "Pregunta clasificatoria"

    @Property(str, notify=participationChanged)
    def qualifierQuestionText(self) -> str:
        plan = self.orchestrator.plan
        if plan is None:
            return ""
        item = plan.reserve if self._using_reserve else plan.qualifier
        return item.question.prompt

    @Property("QVariantList", notify=participationChanged)
    def qualifierAnswers(self) -> list[str]:
        plan = self.orchestrator.plan
        if plan is None:
            return []
        item = plan.reserve if self._using_reserve else plan.qualifier
        return list(item.question.answers)

    @Property(int, notify=participationChanged)
    def qualifierCorrectIndex(self) -> int:
        plan = self.orchestrator.plan
        if plan is None:
            return -1
        item = plan.reserve if self._using_reserve else plan.qualifier
        return item.question.correct_index

    @Property(str, notify=participationChanged)
    def activeParticipantAlias(self) -> str:
        participant_id = self.orchestrator.active_participant_id
        participant = self._participant_by_id(participant_id)
        return str(participant.get("alias", "Participante"))

    @Property(str, notify=participationChanged)
    def activeParticipantAvatarSymbol(self) -> str:
        participant_id = self.orchestrator.active_participant_id
        participant = self._participant_by_id(participant_id)
        return str(participant.get("avatar_symbol", "●"))

    @Property(int, notify=participationChanged)
    def participativeRoundNumber(self) -> int:
        return self.orchestrator.round_index + 1

    @Property(int, notify=participationChanged)
    def firstPlayerScore(self) -> int:
        return self.orchestrator.scores[0]

    @Property(int, notify=participationChanged)
    def secondPlayerScore(self) -> int:
        return self.orchestrator.scores[1]

    @Property(str, notify=participationChanged)
    def firstPlayerAlias(self) -> str:
        ids = self.orchestrator.selected_participants
        return (
            str(self._participant_by_id(ids[0]).get("alias", "Participante 1"))
            if len(ids) == 2
            else "Participante 1"
        )

    @Property(str, notify=participationChanged)
    def firstPlayerAvatarSymbol(self) -> str:
        ids = self.orchestrator.selected_participants
        return (
            str(self._participant_by_id(ids[0]).get("avatar_symbol", "●"))
            if len(ids) == 2
            else "●"
        )

    @Property(str, notify=participationChanged)
    def secondPlayerAlias(self) -> str:
        ids = self.orchestrator.selected_participants
        return (
            str(self._participant_by_id(ids[1]).get("alias", "Participante 2"))
            if len(ids) == 2
            else "Participante 2"
        )

    @Property(str, notify=participationChanged)
    def secondPlayerAvatarSymbol(self) -> str:
        ids = self.orchestrator.selected_participants
        return (
            str(self._participant_by_id(ids[1]).get("avatar_symbol", "●"))
            if len(ids) == 2
            else "●"
        )

    @Property(int, notify=participationChanged)
    def fiftyRemaining(self) -> int:
        return self._lifeline_remaining("fifty")

    @Property(int, notify=participationChanged)
    def phoneRemaining(self) -> int:
        return self._lifeline_remaining("phone")

    @Property(int, notify=participationChanged)
    def audienceRemaining(self) -> int:
        return self._lifeline_remaining("audience")

    @Property(str, notify=participationChanged)
    def globalElapsedText(self) -> str:
        minutes, seconds = divmod(self._global_elapsed, 60)
        return f"{minutes:02d}:{seconds:02d}"

    def _participant_by_id(self, participant_id: str) -> dict[str, object]:
        for participant in self._room_snapshot.get("participants", []):
            if participant.get("participant_id") == participant_id:
                return participant
        manager = self.participation.manager
        if manager is not None:
            item = manager.participants.get(participant_id)
            if item is not None:
                return item.public_dict()
        return {}

    def _lifeline_remaining(self, name: str) -> int:
        if not 0 <= self.orchestrator.round_index < 2:
            return 3
        return 3 - self.orchestrator.lifeline_uses[
            self.orchestrator.round_index
        ][name]

    def _log(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        if self._event_store is None:
            return
        try:
            self._event_store.append(event_type, payload)
            self._event_store.snapshot(
                {
                    "state": self.orchestrator.state.value,
                    "room_code": self.orchestrator.room_code,
                    "round_index": self.orchestrator.round_index,
                    "question_index": self.orchestrator.question_index,
                    "selected_participants": list(
                        self.orchestrator.selected_participants
                    ),
                    "scores": list(self.orchestrator.scores),
                }
            )
        except OSError:
            self._message = "La sesión continúa, pero no fue posible guardar el registro."

    @Slot()
    def startParticipation(self) -> None:
        self.timer.stop()
        self.room_poll_timer.stop()
        self.participation.stop()
        self._screen = "preflight"
        self._server_status = "Validando banco y red local…"
        self._network_warning = ""
        self._candidate_map.clear()
        self._selected_candidate_ids.clear()
        self._using_reserve = False
        self._reserve_used = False
        self._round_number = 0
        self._qualifier_results = {
            "counts": [0, 0, 0, 0],
            "percentages": [0, 0, 0, 0],
            "total": 0,
        }
        self._refresh()
        try:
            self.orchestrator.reset()
            self.orchestrator.begin(self.project)
            network = self.participation.start(
                session_id=self.orchestrator.session_id,
                room_code=self.orchestrator.room_code,
                max_participants=30,
            )
            self.orchestrator.lobby_opened()
        except (SessionError, RuntimeError, OSError) as error:
            self.orchestrator.fail_safe()
            self._screen = "preflight_error"
            self._server_status = "No fue posible abrir la sala"
            self._message = str(error)
            self._refresh()
            return

        self._event_store = EventStore(
            self.project_root / "data" / "sessions",
            self.orchestrator.session_id,
        )
        self._server_status = "Servidor local activo"
        self._network_warning = network.warning or (
            "Si Windows solicita acceso, habilita únicamente Redes privadas."
        )
        self._screen = "lobby"
        self._message = "Escanea el QR desde los teléfonos conectados a la misma red."
        self._session_started_perf = time.monotonic()
        self._global_elapsed = 0
        self.room_poll_timer.start()
        self._poll_room()
        self._log(
            "room.open",
            {"room_code": self.orchestrator.room_code, "url": network.local_url},
        )
        self.audio.start_intro_music()
        self._refresh()

    @Slot()
    def lockRoomAndPrepareQualifier(self) -> None:
        manager = self.participation.manager
        if manager is None:
            self._message = "El servidor local no está disponible."
            self._refresh()
            return
        if self.enrolledCount < 2:
            self._message = "Se requieren al menos dos participantes enrolados."
            self._refresh()
            return
        try:
            manager.lock()
            self.orchestrator.lock_lobby()
            self.orchestrator.prepare_qualifier()
        except (RoomError, SessionError) as error:
            self._message = str(error)
            self._refresh()
            return
        self.participation.broadcast(
            "room.locked",
            {
                "room_code": self.roomCode,
                "message": "La clasificación comenzará ahora.",
            },
        )
        self._log("room.lock")
        self.openQualifier()

    @Slot()
    def openQualifier(self) -> None:
        manager = self.participation.manager
        plan = self.orchestrator.plan
        if manager is None or plan is None:
            return
        planned = plan.reserve if self._using_reserve else plan.qualifier
        eligible = [
            participant.participant_id
            for participant in manager.participants.values()
            if not participant.removed
            and participant.participant_id not in self._candidate_map
        ]
        try:
            self.orchestrator.open_qualifier()
            opening = manager.open_remote(
                opening_type="qualifier",
                question_id=planned.question_id,
                duration_ms=30_000,
                eligible_ids=eligible,
            )
        except (RoomError, SessionError) as error:
            self._message = str(error)
            self._refresh()
            return
        self._screen = "qualifier_open"
        self._timer_mode = "qualifier"
        self._countdown = 30
        self.timer.start()
        self._message = (
            "Votación abierta: las alternativas ya están activas en los teléfonos."
        )
        self.participation.broadcast(
            "qualifier.opened",
            opening.public_dict(),
            participant_ids=opening.eligible_ids,
        )
        self._log(
            "qualifier.open",
            {"question_id": planned.question_id, "reserve": self._using_reserve},
        )
        self._refresh()

    @Slot()
    def closeQualifier(self) -> None:
        if self.orchestrator.state is not SessionState.QUALIFIER_OPEN:
            return
        manager = self.participation.manager
        plan = self.orchestrator.plan
        if manager is None or plan is None:
            return
        planned = plan.reserve if self._using_reserve else plan.qualifier
        self.timer.stop()
        self._countdown = 0
        try:
            results = manager.close_opening(
                correct_index=planned.question.correct_index
            )
            self.orchestrator.qualifier_results()
        except (RoomError, SessionError) as error:
            self._message = str(error)
            self._refresh()
            return
        self._qualifier_results = results
        for candidate in results.get("candidates", []):
            participant_id = str(candidate["participant_id"])
            self._candidate_map.setdefault(participant_id, dict(candidate))
        if self._using_reserve:
            self._reserve_used = True
        self._screen = "qualifier_results"
        self._timer_mode = ""
        self._message = (
            f"Se recibieron {results['total']} respuestas. "
            f"Hay {len(self._candidate_map)} candidato(s) correcto(s)."
        )
        self.participation.broadcast("qualifier.closed", {"total": results["total"]})
        self._log(
            "qualifier.close",
            {
                "results": results,
                "reserve": self._using_reserve,
            },
        )
        self._refresh()

    @Slot()
    def startReserveQualifier(self) -> None:
        if not self.canUseReserve:
            return
        try:
            self.orchestrator.prepare_reserve_qualifier()
        except SessionError as error:
            self._message = str(error)
            self._refresh()
            return
        self._using_reserve = True
        self._screen = "qualifier_ready"
        self._message = (
            "La reserva será respondida solo por quienes aún no clasificaron."
        )
        self._refresh()

    @Slot()
    def showCandidateSelection(self) -> None:
        manager = self.participation.manager
        if manager is None:
            return
        if len(self._candidate_map) < 2 and not self._reserve_used:
            self._message = (
                "Se completarán los cupos con participantes disponibles."
            )
        if len(self._candidate_map) < 2:
            for participant in manager.participants.values():
                if participant.removed or participant.participant_id in self._candidate_map:
                    continue
                self._candidate_map[participant.participant_id] = {
                    "participant_id": participant.participant_id,
                    "alias": participant.alias,
                    "avatar": participant.public_dict()["avatar"],
                    "avatar_symbol": participant.public_dict()["avatar_symbol"],
                    "elapsed_ms": -1,
                    "alternative": "Cupo disponible",
                }
                if len(self._candidate_map) == 2:
                    break
        if len(self._candidate_map) < 2:
            self._message = "No existen dos participantes disponibles para continuar."
            self._refresh()
            return
        try:
            self.orchestrator.begin_player_selection()
        except SessionError as error:
            self._message = str(error)
            self._refresh()
            return
        self._screen = "player_selection"
        self._selected_candidate_ids = set(self._candidate_map)
        self._message = "Confirma los dos jugadores clasificados."
        self._refresh()

    @Slot(int)
    def toggleCandidate(self, index: int) -> None:
        candidates = list(self._candidate_map.values())
        if not 0 <= index < len(candidates):
            return
        participant_id = str(candidates[index]["participant_id"])
        if participant_id in self._selected_candidate_ids:
            self._selected_candidate_ids.remove(participant_id)
        elif len(self._selected_candidate_ids) < 2:
            self._selected_candidate_ids.add(participant_id)
        else:
            self._message = "Ya seleccionaste dos participantes."
        self._refresh()

    @Slot()
    def confirmCandidates(self) -> None:
        manager = self.participation.manager
        if manager is None:
            return
        try:
            selected = [
                participant_id
                for participant_id in self._candidate_map
                if participant_id in self._selected_candidate_ids
            ]
            self.orchestrator.select_players(selected)
            manager.set_selected(selected)
        except (SessionError, RoomError) as error:
            self._message = str(error)
            self._refresh()
            return
        self._screen = "round_intro"
        self._game_finished = False
        self._message = "Participantes confirmados. Comienza la primera ronda."
        self.participation.broadcast(
            "candidates.selected",
            {"participant_ids": selected},
        )
        self._log("candidates.select", {"participant_ids": selected})
        self._refresh()

    @Slot()
    def startParticipativeRound(self) -> None:
        try:
            self.orchestrator.start_round_question()
        except SessionError as error:
            self._message = str(error)
            self._refresh()
            return
        questions = self.orchestrator.current_questions
        self._game_questions = tuple(item.question for item in questions)
        self.question_index = self.orchestrator.question_index
        self._round_number = self.orchestrator.round_index + 1
        self._score = self.orchestrator.scores[self.orchestrator.round_index]
        self._open_current_round_question()
        participant_id = self.orchestrator.active_participant_id
        alias = self.activeParticipantAlias
        self.participation.broadcast(
            "round.started",
            {
                "round": self.orchestrator.round_index + 1,
                "participant_id": participant_id,
                "alias": alias,
            },
        )
        self._log(
            "round.start",
            {"round": self.orchestrator.round_index + 1, "participant_id": participant_id},
        )

    def _open_current_round_question(self) -> None:
        self._game_used_lifelines.clear()
        planned = self.orchestrator.current_question
        seed = hash(
            (
                self.orchestrator.session_id,
                self.orchestrator.round_index,
                self.orchestrator.question_index,
                planned.question_id,
            )
        )
        self.session = GameSession(
            planned.question,
            rng=random.Random(seed),
            used_lifelines=self._game_used_lifelines,
        )
        self.session.start(reset_lifelines=False)
        self.question_index = self.orchestrator.question_index
        self._screen = "round_question"
        self._question_remaining = 45
        self._countdown = 45
        self._timer_mode = "question"
        self.timer.start()
        self._message = (
            f"{self.activeParticipantAlias}: responde antes de que termine el tiempo."
        )
        self.audio.start_question_music()
        self._refresh()

    @Slot(int)
    def selectParticipativeAnswer(self, index: int) -> None:
        if self.orchestrator.state is not SessionState.QUESTION_ACTIVE:
            self._message = "Finaliza el comodín antes de bloquear la respuesta."
            self._refresh()
            return
        try:
            correct = self.session.answer(index)
            self.orchestrator.reveal_answer(correct=correct)
        except (RuntimeError, ValueError, SessionError) as error:
            self._message = str(error)
            self._refresh()
            return
        self.timer.stop()
        self._timer_mode = ""
        self._countdown = 0
        self._score = self.orchestrator.scores[self.orchestrator.round_index]
        self.audio.stop_music()
        if correct:
            self._message = "¡Respuesta correcta!"
            self.audio.play_correct()
        else:
            letter = "ABCD"[self.session.question.correct_index]
            self._message = f"Respuesta incorrecta. La alternativa correcta es {letter}."
            self.audio.play_incorrect()
        self._log(
            "answer.reveal",
            {
                "round": self.orchestrator.round_index + 1,
                "question_id": self.orchestrator.current_question.question_id,
                "selected_index": index,
                "correct": correct,
            },
        )
        self._refresh()

    @Slot()
    def nextParticipativeQuestion(self) -> None:
        if self.session.state is not GameState.ANSWERED:
            self._message = "Debes bloquear una respuesta antes de continuar."
            self._refresh()
            return
        try:
            round_complete = self.orchestrator.advance_after_answer()
        except SessionError as error:
            self._message = str(error)
            self._refresh()
            return
        if round_complete:
            self.timer.stop()
            self._screen = "round_summary"
            self._message = (
                f"Ronda terminada: {self._score} de 5 respuestas correctas."
            )
            self.participation.broadcast(
                "client.waiting",
                {
                    "title": "Ronda finalizada",
                    "message": "Espera la siguiente etapa en la pantalla principal.",
                },
            )
            self._log(
                "round.finish",
                {
                    "round": self.orchestrator.round_index + 1,
                    "score": self._score,
                },
            )
            self._refresh()
            return
        try:
            self.orchestrator.start_round_question()
        except SessionError as error:
            self._message = str(error)
            self._refresh()
            return
        self._open_current_round_question()

    @Slot()
    def advanceAfterRound(self) -> None:
        try:
            finished = self.orchestrator.advance_after_round()
        except SessionError as error:
            self._message = str(error)
            self._refresh()
            return
        if finished:
            self.timer.stop()
            self._screen = "session_summary"
            self.audio.stop_music()
            self.participation.broadcast(
                "session.finished",
                {
                    "players": [
                        {"alias": self.firstPlayerAlias, "score": self.firstPlayerScore},
                        {"alias": self.secondPlayerAlias, "score": self.secondPlayerScore},
                    ]
                },
            )
            self._log(
                "session.finish",
                {"scores": list(self.orchestrator.scores)},
            )
        else:
            self._screen = "round_intro"
            self._score = 0
            self._message = "La segunda persona está lista para comenzar."
        self._refresh()

    @Slot()
    def repeatParticipativeGame(self) -> None:
        manager = self.participation.manager
        if manager is None or self.orchestrator.state is not SessionState.SESSION_SUMMARY:
            return
        try:
            self.orchestrator.begin(self.project)
            self.orchestrator.room_code = manager.room_code
            manager.reset_for_replay(session_id=self.orchestrator.session_id)
            self.orchestrator.lobby_opened()
        except (SessionError, RoomError) as error:
            self._message = str(error)
            self._refresh()
            return
        self.timer.stop()
        self._candidate_map.clear()
        self._selected_candidate_ids.clear()
        self._using_reserve = False
        self._reserve_used = False
        self._qualifier_results = {
            "counts": [0, 0, 0, 0],
            "percentages": [0, 0, 0, 0],
            "total": 0,
        }
        self._round_number = 0
        self._score = 0
        self._game_finished = False
        self._screen = "lobby"
        self._message = (
            "Nueva partida preparada. Todos vuelven a participar en la clasificación."
        )
        self._session_started_perf = time.monotonic()
        self._global_elapsed = 0
        self._event_store = EventStore(
            self.project_root / "data" / "sessions",
            self.orchestrator.session_id,
        )
        self.participation.broadcast(
            "session.restarted",
            {
                "room_code": self.roomCode,
                "message": "Nueva partida preparada.",
            },
        )
        self.participation.broadcast_snapshot()
        self._poll_room()
        self._log("session.restart")
        self._refresh()

    @Slot()
    def useParticipativeFifty(self) -> None:
        try:
            self.orchestrator.use_lifeline("fifty")
            self.session.use_fifty_fifty()
            self.orchestrator.finish_lifeline()
        except (SessionError, RuntimeError) as error:
            self._message = str(error)
            self._refresh()
            return
        self._message = "50:50 eliminó dos respuestas incorrectas."
        self.audio.play_fifty()
        self._log("lifeline.fifty", {"round": self.roundNumber})
        self._refresh()

    @Slot()
    def useParticipativePhone(self) -> None:
        if self._timer_mode != "question":
            self._message = "Espera a que finalice la acción en curso."
            self._refresh()
            return
        try:
            self.orchestrator.use_lifeline("phone")
            self.session.use_timed_lifeline("phone")
        except (SessionError, RuntimeError) as error:
            self._message = str(error)
            self._refresh()
            return
        self._pause_question_for("phone")
        self._message = "Llamada en curso: 15 segundos."
        self.audio.play_phone()
        self._log("lifeline.phone", {"round": self.roundNumber})

    @Slot()
    def useParticipativeAudience(self) -> None:
        if self._timer_mode != "question":
            self._message = "Espera a que finalice la acción en curso."
            self._refresh()
            return
        manager = self.participation.manager
        if manager is None:
            self._message = "El público remoto no está disponible."
            self._refresh()
            return
        try:
            self.orchestrator.use_lifeline("audience")
            self.session.use_timed_lifeline("audience")
            eligible = [
                participant.participant_id
                for participant in manager.participants.values()
                if not participant.removed and participant.role == "audience"
            ]
            opening = manager.open_remote(
                opening_type="audience",
                question_id=self.orchestrator.current_question.question_id,
                duration_ms=15_000,
                eligible_ids=eligible,
            )
        except (SessionError, RuntimeError, RoomError) as error:
            self._message = str(error)
            self._refresh()
            return
        self._pause_question_for("audience")
        self._message = f"Consulta abierta para {len(opening.eligible_ids)} teléfono(s)."
        self.audio.play_audience()
        self.participation.broadcast(
            "audience.opened",
            opening.public_dict(),
            participant_ids=opening.eligible_ids,
        )
        self._log(
            "lifeline.audience.open",
            {"round": self.roundNumber, "eligible": len(opening.eligible_ids)},
        )

    def _pause_question_for(self, mode: str) -> None:
        self._question_remaining = max(0, self._countdown)
        self._timer_mode = mode
        self._countdown = 15
        self.timer.start()
        self._refresh()

    def _tick_countdown(self) -> None:
        self._countdown = max(0, self._countdown - 1)
        if self._countdown > 0:
            self._refresh()
            return
        self.timer.stop()
        mode = self._timer_mode
        if mode == "qualifier":
            self.closeQualifier()
            return
        if mode == "audience":
            self._finish_audience()
            return
        if mode == "phone":
            try:
                self.orchestrator.finish_lifeline()
            except SessionError:
                pass
            self._message = "Finalizó el tiempo de la llamada."
            self._resume_question_timer()
            return
        if mode == "question":
            self._timer_mode = ""
            self._message = "Tiempo agotado. El anfitrión debe bloquear una respuesta."
            self._refresh()

    def _finish_audience(self) -> None:
        manager = self.participation.manager
        if manager is None:
            return
        try:
            results = manager.close_opening()
            self.orchestrator.finish_lifeline()
        except (RoomError, SessionError) as error:
            self._message = str(error)
            self._refresh()
            return
        result_text = " · ".join(
            f"{letter}: {results['percentages'][index]}%"
            for index, letter in enumerate("ABCD")
        )
        self._message = f"Resultado del público: {result_text}"
        self.participation.broadcast(
            "audience.closed",
            {"total": results["total"]},
        )
        self.participation.broadcast(
            "audience.results",
            {
                "counts": results["counts"],
                "percentages": results["percentages"],
                "total": results["total"],
            },
        )
        self._log("lifeline.audience.close", {"results": results})
        self._resume_question_timer()

    def _resume_question_timer(self) -> None:
        self._timer_mode = "question"
        self._countdown = self._question_remaining
        if self._countdown > 0:
            self.timer.start()
        self._refresh()

    @Slot(str)
    def removeParticipant(self, participant_id: str) -> None:
        manager = self.participation.manager
        if manager is None or self.orchestrator.state is not SessionState.LOBBY_OPEN:
            return
        try:
            manager.remove(participant_id)
        except RoomError as error:
            self._message = str(error)
        self.participation.broadcast_snapshot()
        self._poll_room()

    @Slot()
    def returnV3ToMenu(self) -> None:
        self.timer.stop()
        self.room_poll_timer.stop()
        if self.participation.running:
            self.participation.broadcast(
                "session.finished",
                {"reason": "host_closed"},
            )
        self.participation.stop()
        self.orchestrator.reset()
        self._screen = "home"
        self._countdown = 0
        self._timer_mode = ""
        self._game_finished = False
        self._server_status = "Servidor detenido"
        self.audio.start_intro_music()
        self._refresh()

    def _poll_room(self) -> None:
        manager = self.participation.manager
        if manager is None:
            return
        snapshot = manager.host_snapshot()
        participants = tuple(
            (
                item["participant_id"],
                item["alias"],
                item["role"],
                item["connected"],
            )
            for item in snapshot.get("participants", [])
        )
        elapsed = (
            int(time.monotonic() - self._session_started_perf)
            if self._session_started_perf
            else 0
        )
        signature = (
            snapshot.get("enrolled"),
            snapshot.get("connected"),
            snapshot.get("answers_received"),
            snapshot.get("opening_eligible"),
            participants,
            elapsed,
        )
        self._room_snapshot = snapshot
        self._global_elapsed = elapsed
        if signature != self._snapshot_signature:
            self._snapshot_signature = signature
            self._refresh()

    def shutdown(self) -> None:
        self.room_poll_timer.stop()
        self.participation.stop()
        super().shutdown()
