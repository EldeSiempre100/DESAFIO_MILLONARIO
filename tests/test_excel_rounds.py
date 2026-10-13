from __future__ import annotations

import random
import tempfile
from pathlib import Path

import pytest

from millonario.excel_import import ExcelImportError, import_project_from_excel
from millonario.model import Project, Question, ValidationError
from millonario.rounds import RoundSelector, question_fingerprint


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = PROJECT_ROOT / "templates" / "Banco_preguntas_V2.xlsx"


def _questions(count: int = 12) -> tuple[Question, ...]:
    return tuple(
        Question(
            prompt=f"¿Pregunta de prueba {index + 1}?",
            answers=(
                f"A {index}",
                f"B {index}",
                f"C {index}",
                f"D {index}",
            ),
            correct_index=index % 4,
        )
        for index in range(count)
    )


def test_excel_template_imports_twelve_questions() -> None:
    project = import_project_from_excel(TEMPLATE_PATH)
    assert len(project.questions) == 12
    assert [question.correct_index for question in project.questions] == [
        0,
        0,
        1,
        2,
        3,
        0,
        1,
        2,
        3,
        0,
        1,
        2,
    ]


def test_excel_import_rejects_non_xlsx_file() -> None:
    with pytest.raises(ExcelImportError, match="\\.xlsx"):
        import_project_from_excel(PROJECT_ROOT / "README.md")


def test_project_rejects_more_than_twelve_questions() -> None:
    with pytest.raises(ValidationError, match="máximo 12"):
        Project(title="Demasiadas", questions=_questions(13)).normalized()


def test_three_rounds_use_all_twelve_questions_without_repetition() -> None:
    with tempfile.TemporaryDirectory() as directory:
        selector = RoundSelector(
            Path(directory) / "history.json",
            rng=random.Random(42),
        )
        questions = _questions()
        seen: set[str] = set()
        for expected_round in range(1, 4):
            selection = selector.select(questions)
            fingerprints = {
                question_fingerprint(question) for question in selection.questions
            }
            assert selection.round_number == expected_round
            assert selection.repeated_count == 0
            assert len(fingerprints) == 4
            assert not fingerprints.intersection(seen)
            seen.update(fingerprints)
        assert len(seen) == 12


def test_fourth_round_reuses_only_after_bank_is_exhausted() -> None:
    with tempfile.TemporaryDirectory() as directory:
        history_path = Path(directory) / "history.json"
        questions = _questions()
        selector = RoundSelector(history_path, rng=random.Random(7))
        first_three = [selector.select(questions) for _ in range(3)]
        fourth = RoundSelector(
            history_path,
            rng=random.Random(99),
        ).select(questions)
        assert [selection.repeated_count for selection in first_three] == [0, 0, 0]
        assert fourth.round_number == 4
        assert fourth.repeated_count == 4
