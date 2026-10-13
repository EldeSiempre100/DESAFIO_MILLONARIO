from __future__ import annotations

from fastapi.testclient import TestClient

from desafio_online.app import app


def test_host_loads_phase3_scene_styles() -> None:
    with TestClient(app) as client:
        response = client.get("/host/123456")
        assert response.status_code == 200
        assert "/assets/phase3.css" in response.text
        assert "Panel del moderador" in response.text


def test_phase3_restores_named_canonical_scenes() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/host.js").text
        for copy in (
            "PREGUNTA CLASIFICATORIA",
            "RESULTADO DE LA CLASIFICACIÓN",
            "JUGADORES CLASIFICADOS",
            "Confirmar los 2 jugadores",
            "Comenzar ronda",
            "RONDA FINALIZADA",
            "¡TENEMOS DOS GANADORES!",
        ):
            assert copy in script


def test_qualifier_is_automatic_without_manual_close_control() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/host.js").text
        assert "Cerrar respuestas ahora" not in script
        assert "/qualifier/close" not in script
        assert "renderTimer(question.opening)" in script


def test_question_scene_uses_server_question_total_and_v3_lifelines() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/host.js").text
        assert "question.question_total" in script
        assert "round.question_total" in script
        assert "v3-lifeline-stack" in script
        assert "/media/images/phone.png" in script
        assert "/media/images/audience.png" in script
        assert "/lifelines/${name}" in script


def test_game_scene_hides_dashboard_metrics_and_participant_panel() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/host.js").text
        css = client.get("/assets/phase3.css").text
        assert 'byId("metricGrid").classList.add("hidden")' in script
        assert 'byId("participantsCard").classList.toggle("hidden", !showLobby)' in script
        assert ".host-layout.game-in-progress #participantsCard" in css
        assert ".host-layout.game-in-progress #metricGrid" in css


def test_selection_scene_confirms_server_preselection_without_admin_list() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/host.js").text
        assert "preselected_ids" in script
        assert "classified-player-card" in script
        assert "ranking-list" not in script
        assert "candidate-card" not in script
