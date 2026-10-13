from __future__ import annotations

import random
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from .audio import AudioService
from .engine import GameSession, GameState
from .excel_import import ExcelImportError, import_project_from_excel
from .model import Question, ValidationError, default_project
from .rounds import RoundSelector
from .storage import (
    ProjectFileError,
    load_project_with_recovery,
    project_directory_is_writable,
    save_project,
)


class GameController(QObject):
    viewChanged = Signal()

    def __init__(self, project_root: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.project_root = project_root
        self.project_path = project_root / "projects" / "demo.juego"
        self.history_path = project_root / "projects" / "demo.history.json"
        self.template_path = project_root / "templates" / "Banco_preguntas_V2.xlsx"
        self.assets_dir = project_root / "assets"
        self.audio = AudioService(self.assets_dir / "audio", self)
        self._round_selector = RoundSelector(self.history_path)
        self._message = ""
        self._import_status = ""
        self._revision = 0
        self._countdown = 0
        self._active_timed_lifeline = ""
        self._score = 0
        self._game_finished = False
        self._game_used_lifelines: set[str] = set()
        self._round_number = 0
        self._round_repeated_count = 0

        recovered_from: Path | None = None
        try:
            self.project, recovered_from = load_project_with_recovery(self.project_path)
        except ProjectFileError:
            self.project = default_project()
            try:
                save_project(self.project_path, self.project, create_backup=False)
            except ProjectFileError:
                pass
        self._project_writable = project_directory_is_writable(self.project_path)

        self._game_questions = tuple(self.project.questions[:4])
        self.question_index = 0
        self.editor_index = 0
        self.session = self._new_session()

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._tick_countdown)
        self.session.start(reset_lifelines=False)
        self._message = (
            f"Proyecto recuperado desde {recovered_from.name}."
            if recovered_from is not None
            else "Selecciona una respuesta o utiliza un comodín."
        )

    def _new_session(self) -> GameSession:
        seed = hash(
            (
                self.project.title,
                self._round_number,
                self.question_index,
                self._game_questions[self.question_index].prompt,
            )
        ) & 0xFFFFFFFF
        return GameSession(
            self._game_questions[self.question_index],
            rng=random.Random(seed),
            used_lifelines=self._game_used_lifelines,
        )

    def _refresh(self) -> None:
        self._revision += 1
        self.viewChanged.emit()

    @Property(str, notify=viewChanged)
    def questionText(self) -> str:
        return self.session.question.prompt

    @Property("QVariantList", notify=viewChanged)
    def answers(self) -> list[str]:
        return list(self.session.question.answers)

    @Property(int, notify=viewChanged)
    def correctIndex(self) -> int:
        return self.session.question.correct_index

    @Property(int, notify=viewChanged)
    def selectedIndex(self) -> int:
        return self.session.selected_index

    @Property("QVariantList", notify=viewChanged)
    def hiddenIndices(self) -> list[int]:
        return sorted(self.session.hidden_indices)

    @Property("QVariantList", notify=viewChanged)
    def usedLifelines(self) -> list[str]:
        return sorted(self._game_used_lifelines)

    @Property(str, notify=viewChanged)
    def state(self) -> str:
        return str(self.session.state)

    @Property(str, notify=viewChanged)
    def message(self) -> str:
        return self._message

    @Property(int, notify=viewChanged)
    def revision(self) -> int:
        return self._revision

    @Property(int, notify=viewChanged)
    def countdown(self) -> int:
        return self._countdown

    @Property(bool, notify=viewChanged)
    def countdownActive(self) -> bool:
        return self.timer.isActive()

    @Property(int, notify=viewChanged)
    def questionNumber(self) -> int:
        return self.question_index + 1

    @Property(int, notify=viewChanged)
    def questionCount(self) -> int:
        return len(self.project.questions)

    @Property(int, notify=viewChanged)
    def bankQuestionCount(self) -> int:
        return len(self.project.questions)

    @Property(int, notify=viewChanged)
    def roundQuestionCount(self) -> int:
        return len(self._game_questions)

    @Property(int, notify=viewChanged)
    def roundNumber(self) -> int:
        return self._round_number

    @Property(int, notify=viewChanged)
    def score(self) -> int:
        return self._score

    @Property(bool, notify=viewChanged)
    def gameFinished(self) -> bool:
        return self._game_finished

    @Property(bool, notify=viewChanged)
    def canAdvance(self) -> bool:
        return self.session.state is GameState.ANSWERED

    @Property(bool, notify=viewChanged)
    def isLastQuestion(self) -> bool:
        return self.question_index == len(self._game_questions) - 1

    @Property("QVariantList", notify=viewChanged)
    def questionSummaries(self) -> list[str]:
        return [
            f"{index + 1}. {question.prompt}"
            for index, question in enumerate(self.project.questions)
        ]

    @Property(int, notify=viewChanged)
    def editorIndex(self) -> int:
        return self.editor_index

    @Property(str, notify=viewChanged)
    def editorQuestionText(self) -> str:
        return self.project.questions[self.editor_index].prompt

    @Property("QVariantList", notify=viewChanged)
    def editorAnswers(self) -> list[str]:
        return list(self.project.questions[self.editor_index].answers)

    @Property(int, notify=viewChanged)
    def editorCorrectIndex(self) -> int:
        return self.project.questions[self.editor_index].correct_index

    @Property(str, constant=True)
    def projectPath(self) -> str:
        return str(self.project_path)

    @Property(bool, constant=True)
    def projectWritable(self) -> bool:
        return self._project_writable

    @Property(str, notify=viewChanged)
    def importStatus(self) -> str:
        return self._import_status

    @Property(str, constant=True)
    def templatePath(self) -> str:
        return str(self.template_path)

    @Property(str, constant=True)
    def backgroundUrl(self) -> str:
        return QUrl.fromLocalFile(
            str(self.assets_dir / "images" / "game_background_v3_clean.png")
        ).toString()

    @Property(str, constant=True)
    def menuBackgroundUrl(self) -> str:
        return QUrl.fromLocalFile(
            str(self.assets_dir / "images" / "menu_background_v2.png")
        ).toString()

    @Property(str, constant=True)
    def phoneIconUrl(self) -> str:
        return QUrl.fromLocalFile(
            str(self.assets_dir / "images" / "phone.png")
        ).toString()

    @Property(str, constant=True)
    def audienceIconUrl(self) -> str:
        return QUrl.fromLocalFile(
            str(self.assets_dir / "images" / "audience.png")
        ).toString()

    @Slot()
    def startGame(self) -> None:
        self.timer.stop()
        self._countdown = 0
        self._active_timed_lifeline = ""
        self._game_used_lifelines.clear()
        self._score = 0
        self._game_finished = False
        selection = self._round_selector.select(self.project.questions, count=4)
        self._game_questions = selection.questions
        self._round_number = selection.round_number
        self._round_repeated_count = selection.repeated_count
        self.question_index = 0
        self.session = self._new_session()
        self.session.start(reset_lifelines=False)
        if self._round_repeated_count:
            self._message = (
                f"Ronda {self._round_number}: {self._round_repeated_count} pregunta(s) "
                "debieron reutilizarse."
            )
        else:
            self._message = (
                f"Ronda {self._round_number}: cuatro preguntas nuevas seleccionadas."
            )
        self.audio.start_question_music()
        self._refresh()

    @Slot()
    def startAudio(self) -> None:
        self.audio.start_intro_music()

    @Slot()
    def nextQuestion(self) -> None:
        if self.session.state is not GameState.ANSWERED:
            self._message = "Debes responder antes de continuar."
            self._refresh()
            return
        self.timer.stop()
        self._countdown = 0
        self._active_timed_lifeline = ""
        if self.isLastQuestion:
            self._game_finished = True
            self.audio.stop_music()
            self._message = (
                f"Ronda finalizada: {self._score} de {len(self._game_questions)} "
                "respuestas correctas."
            )
            self._refresh()
            return
        self.question_index += 1
        self.session = self._new_session()
        self.session.start(reset_lifelines=False)
        self._message = "Selecciona una respuesta o utiliza un comodín."
        self.audio.start_question_music()
        self._refresh()

    @Slot()
    def returnToMenu(self) -> None:
        self.timer.stop()
        self._countdown = 0
        self._active_timed_lifeline = ""
        self._game_finished = False
        self.audio.start_intro_music()
        self._refresh()

    @Slot(int)
    def selectAnswer(self, index: int) -> None:
        try:
            correct = self.session.answer(index)
        except (RuntimeError, ValueError) as exc:
            self._message = str(exc)
            self._refresh()
            return

        self.timer.stop()
        self._countdown = 0
        self.audio.stop_music()
        if correct:
            self._score += 1
            self._message = "¡Respuesta correcta!"
            self.audio.play_correct()
        else:
            letter = "ABCD"[self.session.question.correct_index]
            self._message = f"Respuesta incorrecta. La alternativa correcta es {letter}."
            self.audio.play_incorrect()
        self._refresh()

    @Slot()
    def useFiftyFifty(self) -> None:
        try:
            self.session.use_fifty_fifty()
            self._message = "50:50 eliminó dos respuestas incorrectas."
            self.audio.play_fifty()
        except RuntimeError as exc:
            self._message = str(exc)
        self._refresh()

    @Slot()
    def usePhone(self) -> None:
        if self.timer.isActive():
            self._message = "Espera a que termine el comodín en curso."
            self._refresh()
            return
        try:
            self.session.use_timed_lifeline("phone")
        except RuntimeError as exc:
            self._message = str(exc)
            self._refresh()
            return
        self._message = "Llamada en curso: tienes 15 segundos para escuchar."
        self.audio.play_phone()
        self._start_countdown("phone")

    @Slot()
    def useAudience(self) -> None:
        if self.timer.isActive():
            self._message = "Espera a que termine el comodín en curso."
            self._refresh()
            return
        try:
            self.session.use_timed_lifeline("audience")
        except RuntimeError as exc:
            self._message = str(exc)
            self._refresh()
            return
        percentages = self._audience_percentages()
        result = " · ".join(
            f"{letter}: {percentages[index]}%"
            for index, letter in enumerate("ABCD")
        )
        self._message = f"Resultado del público: {result}"
        self.audio.play_audience()
        self._start_countdown("audience")

    def _audience_percentages(self) -> list[int]:
        percentages = [12, 15, 18, 55]
        correct = self.session.question.correct_index
        percentages[correct], percentages[3] = percentages[3], percentages[correct]
        return percentages

    def _start_countdown(self, lifeline: str) -> None:
        self._active_timed_lifeline = lifeline
        self._countdown = 15
        self.timer.start()
        self._refresh()

    @Slot()
    def _tick_countdown(self) -> None:
        self._countdown -= 1
        if self._countdown <= 0:
            self.timer.stop()
            self._countdown = 0
            if self._active_timed_lifeline == "phone":
                self._message = "Finalizó el tiempo de la llamada."
            else:
                self._message = "Finalizó el tiempo del público."
            self._active_timed_lifeline = ""
        self._refresh()

    @Slot(str, str, str, str, str, int, result=bool)
    def saveQuestion(
        self,
        prompt: str,
        answer_a: str,
        answer_b: str,
        answer_c: str,
        answer_d: str,
        correct_index: int,
    ) -> bool:
        try:
            question = Question(
                prompt=prompt,
                answers=(answer_a, answer_b, answer_c, answer_d),
                correct_index=correct_index,
            ).normalized()
            updated = self.project.replace_question(self.editor_index, question)
            save_project(self.project_path, updated)
        except (ValidationError, ProjectFileError) as exc:
            self._message = str(exc)
            self._refresh()
            return False

        self.project = updated
        self._message = (
            f"Pregunta {self.editor_index + 1} guardada correctamente."
        )
        self._refresh()
        return True

    @Slot(int, result=bool)
    def selectEditorQuestion(self, index: int) -> bool:
        if not 0 <= index < len(self.project.questions):
            self._message = "La pregunta seleccionada no existe."
            self._refresh()
            return False
        self.editor_index = index
        self._refresh()
        return True

    @Slot(result=bool)
    def addQuestion(self) -> bool:
        insertion_index = self.editor_index + 1
        question = Question(
            prompt="Nueva pregunta",
            answers=("Alternativa A", "Alternativa B", "Alternativa C", "Alternativa D"),
            correct_index=0,
        )
        try:
            updated = self.project.add_question(question, insertion_index)
            save_project(self.project_path, updated)
        except (ValidationError, ProjectFileError, IndexError) as exc:
            self._message = str(exc)
            self._refresh()
            return False
        self.project = updated
        self.editor_index = insertion_index
        self._message = "Nueva pregunta agregada."
        self._refresh()
        return True

    @Slot(str, result=bool)
    def importQuestionsFromExcel(self, selected_file: str) -> bool:
        url = QUrl(selected_file)
        excel_path = Path(url.toLocalFile() if url.isLocalFile() else selected_file)
        try:
            imported = import_project_from_excel(excel_path)
            save_project(self.project_path, imported)
        except (ExcelImportError, ProjectFileError) as exc:
            self._import_status = str(exc)
            self._message = self._import_status
            self._refresh()
            return False

        self.project = imported
        self.editor_index = 0
        self._round_selector.reset()
        self._round_number = 0
        self._round_repeated_count = 0
        self._game_questions = tuple(imported.questions[:4])
        self.question_index = 0
        self.session = self._new_session()
        self.session.start(reset_lifelines=False)
        self._import_status = (
            f"Banco cargado correctamente: {len(imported.questions)} preguntas."
        )
        self._message = self._import_status
        self._refresh()
        return True

    @Slot()
    def openTemplateFolder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.template_path.parent)))

    @Slot(result=bool)
    def duplicateQuestion(self) -> bool:
        original = self.project.questions[self.editor_index]
        suffix = " (copia)"
        prompt = original.prompt
        if not prompt.endswith(suffix):
            prompt = f"{prompt[: 320 - len(suffix)]}{suffix}"
        copy = Question(prompt, original.answers, original.correct_index)
        insertion_index = self.editor_index + 1
        try:
            updated = self.project.add_question(copy, insertion_index)
            save_project(self.project_path, updated)
        except (ValidationError, ProjectFileError, IndexError) as exc:
            self._message = str(exc)
            self._refresh()
            return False
        self.project = updated
        self.editor_index = insertion_index
        self._message = "Pregunta duplicada."
        self._refresh()
        return True

    @Slot(result=bool)
    def deleteQuestion(self) -> bool:
        deleted_index = self.editor_index
        try:
            updated = self.project.delete_question(deleted_index)
            save_project(self.project_path, updated)
        except (ValidationError, ProjectFileError, IndexError) as exc:
            self._message = str(exc)
            self._refresh()
            return False
        self.project = updated
        self.editor_index = min(deleted_index, len(updated.questions) - 1)
        self._message = "Pregunta eliminada."
        self._refresh()
        return True

    @Slot(int, result=bool)
    def moveQuestion(self, offset: int) -> bool:
        destination = self.editor_index + offset
        try:
            updated = self.project.move_question(self.editor_index, destination)
            save_project(self.project_path, updated)
        except (ValidationError, ProjectFileError, IndexError) as exc:
            self._message = str(exc)
            self._refresh()
            return False
        self.project = updated
        self.editor_index = destination
        self._message = "Orden de preguntas actualizado."
        self._refresh()
        return True

    @Slot()
    def shutdown(self) -> None:
        self.timer.stop()
        self.audio.shutdown()
