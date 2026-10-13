from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QGuiApplication

from millonario.controller import GameController
from millonario.storage import load_project


class ControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QGuiApplication.instance() or QGuiApplication([])

    def test_editor_save_persists_and_reloads(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = GameController(root)
            saved = controller.saveQuestion(
                "¿Pregunta editada?",
                "Respuesta A",
                "Respuesta B",
                "Respuesta C",
                "Respuesta D",
                2,
            )
            self.assertTrue(saved)
            reloaded = load_project(root / "projects" / "demo.juego")
            self.assertEqual(reloaded.questions[0].prompt, "¿Pregunta editada?")
            self.assertEqual(reloaded.questions[0].correct_index, 2)
            controller.shutdown()

    def test_timed_lifeline_starts_at_fifteen_seconds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            controller = GameController(Path(directory))
            controller.usePhone()
            self.assertEqual(controller.countdown, 15)
            self.assertTrue(controller.countdownActive)
            self.assertIn("phone", controller.usedLifelines)
            controller.shutdown()

    def test_game_advances_and_keeps_game_lifelines(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            controller = GameController(Path(directory))
            controller.startGame()
            controller.useFiftyFifty()
            controller.selectAnswer(controller.correctIndex)
            self.assertEqual(controller.score, 1)
            controller.nextQuestion()
            self.assertEqual(controller.questionNumber, 2)
            self.assertIn("fifty", controller.usedLifelines)
            controller.shutdown()

    def test_editor_manages_question_bank(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            controller = GameController(Path(directory))
            initial_count = controller.questionCount
            self.assertTrue(controller.addQuestion())
            self.assertEqual(controller.questionCount, initial_count + 1)
            self.assertTrue(controller.duplicateQuestion())
            self.assertEqual(controller.questionCount, initial_count + 2)
            self.assertTrue(controller.moveQuestion(-1))
            self.assertTrue(controller.deleteQuestion())
            self.assertEqual(controller.questionCount, initial_count + 1)
            controller.shutdown()

    def test_game_finishes_after_last_question(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            controller = GameController(Path(directory))
            controller.startGame()
            for index in range(controller.roundQuestionCount):
                controller.selectAnswer(controller.correctIndex)
                controller.nextQuestion()
                if index < controller.roundQuestionCount - 1:
                    self.assertEqual(controller.questionNumber, index + 2)
            self.assertTrue(controller.gameFinished)
            self.assertEqual(controller.score, controller.roundQuestionCount)
            self.assertEqual(controller.roundQuestionCount, 4)
            controller.shutdown()

    def test_excel_import_replaces_bank_and_resets_rounds(self) -> None:
        template = (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "Banco_preguntas_V2.xlsx"
        )
        with tempfile.TemporaryDirectory() as directory:
            controller = GameController(Path(directory))
            controller.startGame()
            self.assertEqual(controller.roundNumber, 1)
            self.assertTrue(controller.importQuestionsFromExcel(str(template)))
            self.assertEqual(controller.bankQuestionCount, 12)
            self.assertIn("12 preguntas", controller.importStatus)
            controller.startGame()
            self.assertEqual(controller.roundNumber, 1)
            controller.shutdown()


if __name__ == "__main__":
    unittest.main()
