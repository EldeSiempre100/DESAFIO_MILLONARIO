from __future__ import annotations

import random
import unittest

from millonario.engine import GameSession, GameState
from millonario.model import default_project


class GameSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        question = default_project().questions[0]
        self.session = GameSession(question, rng=random.Random(7))
        self.session.start()

    def test_correct_answer_locks_question(self) -> None:
        self.assertTrue(self.session.answer(0))
        self.assertEqual(self.session.state, GameState.ANSWERED)
        with self.assertRaises(RuntimeError):
            self.session.answer(1)

    def test_fifty_fifty_keeps_correct_answer(self) -> None:
        removed = self.session.use_fifty_fifty()
        self.assertEqual(len(removed), 2)
        self.assertNotIn(self.session.question.correct_index, removed)
        with self.assertRaises(RuntimeError):
            self.session.use_fifty_fifty()

    def test_hidden_answer_cannot_be_selected(self) -> None:
        removed = self.session.use_fifty_fifty()
        with self.assertRaises(ValueError):
            self.session.answer(removed[0])


if __name__ == "__main__":
    unittest.main()
