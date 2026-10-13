from __future__ import annotations

from pathlib import Path

from millonario_v3.model import Project, Question
from millonario_v3.participation.models import SubmissionStatus
from millonario_v3.session import SessionState
from millonario_v3.storage import backup_paths, load_project, save_project

from desafio_online.bank import QuestionBankService
from desafio_online.registry import RoomRegistry


def make_project(title: str) -> Project:
    return Project(
        title=title,
        questions=tuple(
            Question(
                prompt=f"{title} pregunta {index + 1}",
                answers=(
                    f"{title} A {index + 1}",
                    f"{title} B {index + 1}",
                    f"{title} C {index + 1}",
                    f"{title} D {index + 1}",
                ),
                correct_index=index % 4,
            )
            for index in range(12)
        ),
    ).normalized()


def join_people(room, count: int = 4):
    return [
        room.manager.join(f"Persistencia {index}", f"persist-device-{index:02d}")
        for index in range(count)
    ]


def reach_round_intro(room, people):
    qualifier = room.start_qualifier()
    correct = "ABCD"[room.qualifier_question.question.correct_index]
    for person in people:
        result = room.manager.submit_answer(
            token=person.token,
            opening_id=qualifier["opening"]["opening_id"],
            answer=correct,
        )
        assert result.status is SubmissionStatus.ACCEPTED
    room.close_qualifier()
    room.begin_player_selection()
    room.confirm_players(room.preselected_ids)


def answer_active_question(room, people):
    token = next(
        person.token
        for person in people
        if person.participant.participant_id == room.active_player_id
    )
    correct = "ABCD"[room.question_session.question.correct_index]
    result, revealed = room.submit_regular_answer(
        token=token,
        opening_id=room.question_opening_id,
        answer=correct,
    )
    assert result["status"] == "accepted"
    assert revealed is True


def finish_short_game(room, people):
    room.configure_questions_per_round(1)
    reach_round_intro(room, people)
    for round_index in range(2):
        room.start_round()
        answer_active_question(room, people)
        room.advance_after_answer()
        assert room.state is SessionState.ROUND_SUMMARY
        room.advance_after_round()
        if round_index == 0:
            assert room.state is SessionState.ROUND_INTRO
    assert room.state is SessionState.SESSION_SUMMARY


def test_recovery_restores_bank_from_valid_backup(tmp_path: Path) -> None:
    seed = tmp_path / "seed.juego"
    target = tmp_path / "bank" / "demo.juego"
    original = make_project("Banco original")
    updated = make_project("Banco actualizado")
    save_project(seed, original, create_backup=False)
    service = QuestionBankService(target, seed_path=seed, allow_writes=True)

    service.publish(updated, expected_revision=service.snapshot()["revision"])
    assert backup_paths(target)[0].exists()
    target.write_bytes(b"archivo corrupto")

    recovered = QuestionBankService(target, seed_path=seed, allow_writes=True)
    assert recovered.snapshot()["title"] == "Banco original"
    assert load_project(target).title == "Banco original"


def test_existing_room_keeps_project_and_new_room_uses_published_bank(tmp_path: Path) -> None:
    seed = tmp_path / "seed.juego"
    target = tmp_path / "demo.juego"
    save_project(seed, make_project("Banco sala A"), create_backup=False)
    bank = QuestionBankService(target, seed_path=seed, allow_writes=True)
    registry = RoomRegistry(target)

    room_a = registry.create(seed=31)
    revision = bank.snapshot()["revision"]
    bank.publish(make_project("Banco sala B"), expected_revision=revision)
    room_b = registry.create(seed=31)

    assert room_a.project.title == "Banco sala A"
    assert room_b.project.title == "Banco sala B"
    assert room_a.project.questions[0].prompt.startswith("Banco sala A")
    assert room_b.project.questions[0].prompt.startswith("Banco sala B")


def test_replay_keeps_room_project_after_master_bank_changes(tmp_path: Path) -> None:
    seed = tmp_path / "seed.juego"
    target = tmp_path / "demo.juego"
    save_project(seed, make_project("Banco replay original"), create_backup=False)
    bank = QuestionBankService(target, seed_path=seed, allow_writes=True)
    registry = RoomRegistry(target)
    room = registry.create(seed=42)
    people = join_people(room)
    finish_short_game(room, people)

    bank.publish(make_project("Banco replay nuevo"), expected_revision=bank.snapshot()["revision"])
    room.repeat()

    assert room.state is SessionState.LOBBY_OPEN
    assert room.project.title == "Banco replay original"
    assert room.orchestrator.plan.qualifier.question.prompt.startswith("Banco replay original")
    new_room = registry.create(seed=42)
    assert new_room.project.title == "Banco replay nuevo"


def test_single_bank_ux_remains_admin_only_without_restoring_mis_bancos() -> None:
    admin = (Path(__file__).resolve().parents[1] / "static" / "admin.html").read_text(encoding="utf-8")
    script = (Path(__file__).resolve().parents[1] / "static" / "admin.js").read_text(encoding="utf-8")

    assert "Mis bancos" not in admin
    assert "/api/banks" not in script
    assert 'bank_id: "main"' in script
