from __future__ import annotations

import io
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from millonario_v3.model import Project, Question

from .bank import BankError, QuestionBankService


MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_ZIP_ENTRIES = 256
MAX_UNCOMPRESSED_BYTES = 12 * 1024 * 1024
MAX_ZIP_ENTRY_BYTES = 8 * 1024 * 1024
REVISION_PATTERN = r"^[0-9a-f]{64}$"


class QuestionBody(BaseModel):
    prompt: str = Field(min_length=1, max_length=320)
    answers: list[str] = Field(min_length=4, max_length=4)
    correct_index: int = Field(ge=0, le=3)


class QuestionBankBody(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    questions: list[QuestionBody] = Field(min_length=12, max_length=12)
    expected_revision: str = Field(pattern=REVISION_PATTERN)


def bank_http_error(error: BankError) -> HTTPException:
    status = {
        "revision_conflict": 409,
        "invalid_bank": 422,
        "bank_read_only": 503,
        "bank_unavailable": 503,
        "bank_write_failed": 503,
    }.get(error.code, 400)
    return HTTPException(
        status_code=status,
        detail={"code": error.code, "message": str(error)},
    )


def _project_from_body(body: QuestionBankBody) -> Project:
    return Project(
        title=body.title,
        questions=tuple(
            Question(
                prompt=item.prompt,
                answers=tuple(item.answers),  # type: ignore[arg-type]
                correct_index=item.correct_index,
            )
            for item in body.questions
        ),
    )


def _content_length(request: Request) -> int | None:
    raw = request.headers.get("content-length", "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _validate_xlsx_payload(filename: str, payload: bytes) -> None:
    if not filename.casefold().endswith(".xlsx"):
        raise HTTPException(status_code=422, detail="El archivo debe tener extensión .xlsx.")
    if not payload:
        raise HTTPException(status_code=422, detail="El archivo Excel está vacío.")
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="El archivo Excel supera el máximo de 2 MB.")

    try:
        with zipfile.ZipFile(io.BytesIO(payload), "r") as archive:
            entries = archive.infolist()
            if len(entries) > MAX_ZIP_ENTRIES:
                raise HTTPException(status_code=422, detail="El archivo Excel contiene demasiados elementos internos.")
            if any(item.flag_bits & 0x1 for item in entries):
                raise HTTPException(status_code=422, detail="No se aceptan archivos Excel cifrados.")
            if any(item.file_size > MAX_ZIP_ENTRY_BYTES for item in entries):
                raise HTTPException(status_code=422, detail="El archivo Excel contiene un elemento interno demasiado grande.")
            if sum(item.file_size for item in entries) > MAX_UNCOMPRESSED_BYTES:
                raise HTTPException(status_code=422, detail="El archivo Excel descomprimido supera el límite permitido.")
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=422, detail="El archivo .xlsx está dañado o no es un libro Excel válido.") from exc


def build_questions_router(
    bank: QuestionBankService,
    *,
    require_admin: Callable[..., str],
    template_path: str | Path,
) -> APIRouter:
    router = APIRouter(dependencies=[Depends(require_admin)])
    template = Path(template_path)

    @router.get("/api/questions")
    async def get_questions() -> dict[str, Any]:
        try:
            return bank.snapshot()
        except BankError as error:
            raise bank_http_error(error) from error

    @router.put("/api/questions")
    async def put_questions(body: QuestionBankBody) -> dict[str, Any]:
        try:
            return bank.publish(
                _project_from_body(body),
                expected_revision=body.expected_revision,
            )
        except BankError as error:
            raise bank_http_error(error) from error

    @router.get("/api/questions/template")
    async def download_questions_template() -> FileResponse:
        if not template.exists():
            raise HTTPException(status_code=503, detail="La plantilla Excel no está disponible.")
        return FileResponse(
            template,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="Banco_preguntas_V2.xlsx",
        )

    @router.post("/api/questions/import")
    async def import_questions(
        request: Request,
        expected_revision: str = Query(pattern=REVISION_PATTERN),
        filename: str = Query(min_length=1, max_length=200),
    ) -> dict[str, Any]:
        declared_length = _content_length(request)
        if declared_length is not None and declared_length > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="El archivo Excel supera el máximo de 2 MB.")

        payload = await request.body()
        _validate_xlsx_payload(filename, payload)

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", suffix=".xlsx", delete=False) as temporary:
                temporary.write(payload)
                temporary_path = Path(temporary.name)
            try:
                return bank.import_excel(
                    temporary_path,
                    expected_revision=expected_revision,
                )
            except BankError as error:
                raise bank_http_error(error) from error
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    return router
