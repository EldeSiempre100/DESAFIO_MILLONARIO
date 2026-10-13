from __future__ import annotations

from fastapi.testclient import TestClient

from desafio_online.app import app


def test_player_page_is_explicitly_silent_and_does_not_load_audio_runtime() -> None:
    with TestClient(app) as client:
        html = client.get("/join/123456").text
        assert "/assets/phase5_mobile.css" in html
        assert "/assets/sound.js" not in html
        assert "soundButton" not in html
        assert "Activar sonido" not in html
        assert "Este dispositivo permanece en silencio" in html


def test_player_script_contains_no_audio_engine_or_audio_playback_calls() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/play.js").text
        forbidden = (
            "GameAudio",
            "gameAudio",
            "new Audio",
            "/media/audio/",
            ".play()",
            "startMusic",
            "playVoice",
        )
        for token in forbidden:
            assert token not in script


def test_player_removes_legacy_sound_preference_but_keeps_identity_tokens() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/play.js").text
        assert 'localStorage.removeItem("desafio:player-sound")' in script
        assert "tokenKey" in script
        assert "deviceKey" in script
        assert "localStorage.setItem(tokenKey, token)" in script
        assert "/reconnect" in script


def test_player_keeps_websocket_reconnection_and_heartbeat() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/play.js").text
        assert "new WebSocket" in script
        assert 'type: "heartbeat"' in script
        assert "reconnectDelay" in script
        assert "setTimeout(connect, reconnectDelay)" in script
        assert "Math.min(reconnectDelay * 1.7, 10000)" in script


def test_player_remains_keys_only_and_honors_server_allowed_answers() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/play.js").text
        assert "question.prompt" not in script
        assert "question.answers" not in script
        assert "opening.allowed_answers" in script
        assert 'const letters = ["A", "B", "C", "D"]' in script
        assert 'type: "answer.submit"' in script
        assert "opening_id: currentOpening.opening_id" in script


def test_player_retains_visual_feedback_without_audio_feedback() -> None:
    with TestClient(app) as client:
        html = client.get("/join/123456").text
        script = client.get("/assets/play.js").text
        assert "Pulsador interactivo" in html
        assert "Prepara tu pulsador" in html
        assert "Selecciona una alternativa" in html
        assert "Respuesta recibida." in script
        assert "Tiempo finalizado." in script
        assert "Este pulsador no está habilitado en este momento." in script


def test_host_audio_runtime_is_untouched_by_mobile_silence() -> None:
    with TestClient(app) as client:
        host = client.get("/host/123456").text
        assert "/assets/sound.js" in host
        assert "/assets/phase4_audio.js" in host
        player = client.get("/join/123456").text
        assert "/assets/sound.js" not in player
        assert "/assets/phase4_audio.js" not in player
