from __future__ import annotations

from fastapi.testclient import TestClient

from millonario_v3.participation.api import ConnectionHub, create_app
from millonario_v3.participation.room import RoomManager


def make_client(mobile_dir) -> tuple[TestClient, RoomManager]:
    manager = RoomManager(session_id="ses_test", room_code="4827")
    app = create_app(manager, mobile_dir, ConnectionHub())
    return TestClient(app), manager


def test_health_bootstrap_static_and_join(tmp_path) -> None:
    mobile = tmp_path / "mobile"
    mobile.mkdir()
    (mobile / "index.html").write_text("<h1>Pulsador</h1>", encoding="utf-8")
    client, _ = make_client(mobile)
    with client:
        assert client.get("/health").json()["status"] == "ok"
        bootstrap = client.get("/api/v1/rooms/4827/bootstrap")
        assert bootstrap.status_code == 200
        assert "correct" not in bootstrap.text.casefold()
        assert len(bootstrap.json()["avatars"]) == 8
        page = client.get("/sala/4827")
        assert page.status_code == 200
        assert "Pulsador" in page.text
        joined = client.post(
            "/api/v1/rooms/4827/join",
            json={
                "alias": "Camila",
                "avatar": "creative",
                "device_id": "phone-1",
                "client_version": "0.1",
            },
        )
        assert joined.status_code == 200
        assert joined.json()["token"]
        assert joined.json()["avatar"] == "creative"
        assert joined.json()["avatar_symbol"] == "😎"


def test_simple_active_room_routes_do_not_require_room_code(tmp_path) -> None:
    mobile = tmp_path / "mobile"
    mobile.mkdir()
    (mobile / "index.html").write_text("<h1>Pulsador simple</h1>", encoding="utf-8")
    client, _ = make_client(mobile)
    with client:
        page = client.get("/")
        assert page.status_code == 200
        assert "Pulsador simple" in page.text
        bootstrap = client.get("/api/v1/bootstrap")
        assert bootstrap.status_code == 200
        assert bootstrap.json()["room_code"] == "4827"
        joined = client.post(
            "/api/v1/join",
            json={"alias": "Gonzalo", "device_id": "phone-simple"},
        )
        assert joined.status_code == 200
        assert joined.json()["ws_url"] == "/ws/v1/room"
        with client.websocket_connect(
            f"/ws/v1/room?token={joined.json()['token']}"
        ) as websocket:
            assert websocket.receive_json()["type"] == "room.snapshot"


def test_websocket_snapshot_answer_and_duplicate(tmp_path) -> None:
    mobile = tmp_path / "mobile"
    mobile.mkdir()
    (mobile / "index.html").write_text("ok", encoding="utf-8")
    client, manager = make_client(mobile)
    with client:
        joined = client.post(
            "/api/v1/rooms/4827/join",
            json={"alias": "Camila", "device_id": "phone-1"},
        ).json()
        opening = manager.open_remote(
            opening_type="qualifier",
            question_id="q1",
            duration_ms=20_000,
        )
        with client.websocket_connect(
            f"/ws/v1/rooms/4827?token={joined['token']}"
        ) as websocket:
            snapshot = websocket.receive_json()
            assert snapshot["type"] == "room.snapshot"
            assert "correct_answer" not in str(snapshot)

            message = {
                "type": "answer.submit",
                "opening_id": opening.opening_id,
                "alternative": "D",
            }
            websocket.send_json(message)
            accepted = websocket.receive_json()
            assert accepted["type"] == "answer.ack"
            assert accepted["payload"]["status"] == "accepted"

            websocket.send_json(message)
            duplicate = websocket.receive_json()
            assert duplicate["payload"]["status"] == "duplicate"


def test_http_answer_requires_bearer_token(tmp_path) -> None:
    mobile = tmp_path / "mobile"
    mobile.mkdir()
    (mobile / "index.html").write_text("ok", encoding="utf-8")
    client, manager = make_client(mobile)
    with client:
        joined = client.post(
            "/api/v1/rooms/4827/join",
            json={"alias": "Camila", "device_id": "phone-1"},
        ).json()
        opening = manager.open_remote(
            opening_type="qualifier",
            question_id="q1",
            duration_ms=20_000,
        )
        missing = client.post(
            "/api/v1/rooms/4827/answers",
            json={"opening_id": opening.opening_id, "answer": "A"},
        )
        assert missing.status_code == 401
        accepted = client.post(
            "/api/v1/rooms/4827/answers",
            headers={"Authorization": f"Bearer {joined['token']}"},
            json={"opening_id": opening.opening_id, "answer": "A"},
        )
        assert accepted.status_code == 202
        assert accepted.json()["status"] == "accepted"
