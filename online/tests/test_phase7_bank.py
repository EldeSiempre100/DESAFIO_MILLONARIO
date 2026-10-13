from __future__ import annotations

from pathlib import Path

import pytest

from desafio_online.bank import BankError, QuestionBankService, validate_published_project
from millonario_v3.model import Project, Question
from millonario_v3.storage import backup_paths, load_project, save_project


def make_project(title: str = "Banco de prueba") -> Project:
    questions = []
    for index in range(12):
        questions.append(
            Question(
                prompt=f"Pregunta única {index + 1}",
                answers=(
                    f"A {index}",
                    f"B {index}",
                    f"C {index}",
                    f"D {index}",
                ),
                correct_index=index % 4,
            )
        )
    return Project(title=title, questions=tuple(questions)).normalized()


def seed_file(tmp_path: Path) -> Path:
    seed = tmp_path / "seed.juego"
    save_project(seed, make_project(), create_backup=False)
    return seed


def test_service_seeds_configured_path_and_exposes_revision(tmp_path: Path) -> None:
    seed = seed_file(tmp_path)
    target = tmp_path / "persistent" / "demo.juego"
    service = QuestionBankService(target, seed_path=seed, allow_writes=True, storage_mode="test")

    snapshot = service.snapshot()
    assert target.exists()
    assert snapshot["question_count"] == 12
    assert len(snapshot["revision"]) == 64
    assert snapshot["writable"] is True
    assert snapshot["storage_mode"] == "test"


def test_publish_is_transactional_and_creates_backup(tmp_path: Path) -> None:
    seed = seed_file(tmp_path)
    target = tmp_path / "demo.juego"
    service = QuestionBankService(target, seed_path=seed, allow_writes=True)
    before = service.snapshot()

    updated = make_project("Banco actualizado")
    after = service.publish(updated, expected_revision=before["revision"])

    assert after["title"] == "Banco actualizado"
    assert after["revision"] != before["revision"]
    assert backup_paths(target)[0].exists()
    assert load_project(target).title == "Banco actualizado"


def test_stale_revision_cannot_overwrite_newer_bank(tmp_path: Path) -> None:
    seed = seed_file(tmp_path)
    target = tmp_path / "demo.juego"
    service = QuestionBankService(target, seed_path=seed, allow_writes=True)
    stale = service.snapshot()["revision"]
    service.publish(make_project("Primera edición"), expected_revision=stale)

    with pytest.raises(BankError) as caught:
        service.publish(make_project("Edición obsoleta"), expected_revision=stale)

    assert caught.value.code == "revision_conflict"
    assert service.load().title == "Primera edición"


def test_read_only_mode_never_reports_successful_publish(tmp_path: Path) -> None:
    seed = seed_file(tmp_path)
    service = QuestionBankService(seed, allow_writes=False, storage_mode="read_only_repository")
    revision = service.snapshot()["revision"]

    with pytest.raises(BankError) as caught:
        service.publish(make_project("No debe guardarse"), expected_revision=revision)

    assert caught.value.code == "bank_read_only"
    assert load_project(seed).title == "Banco de prueba"


def test_v4_publication_requires_exactly_twelve_questions() -> None:
    project = Project(title="Corto", questions=make_project().questions[:11])
    with pytest.raises(BankError) as caught:
        validate_published_project(project)
    assert caught.value.code == "invalid_bank"


def test_v4_publication_rejects_duplicate_prompts_after_normalization() -> None:
    project = make_project()
    questions = list(project.questions)
    questions[-1] = Question(
        prompt="  PREGUNTA   ÚNICA 1  ",
        answers=("AA", "BB", "CC", "DD"),
        correct_index=0,
    )
    with pytest.raises(BankError) as caught:
        validate_published_project(Project(title=project.title, questions=tuple(questions)))
    assert caught.value.code == "invalid_bank"
