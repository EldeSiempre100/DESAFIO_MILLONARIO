from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from millonario.model import Project, Question, ValidationError, default_project
from millonario.storage import (
    ProjectFileError,
    backup_paths,
    load_project,
    load_project_with_recovery,
    project_directory_is_writable,
    save_project,
)


class ModelStorageTests(unittest.TestCase):
    def test_default_project_contains_six_source_questions(self) -> None:
        project = default_project()
        self.assertEqual(len(project.questions), 6)
        self.assertEqual(
            [question.correct_index for question in project.questions],
            [0, 0, 1, 2, 3, 3],
        )

    def test_project_can_add_move_and_delete_questions(self) -> None:
        project = default_project()
        added = project.add_question(
            Question("Pregunta nueva", ("A1", "B1", "C1", "D1"), 2),
            1,
        )
        self.assertEqual(len(added.questions), 7)
        moved = added.move_question(1, 3)
        self.assertEqual(moved.questions[3].prompt, "Pregunta nueva")
        deleted = moved.delete_question(3)
        self.assertEqual(len(deleted.questions), 6)

    def test_round_trip_preserves_question(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo.juego"
            expected = default_project()
            save_project(path, expected)
            self.assertEqual(load_project(path), expected)

    def test_existing_project_gets_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo.juego"
            first = default_project()
            save_project(path, first)
            second = first.replace_question(
                0,
                Question(
                    prompt="Pregunta modificada",
                    answers=("Uno", "Dos", "Tres", "Cuatro"),
                    correct_index=2,
                ),
            )
            save_project(path, second)
            self.assertEqual(load_project(path), second)
            self.assertEqual(load_project(path.with_suffix(".juego.bak")), first)

    def test_three_rotating_backups_are_kept(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo.juego"
            project = default_project()
            for index in range(5):
                updated = project.replace_question(
                    0,
                    Question(
                        prompt=f"Versión {index}",
                        answers=("Uno", "Dos", "Tres", "Cuatro"),
                        correct_index=index % 4,
                    ),
                )
                save_project(path, updated)
            self.assertTrue(all(backup.exists() for backup in backup_paths(path)))

    def test_corrupt_project_recovers_from_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo.juego"
            original = default_project()
            save_project(path, original)
            changed = original.replace_question(
                0,
                Question("Cambio", ("Uno", "Dos", "Tres", "Cuatro"), 0),
            )
            save_project(path, changed)
            path.write_text("archivo dañado", encoding="utf-8")
            recovered, source = load_project_with_recovery(path)
            self.assertEqual(recovered, original)
            self.assertEqual(source, path.with_suffix(".juego.bak"))
            self.assertEqual(load_project(path), original)

    def test_project_directory_writable_probe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.assertTrue(
                project_directory_is_writable(Path(directory) / "demo.juego")
            )

    def test_invalid_question_is_rejected(self) -> None:
        project = Project(
            title="Inválido",
            questions=(
                Question(
                    prompt="¿Pregunta?",
                    answers=("Repetida", "Repetida", "Tres", "Cuatro"),
                    correct_index=0,
                ),
            ),
        )
        with self.assertRaises(ValidationError):
            project.validate()

    def test_corrupt_project_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "roto.juego"
            path.write_text("no es un zip", encoding="utf-8")
            with self.assertRaises(ProjectFileError):
                load_project(path)


if __name__ == "__main__":
    unittest.main()
