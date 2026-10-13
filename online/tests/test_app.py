from __future__ import annotations

import re

from fastapi.testclient import TestClient

from desafio_online.app import app, registry


def login(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"password": "desafio"})
    assert response.status_code == 200


def create_room(client: TestClient) -> str:
    login(client)
    response = client.post("/api/games", json={"bank_id": "main"})
    assert response.status_code == 201
    code = response.json()["room_code"]
    assert re.fullmatch(r"\d{6}", code)
    return code


def enroll(client: TestClient, code: str, count: int = 4):
    joined = []
    for index in range(count):
        response = client.post(
            f"/api/rooms/{code}/join",
            json={
                "alias": f"Web {index}",
                "device_id": f"web-device-{code}-{index}",
                "avatar": "star" if index == 0 else "explorer",
            },
        )
        assert response.status_code == 200
        joined.append(response.json())
    return joined


def test_thirty_participants_can_join_from_the_same_ip() -> None:
    with TestClient(app) as client:
        code = create_room(client)
        joined = enroll(client, code, 30)
        assert len(joined) == 30
        assert len({participant["participant_id"] for participant in joined}) == 30


def close_qualifier_with_answers(client: TestClient, code: str, joined):
    room = registry.get(code)
    started = client.post(f"/api/games/{code}/qualifier/start")
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
        assert result.to_dict()["status"] == "accepted"
    closed = client.post(f"/api/games/{code}/qualifier/close")
    assert closed.status_code == 200
    return closed.json()


def confirm_players(client: TestClient, code: str, ids: list[str]):
    assert client.post(f"/api/games/{code}/selection/start").status_code == 200
    confirmed = client.post(
        f"/api/games/{code}/players/confirm",
        json={"participant_ids": ids},
    )
    assert confirmed.status_code == 200
    return confirmed.json()


def test_health_auth_creation_qr_and_current_pages() -> None:
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"
        assert client.get("/favicon.ico").status_code == 204
        assert client.get("/api/banks").status_code == 401
        code = create_room(client)
        banks = client.get("/api/banks").json()["banks"]
        assert banks[0]["question_count"] == 12
        assert client.get(f"/api/rooms/{code}/qr").headers["content-type"].startswith("image/svg+xml")
        for path in ("/", "/admin", f"/host/{code}", f"/join/{code}"):
            assert client.get(path).status_code == 200


def test_api_full_qualifier_selection_and_round_start() -> None:
    with TestClient(app) as client:
        code = create_room(client)
        joined = enroll(client, code, 5)
        results = close_qualifier_with_answers(client, code, joined)
        assert results["total"] == 5
        assert len(results["ranking"]) == 5
        selected = [item["participant_id"] for item in results["ranking"][:2]]
        round_intro = confirm_players(client, code, selected)
        assert round_intro["round_number"] == 1
        assert round_intro["question_total"] == 5

        started = client.post(f"/api/games/{code}/rounds/start")
        assert started.status_code == 200
        assert started.json()["opening"]["duration_ms"] == 45_000
        snapshot = client.get(f"/api/games/{code}").json()
        assert snapshot["state"] == "question_active"
        assert snapshot["round"]["active_player"]["participant_id"] == selected[0]
        audience = next(item for item in joined if item["participant_id"] not in selected)
        assert registry.get(code).player_snapshot(audience["participant_id"])["question"] is None


def test_websocket_snapshots_follow_role_and_reconnection() -> None:
    with TestClient(app) as client:
        code = create_room(client)
        joined = enroll(client, code, 4)
        results = close_qualifier_with_answers(client, code, joined)
        selected = [item["participant_id"] for item in results["ranking"][:2]]
        confirm_players(client, code, selected)
        assert client.post(f"/api/games/{code}/rounds/start").status_code == 200

        active = next(item for item in joined if item["participant_id"] == selected[0])
        public = next(item for item in joined if item["participant_id"] not in selected)
        with client.websocket_connect(f"/ws/rooms/{code}?token={active['token']}") as active_ws:
            active_snapshot = active_ws.receive_json()["payload"]
            assert active_snapshot["game_role"] == "player"
            assert active_snapshot["is_active_player"] is True
            assert active_snapshot["question"] is not None
            assert set(active_snapshot["question"]) == {"opening", "answered"}
        with client.websocket_connect(f"/ws/rooms/{code}?token={public['token']}") as public_ws:
            public_snapshot = public_ws.receive_json()["payload"]
            assert public_snapshot["game_role"] == "audience"
            assert public_snapshot["question"] is None

        reconnect = client.post(
            f"/api/rooms/{code}/reconnect",
            json={"token": active["token"]},
        )
        assert reconnect.status_code == 200
        assert reconnect.json()["role"] == "selected"


def test_audience_lifeline_enables_only_public_websocket() -> None:
    with TestClient(app) as client:
        code = create_room(client)
        joined = enroll(client, code, 4)
        results = close_qualifier_with_answers(client, code, joined)
        selected = [item["participant_id"] for item in results["ranking"][:2]]
        confirm_players(client, code, selected)
        client.post(f"/api/games/{code}/rounds/start")
        activated = client.post(f"/api/games/{code}/lifelines/audience")
        assert activated.status_code == 200
        assert activated.json()["opening"]["duration_ms"] == 15_000
        room = registry.get(code)
        for person in joined:
            mobile = room.player_snapshot(person["participant_id"])
            if person["participant_id"] in selected:
                assert mobile["question"] is None
            else:
                assert mobile["question"] is not None
                assert set(mobile["question"]) == {"opening", "answered"}


def test_canonical_setting_and_compatibility_routes_remain_present() -> None:
    with TestClient(app) as client:
        code = create_room(client)
        for questions_per_round in (1, 3, 5):
            configured = client.post(
                f"/api/games/{code}/settings",
                json={"questions_per_round": questions_per_round},
            )
            assert configured.status_code == 200
            assert configured.json()["questions_per_round"] == questions_per_round
            assert client.get(f"/api/games/{code}").json()["settings"]["questions_per_round"] == questions_per_round
        assert client.post(
            f"/api/games/{code}/settings",
            json={"questions_per_round": 2},
        ).status_code == 422
        for suffix in (
            "qualifier/start",
            "qualifier/close",
            "selection/start",
            "players/confirm",
            "rounds/start",
            "questions/next",
            "rounds/advance",
            "lifelines/fifty",
            "replay",
            "questions/open",
            "questions/close",
            "finish",
        ):
            response = client.post(f"/api/games/{code}/{suffix}", json={})
            assert response.status_code != 404


def test_public_pages_keep_product_naming_clean_and_mobile_is_keys_only() -> None:
    forbidden = re.compile(r"\b(v4|beta|build|rama)\b", re.IGNORECASE)
    with TestClient(app) as client:
        for path in ("/", "/admin", "/host/123456", "/join/123456"):
            response = client.get(path)
            assert response.status_code == 200
            assert forbidden.search(response.text) is None
        play_script = client.get("/assets/play.js").text
        assert "question.prompt" not in play_script
        assert "question.answers" not in play_script
        assert "opening.allowed_answers" in play_script


def test_web_exposes_every_canonical_audio_asset_and_visual_assets() -> None:
    with TestClient(app) as client:
        background = client.get("/media/images/game_background_v3_clean.png")
        assert background.status_code == 200
        assert background.headers["content-type"] == "image/png"
        atlas = client.get("/assets/atlas_logo_transparent.png")
        assert atlas.status_code == 200
        assert atlas.headers["content-type"] == "image/png"
        for filename in (
            "intro.mp3",
            "question_music.mp3",
            "transition.mp3",
            "correct.wav",
            "incorrect.wav",
            "lifeline.wav",
            "call.mp3",
            "audience.wav",
        ):
            assert client.get(f"/media/audio/{filename}").status_code == 200
