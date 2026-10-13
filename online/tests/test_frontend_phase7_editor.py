from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from desafio_online.app import app


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
LOGIC_PATH = REPOSITORY_ROOT / "online" / "static" / "phase7_editor_logic.js"


def test_manual_question_editor_is_enabled_and_loads_phase7_assets() -> None:
    with TestClient(app) as client:
        html = client.get("/admin").text
        assert "/assets/phase7_editor.css" in html
        assert "/assets/phase7_editor_logic.js" in html
        assert 'id="manualEditorButton"' in html
        assert 'id="manualEditorButton" class="classic-menu-button" type="button" disabled' not in html
        assert "Administrador manual" in html


def test_manual_editor_exposes_canonical_controls_and_limits() -> None:
    with TestClient(app) as client:
        html = client.get("/admin").text
        for token in (
            "Preguntas <span id=\"questionCount\">0 / 12</span>",
            'id="newQuestionButton"',
            'id="duplicateQuestionButton"',
            'id="moveQuestionUpButton"',
            'id="moveQuestionDownButton"',
            'id="deleteQuestionButton"',
            "Eliminar",
            "Cambios sin guardar",
            "Cancelar",
            "Guardar base de preguntas",
            "Cerrar",
            'maxlength="320"',
            'maxlength="140"',
            "0/320",
            "0/140",
        ):
            assert token in html
        for value, letter in enumerate("ABCD"):
            assert f'<option value="{value}">{letter}</option>' in html


def test_manual_editor_script_uses_transactional_questions_api_with_revision() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/admin.js").text
        logic = client.get("/assets/phase7_editor_logic.js").text

        assert 'api("/api/questions")' in script
        assert 'method: "PUT"' in script
        assert "editorState.snapshot.revision" in script
        assert "expected_revision" in logic
        assert "serializeForPut" in script
        assert "serializeForPut" in logic


def test_manual_editor_handles_conflicts_read_only_and_keeps_draft_on_http_errors() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/admin.js").text
        assert "error.status === 409" in script
        assert "La base de preguntas cambió en otra pestaña" in script
        assert "error.status === 422" in script
        assert "error.status === 503" in script
        assert "bank_read_only" in script
        assert "Tu draft sigue abierto" in script
        assert "editorState.draft = editorLogic.cloneDraft(saved)" in script
        assert "editorState.draft = editorLogic.cloneDraft(snapshot)" in script


def test_manual_editor_does_not_introduce_alternative_crud_questions_api() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/admin.js").text
        assert 'method: "DELETE"' not in script
        assert 'method: "PATCH"' not in script
        assert "questions/${" not in script
        assert "/api/questions/import" in script
        assert "/api/questions/template" not in script


def test_manual_editor_save_requires_exactly_twelve_valid_questions() -> None:
    with TestClient(app) as client:
        logic = client.get("/assets/phase7_editor_logic.js").text
        assert "REQUIRED_COUNT = 12" in logic
        assert "exactamente 12 preguntas activas" in logic
        assert "PROMPT_LIMIT = 320" in logic
        assert "ANSWER_LIMIT = 140" in logic
        assert "validateBank" in logic


def test_excel_import_ui_is_enabled_and_uses_historical_template_download() -> None:
    with TestClient(app) as client:
        html = client.get("/admin").text
        assert 'id="importExcelButton"' in html
        assert 'id="importExcelButton" class="classic-menu-button" type="button" disabled' not in html
        assert "Importar base de preguntas desde Excel" in html
        assert "Descargar plantilla Excel" in html
        assert 'href="/api/questions/template"' in html
        assert "Abrir carpeta de plantilla" not in html
        assert 'id="excelFileInput"' in html
        assert 'type="file"' in html
        assert 'accept=".xlsx' in html
        assert "Seleccionar archivo" in html
        assert "La versión web requiere 12 preguntas activas" in html
        assert "Cargar base de preguntas" in html


def test_excel_import_script_posts_binary_file_with_filename_and_expected_revision() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/admin.js").text
        assert 'api("/api/questions")' in script
        assert "uploadExcelBank" in script
        assert "/api/questions/import?" in script
        assert "expected_revision" in script
        assert "filename: file.name" in script
        assert "body: file" in script
        assert "new URLSearchParams" in script
        assert "window.confirm(\"Esta acción reemplazará la base de preguntas actual completa" in script


def test_excel_import_handles_409_422_read_only_and_preserves_selected_file_on_failure() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/admin.js").text
        assert "error.status === 409" in script
        assert "El archivo seleccionado no se cargó" in script
        assert "error.status === 422" in script
        assert "Validación del Excel" in script
        assert "error.status === 503" in script
        assert "bank_read_only" in script
        assert "importState.file = null" in script
        assert "Base de preguntas importada correctamente" in script


@pytest.mark.skipif(shutil.which("node") is None, reason="Node no está disponible")
def test_manual_editor_draft_logic_duplicate_move_delete_dirty_and_serialize() -> None:
    script = f"""
      const logic = require({str(LOGIC_PATH)!r});
      const snapshot = {{
        title: "Banco",
        revision: "a".repeat(64),
        questions: Array.from({{ length: 12 }}, (_, index) => ({{
          prompt: `Pregunta ${{index + 1}}`,
          answers: ["A", "B", "C", "D"].map((letter) => `${{letter}} ${{index + 1}}`),
          correct_index: index % 4,
        }})),
      }};
      let draft = logic.cloneDraft(snapshot);
      let changed = logic.duplicateQuestion(draft, 0);
      if (changed.draft.questions.length !== 13) throw new Error("duplicate failed");
      if (changed.selectedIndex !== 1) throw new Error("duplicate selection failed");
      changed = logic.moveQuestion(changed.draft, 1, 1);
      if (changed.selectedIndex !== 2) throw new Error("move failed");
      changed = logic.deleteQuestion(changed.draft, 2);
      draft = changed.draft;
      if (draft.questions.length !== 12) throw new Error("delete failed");
      if (logic.isDirty(snapshot, draft) !== false) throw new Error("dirty should be false after reversible edit");
      draft = logic.updateQuestion(draft, 0, {{ prompt: "Pregunta editada" }});
      if (logic.isDirty(snapshot, draft) !== true) throw new Error("dirty failed");
      const validation = logic.validateBank(draft);
      if (!validation.valid) throw new Error(validation.errors[0]);
      const payload = logic.serializeForPut(draft, snapshot.revision);
      if (payload.expected_revision !== snapshot.revision) throw new Error("revision missing");
      if (payload.questions.length !== 12) throw new Error("serialized question count failed");
    """
    subprocess.run(["node", "-e", script], check=True, cwd=REPOSITORY_ROOT)
