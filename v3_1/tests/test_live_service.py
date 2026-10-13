from __future__ import annotations

import json
from contextlib import ExitStack

import httpx
from websockets.sync.client import connect

from millonario_v3.participation.service import ParticipationService


def test_live_http_and_websocket_service(tmp_path) -> None:
    mobile = tmp_path / "mobile"
    mobile.mkdir()
    (mobile / "index.html").write_text("<h1>Pulsador local</h1>", encoding="utf-8")
    service = ParticipationService(static_dir=mobile, runtime_dir=tmp_path / "runtime")
    try:
        network = service.start(
            session_id="ses_live",
            room_code="4827",
            max_participants=30,
            preferred_port=18887,
        )
        local_base = f"http://127.0.0.1:{network.port}"
        health = httpx.get(f"{local_base}/health", timeout=5)
        assert health.status_code == 200

        joined = httpx.post(
            f"{local_base}/api/v1/rooms/4827/join",
            json={"alias": "Camila", "device_id": "phone-live"},
            timeout=5,
        ).json()
        opening = service.manager.open_remote(
            opening_type="qualifier",
            question_id="q-live",
            duration_ms=20_000,
        )
        with connect(
            f"ws://127.0.0.1:{network.port}/ws/v1/rooms/4827"
            f"?token={joined['token']}",
            open_timeout=5,
        ) as websocket:
            snapshot = json.loads(websocket.recv(timeout=5))
            assert snapshot["type"] == "room.snapshot"
            service.broadcast(
                "qualifier.opened",
                opening.public_dict(),
                participant_ids={joined["participant_id"]},
            )
            event = json.loads(websocket.recv(timeout=5))
            assert event["type"] == "qualifier.opened"
            websocket.send(
                json.dumps(
                    {
                        "type": "answer.submit",
                        "opening_id": opening.opening_id,
                        "alternative": "B",
                    }
                )
            )
            acknowledgement = json.loads(websocket.recv(timeout=5))
            assert acknowledgement["payload"]["status"] == "accepted"
    finally:
        service.stop()


def test_three_clients_receive_selection_and_reconnect_role(tmp_path) -> None:
    mobile = tmp_path / "mobile"
    mobile.mkdir()
    (mobile / "index.html").write_text("<h1>Pulsadores</h1>", encoding="utf-8")
    service = ParticipationService(static_dir=mobile, runtime_dir=tmp_path / "runtime")
    try:
        network = service.start(
            session_id="ses_three",
            room_code="7300",
            max_participants=30,
            preferred_port=18886,
        )
        base = f"http://127.0.0.1:{network.port}"
        joined = [
            httpx.post(
                f"{base}/api/v1/join",
                json={"alias": f"Persona {index}", "device_id": f"phone-{index}"},
                timeout=5,
            ).json()
            for index in range(3)
        ]
        with ExitStack() as stack:
            sockets = [
                stack.enter_context(
                    connect(
                        f"ws://127.0.0.1:{network.port}/ws/v1/room"
                        f"?token={person['token']}",
                        open_timeout=5,
                    )
                )
                for person in joined
            ]
            for websocket in sockets:
                assert json.loads(websocket.recv(timeout=5))["type"] == "room.snapshot"

            selected = [joined[0]["participant_id"], joined[1]["participant_id"]]
            service.manager.set_selected(selected)
            service.broadcast("candidates.selected", {"participant_ids": selected})
            received = [json.loads(socket.recv(timeout=5)) for socket in sockets]
            assert all(event["type"] == "candidates.selected" for event in received)

        with connect(
            f"ws://127.0.0.1:{network.port}/ws/v1/room"
            f"?token={joined[2]['token']}",
            open_timeout=5,
        ) as audience_socket:
            snapshot = json.loads(audience_socket.recv(timeout=5))
            assert snapshot["payload"]["me"]["role"] == "audience"
            assert snapshot["payload"]["opening"] is None
    finally:
        service.stop()
