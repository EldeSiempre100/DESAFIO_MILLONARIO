from __future__ import annotations

from fastapi.testclient import TestClient

from desafio_online.app import app


def test_home_uses_moderator_entry_and_has_no_manual_room_code_form() -> None:
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert ">Moderador<" in response.text
        assert "Acceso anfitrión" not in response.text
        assert "roomForm" not in response.text
        assert "Escribe el código de sala" not in response.text
        assert "Escanea el QR de la sala" in response.text


def test_moderator_page_restores_canonical_menu_without_bank_selection() -> None:
    with TestClient(app) as client:
        response = client.get("/admin")
        assert response.status_code == 200
        assert "Acceso moderador" in response.text
        assert "Panel del moderador" in response.text
        assert "Crear sala participativa" in response.text
        assert "Editar preguntas" in response.text
        assert "Administrador manual" in response.text
        assert "Importar base de preguntas desde Excel" in response.text
        assert "Mis bancos" not in response.text
        assert "bankList" not in response.text


def test_moderator_script_creates_main_room_directly_without_banks_roundtrip() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/admin.js")
        assert script.status_code == 200
        assert 'bank_id: "main"' in script.text
        assert "/api/banks" not in script.text


def test_phase1_styles_are_served() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/phase1.css")
        assert response.status_code == 200
        assert "moderator-menu-panel" in response.text
        assert "menu_background_v2.png" in response.text
