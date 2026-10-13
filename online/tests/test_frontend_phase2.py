from __future__ import annotations

from fastapi.testclient import TestClient

from desafio_online.app import app


def login(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"password": "desafio"})
    assert response.status_code == 200


def test_lobby_restores_qr_connected_counter_and_canonical_action() -> None:
    with TestClient(app) as client:
        response = client.get("/host/123456")
        assert response.status_code == 200
        html = response.text
        assert "Sala de enrolamiento" in html
        assert 'id="roomQr"' in html
        assert 'id="lobbyConnectedCount"' in html
        assert "Conectados" in html
        assert "Cerrar sala e iniciar clasificación" in html
        assert "Copiar enlace" not in html
        assert "Finalizar partida" not in html
        assert "Panel del moderador" in html


def test_lobby_preserves_the_1_3_5_selector_location_for_phase6() -> None:
    with TestClient(app) as client:
        html = client.get("/host/123456").text
        assert 'data-questions="1"' in html
        assert 'data-questions="3"' in html
        assert 'data-questions="5"' in html
        assert "Preguntas por jugador" in html
        assert "Modo seleccionado: 5 preguntas por jugador." in html


def test_lobby_script_moves_qualifier_action_to_left_panel_and_hides_dashboard_parts() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/host.js")
        assert script.status_code == 200
        text = script.text
        assert 'byId("lobbyStartButton").addEventListener' in text
        assert f"/api/games/${{code}}/qualifier/start" in text
        assert 'byId("metricGrid").classList.add("hidden")' in text
        assert 'stageCard.classList.toggle("hidden", showLobby)' in text
        assert 'byId("participantsCard").classList.toggle("lobby-focus", showLobby)' in text
        assert 'byId("copyLinkButton")' not in text
        assert 'byId("finishButton")' not in text


def test_phase2_styles_use_v3_background_and_compact_participant_grid() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/phase2.css")
        assert response.status_code == 200
        css = response.text
        assert "game_background_v3_clean.png" in css
        assert ".classic-room-panel" in css
        assert ".connected-counter" in css
        assert ".lobby-focus .participant-list" in css
        assert "minmax(145px, 1fr)" in css


def test_room_creation_and_qualifier_api_contract_remain_unchanged() -> None:
    with TestClient(app) as client:
        login(client)
        created = client.post("/api/games", json={"bank_id": "main"})
        assert created.status_code == 201
        code = created.json()["room_code"]
        snapshot = client.get(f"/api/games/{code}")
        assert snapshot.status_code == 200
        assert snapshot.json()["state"] == "lobby_open"
