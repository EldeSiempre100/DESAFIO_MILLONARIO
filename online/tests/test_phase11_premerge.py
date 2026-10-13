from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from millonario_v3.participation.models import SubmissionStatus
from millonario_v3.session import SessionState

from desafio_online.app import app, registry
from desafio_online.app_core import limiter


def login(client: TestClient) -> None:
    limiter._attempts.clear()
    response = client.post("/api/auth/login", json={"password": "desafio"})
    assert response.status_code == 200


def create_room(client: TestClient) -> str:
    login(client)
    response = client.post("/api/games", json={"bank_id": "main"})
    assert response.status_code == 201
    return response.json()["room_code"]


def join_people(client: TestClient, room_code: str, count: int) -> list[dict[str, str]]:
    joined: list[dict[str, str]] = []
    for index in range(count):
        response = client.post(
            f"/api/rooms/{room_code}/join",
            json={
                "alias": f"QA {room_code}-{index:02d}",
                "device_id": f"qa-device-{room_code}-{index:02d}",
                "avatar": "explorer",
            },
        )
        assert response.status_code == 200
        joined.append(response.json())
    return joined


def complete_qualifier(client: TestClient, room_code: str, joined: list[dict[str, str]]) -> list[str]:
    room = registry.get(room_code)
    started = client.post(f"/api/games/{room_code}/qualifier/start")
    assert started.status_code == 200
    assert started.json()["opening"]["duration_ms"] == 30_000
    opening_id = started.json()["opening"]["opening_id"]
    correct = "ABCD"[room.qualifier_question.question.correct_index]
    for person in joined:
        result = room.manager.submit_answer(
            token=person["token"],
            opening_id=opening_id,
            answer=correct,
        )
        assert result.status is SubmissionStatus.ACCEPTED

    closed = client.post(f"/api/games/{room_code}/qualifier/close")
    assert closed.status_code == 200
    ranking = closed.json()["ranking"]
    assert len(ranking) == len(joined)
    return [item["participant_id"] for item in ranking[:2]]


def confirm_players(client: TestClient, room_code: str, selected: list[str]) -> None:
    assert client.post(f"/api/games/{room_code}/selection/start").status_code == 200
    confirmed = client.post(
        f"/api/games/{room_code}/players/confirm",
        json={"participant_ids": selected},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["round_number"] == 1


def answer_active_question(room_code: str, joined: list[dict[str, str]]) -> None:
    room = registry.get(room_code)
    active = next(
        item for item in joined if item["participant_id"] == room.active_player_id
    )
    correct = "ABCD"[room.question_session.question.correct_index]
    result, revealed = room.submit_regular_answer(
        token=active["token"],
        opening_id=room.question_opening_id,
        answer=correct,
    )
    assert result["status"] == "accepted"
    assert revealed is True


def play_complete_game(client: TestClient, room_code: str, joined: list[dict[str, str]], questions_per_round: int) -> None:
    for round_index in range(2):
        started = client.post(f"/api/games/{room_code}/rounds/start")
        assert started.status_code == 200
        assert started.json()["opening"]["duration_ms"] == 45_000
        assert started.json()["question_total"] == questions_per_round

        for question_number in range(1, questions_per_round + 1):
            snapshot = client.get(f"/api/games/{room_code}").json()
            assert snapshot["state"] == "question_active"
            assert snapshot["question"]["question_number"] == question_number
            assert snapshot["question"]["question_total"] == questions_per_round

            answer_active_question(room_code, joined)
            advanced = client.post(f"/api/games/{room_code}/questions/next")
            assert advanced.status_code == 200

        room = registry.get(room_code)
        assert room.state is SessionState.ROUND_SUMMARY
        advanced_round = client.post(f"/api/games/{room_code}/rounds/advance")
        assert advanced_round.status_code == 200
        expected_state = "session_summary" if round_index == 1 else "round_intro"
        assert client.get(f"/api/games/{room_code}").json()["state"] == expected_state


@pytest.mark.parametrize("questions_per_round", [1, 3, 5])
def test_phase11_api_walkthrough_modes_1_3_5_reach_final_and_replay(
    questions_per_round: int,
) -> None:
    with TestClient(app) as client:
        room_code = create_room(client)
        configured = client.post(
            f"/api/games/{room_code}/settings",
            json={"questions_per_round": questions_per_round},
        )
        assert configured.status_code == 200

        joined = join_people(client, room_code, 6)
        tokens_before = {item["participant_id"]: item["token"] for item in joined}
        selected = complete_qualifier(client, room_code, joined)
        confirm_players(client, room_code, selected)
        play_complete_game(client, room_code, joined, questions_per_round)

        snapshot = client.get(f"/api/games/{room_code}").json()
        assert snapshot["state"] == "session_summary"
        assert snapshot["summary"]["scores"] == [questions_per_round, questions_per_round]

        replay = client.post(f"/api/games/{room_code}/replay")
        assert replay.status_code == 200
        replay_snapshot = replay.json()
        assert replay_snapshot["room_code"] == room_code
        assert replay_snapshot["state"] == "lobby_open"
        assert replay_snapshot["settings"]["questions_per_round"] == questions_per_round

        room = registry.get(room_code)
        for participant_id, token in tokens_before.items():
            assert room.manager.authenticate(token).participant_id == participant_id
        assert all(participant.role == "audience" for participant in room.manager.participants.values())

        reconfigured = client.post(
            f"/api/games/{room_code}/settings",
            json={"questions_per_round": 5 if questions_per_round != 5 else 1},
        )
        assert reconfigured.status_code == 200


def test_phase11_thirty_participants_same_ip_rejects_number_31_and_can_qualify() -> None:
    with TestClient(app) as client:
        room_code = create_room(client)
        joined = join_people(client, room_code, 30)
        overflow = client.post(
            f"/api/rooms/{room_code}/join",
            json={
                "alias": "QA overflow",
                "device_id": f"qa-device-{room_code}-overflow",
                "avatar": "explorer",
            },
        )
        assert overflow.status_code == 409
        assert overflow.json()["detail"]["code"] == "room_full"

        selected = complete_qualifier(client, room_code, joined)
        assert len(selected) == 2
        snapshot = client.get(f"/api/games/{room_code}").json()
        assert snapshot["enrolled"] == 30
        assert snapshot["state"] == "qualifier_results"
