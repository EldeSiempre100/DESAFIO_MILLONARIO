from __future__ import annotations

import io
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from fastapi import FastAPI
from fastapi.testclient import TestClient

from desafio_online.app import app as production_app, limiter
from desafio_online.bank import QuestionBankService
from desafio_online.questions_api import build_questions_router
from millonario_v3.model import Project, Question
from millonario_v3.storage import save_project


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = REPOSITORY_ROOT / "v3_1" / "templates" / "Banco_preguntas_V2.xlsx"


def make_project(title: str = "Banco API") -> Project:
    return Project(
        title=title,
        questions=tuple(
            Question(
                prompt=f"Pregunta API {index + 1}",
                answers=(
                    f"Respuesta A {index}",
                    f"Respuesta B {index}",
                    f"Respuesta C {index}",
                    f"Respuesta D {index}",
                ),
                correct_index=index % 4,
            )
            for index in range(12)
        ),
    ).normalized()


def isolated_client(tmp_path: Path, *, writable: bool = True) -> tuple[TestClient, QuestionBankService]:
    source = tmp_path / "source.juego"
    target = tmp_path / "bank" / "demo.juego"
    save_project(source, make_project(), create_backup=False)
    bank = QuestionBankService(
        target,
        seed_path=source,
        allow_writes=writable,
        storage_mode="test",
    ) if writable else QuestionBankService(
        source,
        allow_writes=False,
        storage_mode="read_only_repository",
    )
    api = FastAPI()
    api.include_router(
        build_questions_router(
            bank,
            require_admin=lambda: "test-session",
            template_path=TEMPLATE,
        )
    )
    return TestClient(api), bank


def put_payload(snapshot: dict, *, title: str) -> dict:
    return {
        "title": title,
        "questions": snapshot["questions"],
        "expected_revision": snapshot["revision"],
    }


def minimal_xlsx(active_questions: int = 12) -> bytes:
    headers = (
        "ID",
        "Pregunta",
        "Alternativa A",
        "Alternativa B",
        "Alternativa C",
        "Alternativa D",
        "Respuesta correcta",
        "Activa",
        "Observaciones",
    )

    def cell(reference: str, value: str) -> str:
        return (
            f'<c r="{reference}" t="inlineStr">'
            f"<is><t>{escape(value)}</t></is>"
            "</c>"
        )

    rows = [
        '<row r="1">'
        + "".join(cell(f"{chr(65 + index)}1", header) for index, header in enumerate(headers))
        + "</row>"
    ]
    for index in range(12):
        row_number = index + 2
        active = "SI" if index < active_questions else "NO"
        values = (
            str(index + 1),
            f"Pregunta Excel {index + 1}",
            f"Excel A {index + 1}",
            f"Excel B {index + 1}",
            f"Excel C {index + 1}",
            f"Excel D {index + 1}",
            "ABCD"[index % 4],
            active,
            "",
        )
        rows.append(
            f'<row r="{row_number}">'
            + "".join(cell(f"{chr(65 + column)}{row_number}", value) for column, value in enumerate(values))
            + "</row>"
        )

    sheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>"
        + "".join(rows)
        + "</sheetData></worksheet>"
    )

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            "</Types>",
        )
        archive.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Preguntas" sheetId="1" r:id="rId1"/></sheets>'
            "</workbook>",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            "</Relationships>",
        )
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
    return output.getvalue()


def test_questions_endpoint_uses_existing_moderator_authentication() -> None:
    with TestClient(production_app) as client:
        assert client.get("/api/questions").status_code == 401
        with limiter._lock:
            limiter._attempts.clear()
        assert client.post("/api/auth/login", json={"password": "desafio"}).status_code == 200
        response = client.get("/api/questions")
        assert response.status_code == 200
        assert response.json()["question_count"] == 12
        assert len(response.json()["revision"]) == 64


def test_manual_publication_returns_new_revision_and_stale_write_is_409(tmp_path: Path) -> None:
    client, _ = isolated_client(tmp_path)
    with client:
        before = client.get("/api/questions").json()
        published = client.put("/api/questions", json=put_payload(before, title="Banco actualizado"))
        assert published.status_code == 200
        assert published.json()["title"] == "Banco actualizado"
        assert published.json()["revision"] != before["revision"]

        stale = client.put("/api/questions", json=put_payload(before, title="Banco obsoleto"))
        assert stale.status_code == 409
        assert stale.json()["detail"]["code"] == "revision_conflict"


def test_manual_publication_requires_exactly_twelve_questions(tmp_path: Path) -> None:
    client, _ = isolated_client(tmp_path)
    with client:
        snapshot = client.get("/api/questions").json()
        payload = put_payload(snapshot, title="Banco corto")
        payload["questions"] = payload["questions"][:11]
        assert client.put("/api/questions", json=payload).status_code == 422


def test_read_only_storage_rejects_write_explicitly(tmp_path: Path) -> None:
    client, _ = isolated_client(tmp_path, writable=False)
    with client:
        snapshot = client.get("/api/questions").json()
        assert snapshot["writable"] is False
        response = client.put("/api/questions", json=put_payload(snapshot, title="No guardar"))
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "bank_read_only"


def test_template_is_downloaded_directly_from_historical_v2_asset(tmp_path: Path) -> None:
    client, _ = isolated_client(tmp_path)
    with client:
        response = client.get("/api/questions/template")
        assert response.status_code == 200
        assert response.content == TEMPLATE.read_bytes()
        assert "Banco_preguntas_V2.xlsx" in response.headers["content-disposition"]


def test_excel_import_accepts_official_template_and_returns_new_revision(tmp_path: Path) -> None:
    client, _ = isolated_client(tmp_path)
    with client:
        before = client.get("/api/questions").json()
        response = client.post(
            "/api/questions/import",
            params={
                "expected_revision": before["revision"],
                "filename": "Banco_preguntas_V2.xlsx",
            },
            content=TEMPLATE.read_bytes(),
            headers={"Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
        )
        assert response.status_code == 200
        assert response.json()["question_count"] == 12
        assert response.json()["revision"] != before["revision"]


def test_excel_import_rejects_non_xlsx_filename_non_zip_and_oversized_payloads(tmp_path: Path) -> None:
    client, _ = isolated_client(tmp_path)
    with client:
        before = client.get("/api/questions").json()
        revision = before["revision"]
        wrong_extension = client.post(
            "/api/questions/import",
            params={"expected_revision": revision, "filename": "fallido.txt"},
            content=minimal_xlsx(),
        )
        assert wrong_extension.status_code == 422

        corrupt = client.post(
            "/api/questions/import",
            params={"expected_revision": revision, "filename": "fallido.xlsx"},
            content=b"esto no es un xlsx",
        )
        assert corrupt.status_code == 422

        oversized = client.post(
            "/api/questions/import",
            params={"expected_revision": revision, "filename": "grande.xlsx"},
            content=b"x" * (2 * 1024 * 1024 + 1),
        )
        assert oversized.status_code == 413
        assert client.get("/api/questions").json()["revision"] == before["revision"]


def test_excel_import_rejects_four_to_eleven_valid_rows_by_v4_policy(tmp_path: Path) -> None:
    client, _ = isolated_client(tmp_path)
    with client:
        before = client.get("/api/questions").json()
        response = client.post(
            "/api/questions/import",
            params={"expected_revision": before["revision"], "filename": "once.xlsx"},
            content=minimal_xlsx(active_questions=11),
        )
        assert response.status_code == 422
        assert "exactamente 12" in response.json()["detail"]["message"]
        assert client.get("/api/questions").json()["revision"] == before["revision"]


def test_excel_import_uses_expected_revision_and_rejects_stale_upload(tmp_path: Path) -> None:
    client, _ = isolated_client(tmp_path)
    with client:
        before = client.get("/api/questions").json()
        assert client.put("/api/questions", json=put_payload(before, title="Cambio previo")).status_code == 200

        stale = client.post(
            "/api/questions/import",
            params={"expected_revision": before["revision"], "filename": "stale.xlsx"},
            content=minimal_xlsx(),
        )
        assert stale.status_code == 409
        assert stale.json()["detail"]["code"] == "revision_conflict"


def test_excel_import_read_only_error_is_explicit_and_does_not_change_bank(tmp_path: Path) -> None:
    client, _ = isolated_client(tmp_path, writable=False)
    with client:
        before = client.get("/api/questions").json()
        response = client.post(
            "/api/questions/import",
            params={"expected_revision": before["revision"], "filename": "readonly.xlsx"},
            content=minimal_xlsx(),
        )
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "bank_read_only"
        assert client.get("/api/questions").json()["revision"] == before["revision"]
