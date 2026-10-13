from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from millonario_v3.participation.models import SubmissionStatus
from millonario_v3.participation.room import RoomError
from millonario_v3.session import SessionState

from desafio_online.app import app
from desafio_online.registry import RoomRegistry


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROJECT_PATH = REPOSITORY_ROOT / "v3_1" / "projects" / "demo.juego"


def make_room(*, seed: int = 61):
    return RoomRegistry(PROJECT_PATH).create(seed=seed)


def join_people(room, count: int = 4):
    return [
        room.manager.join(f"Fase6 {index}", f"phase6-device-{index:02d}")
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
    return list(room.orchestrator.selected_participants)


def answer_active_question(room, people):
    active = room.active_player_id
    person = next(
        item for item in people if item.participant.participant_id == active
    )
    correct_index = room.question_session.question.correct_index
    result, revealed = room.submit_regular_answer(
        token=person.token,
        opening_id=room.question_opening_id,
        answer="ABCD"[correct_index],
    )
    assert result["status"] == "accepted"
    assert revealed is True


@pytest.mark.parametrize("questions_per_round", [1, 3, 5])
def test_each_mode_finishes_both_rounds_after_exact_configured_count(
    questions_per_round: int,
) -> None:
    room = make_room(seed=60 + questions_per_round)
    assert len(room.plan_ids) == 12
    assert len(set(room.plan_ids)) == 12
    assert len(room.orchestrator.plan.round_one) == 5
    assert len(room.orchestrator.plan.round_two) == 5

    configured = room.configure_questions_per_round(questions_per_round)
    assert configured == {"questions_per_round": questions_per_round}
    assert room.host_snapshot()["settings"]["questions_per_round"] == questions_per_round

    people = join_people(room)
    selected = reach_round_intro(room, people)

    for round_index in range(2):
        opening = room.start_round()
        assert room.active_player_id == selected[round_index]
        assert opening["question_total"] == questions_per_round
        assert opening["question_number"] == 1

        seen_ids: list[str] = []
        for question_index in range(questions_per_round):
            assert room.state is SessionState.QUESTION_ACTIVE
            question = room.regular_question_payload(include_correct=False)
            assert question is not None
            assert question["question_total"] == questions_per_round
            assert question["question_number"] == question_index + 1
            seen_ids.append(question["question_id"])

            answer_active_question(room, people)
            assert room.state is SessionState.ANSWER_REVEALED
            payload = room.advance_after_answer()

            if question_index + 1 < questions_per_round:
                assert room.state is SessionState.QUESTION_ACTIVE
                assert payload["question_number"] == question_index + 2
                assert payload["question_total"] == questions_per_round
            else:
                assert room.state is SessionState.ROUND_SUMMARY
                assert payload["question_total"] == questions_per_round

        assert len(seen_ids) == questions_per_round
        assert len(set(seen_ids)) == questions_per_round
        assert room.orchestrator.scores[round_index] == questions_per_round
        room.advance_after_round()

    assert room.state is SessionState.SESSION_SUMMARY
    assert room.orchestrator.scores == [questions_per_round, questions_per_round]


@pytest.mark.parametrize("questions_per_round", [1, 3, 5])
def test_mode_consumes_only_the_intended_prefix_of_each_canonical_v3_round(
    questions_per_round: int,
) -> None:
    room = make_room(seed=91)
    room.configure_questions_per_round(questions_per_round)

    planned_round_one = tuple(room.orchestrator.plan.round_one[:questions_per_round])
    planned_round_two = tuple(room.orchestrator.plan.round_two[:questions_per_round])

    room.orchestrator.round_index = 0
    assert room.orchestrator.current_questions == planned_round_one
    room.orchestrator.round_index = 1
    assert room.orchestrator.current_questions == planned_round_two

    # El plan maestro permanece intacto: clasificatoria, 5+5 y reserva.
    assert len(room.orchestrator.plan.all_ids) == 12
    assert room.orchestrator.plan.reserve.question_id in room.orchestrator.plan.all_ids


def test_setting_is_locked_after_qualifier_starts() -> None:
    room = make_room()
    people = join_people(room, 2)
    room.configure_questions_per_round(3)
    room.start_qualifier()

    with pytest.raises(RoomError, match="antes de iniciar la clasificatoria"):
        room.configure_questions_per_round(1)

    assert room.questions_per_round == 3
    assert room.state is SessionState.QUALIFIER_OPEN
    assert len(people) == 2


def test_replay_preserves_mode_but_allows_new_choice_in_reopened_lobby() -> None:
    room = make_room(seed=103)
    room.configure_questions_per_round(1)
    people = join_people(room)
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
    room.repeat()
    assert room.state is SessionState.LOBBY_OPEN
    assert room.questions_per_round == 1
    assert room.host_snapshot()["settings"]["questions_per_round"] == 1

    room.configure_questions_per_round(5)
    assert room.questions_per_round == 5


def test_settings_api_accepts_only_1_3_5_and_locks_after_start() -> None:
    with TestClient(app) as client:
        assert client.post("/api/auth/login", json={"password": "desafio"}).status_code == 200
        created = client.post("/api/games", json={"bank_id": "main"})
        assert created.status_code == 201
        code = created.json()["room_code"]

        for value in (1, 3, 5):
            configured = client.post(
                f"/api/games/{code}/settings",
                json={"questions_per_round": value},
            )
            assert configured.status_code == 200
            assert configured.json() == {"questions_per_round": value}
            snapshot = client.get(f"/api/games/{code}").json()
            assert snapshot["settings"]["questions_per_round"] == value

        for invalid in (0, 2, 4, 6):
            assert client.post(
                f"/api/games/{code}/settings",
                json={"questions_per_round": invalid},
            ).status_code == 422

        for index in range(2):
            joined = client.post(
                f"/api/rooms/{code}/join",
                json={
                    "alias": f"Selector {index}",
                    "device_id": f"selector-device-{index:02d}",
                    "avatar": "explorer",
                },
            )
            assert joined.status_code == 200

        assert client.post(f"/api/games/{code}/qualifier/start").status_code == 200
        locked = client.post(
            f"/api/games/{code}/settings",
            json={"questions_per_round": 1},
        )
        assert locked.status_code == 409
        assert "antes de iniciar la clasificatoria" in locked.json()["detail"]["message"]


def test_host_selector_is_live_and_uses_authoritative_settings_endpoint() -> None:
    with TestClient(app) as client:
        html = client.get("/host/123456").text
        script = client.get("/assets/phase6_settings.js").text

        assert "/assets/phase6_settings.js?r=20260818-1" in html
        for value in (1, 3, 5):
            assert f'data-questions="{value}"' in html
        assert 'data-questions="1" disabled' not in html
        assert 'data-questions="3" disabled' not in html
        assert "data.settings?.questions_per_round" in script
        assert "/api/games/${code}/settings" in script
        assert "questions_per_round: questionsPerRound" in script
        assert 'data?.state !== "lobby_open"' in script
