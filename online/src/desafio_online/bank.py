from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Any

from millonario_v3.excel_import import ExcelImportError, import_project_from_excel
from millonario_v3.model import Project, ValidationError
from millonario_v3.storage import (
    ProjectFileError,
    load_project,
    load_project_with_recovery,
    project_directory_is_writable,
    save_project,
)


REQUIRED_QUESTION_COUNT = 12


class BankError(RuntimeError):
    """Error controlado de la capa de banco V4."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _normalized_prompt(value: str) -> str:
    return " ".join(value.casefold().split())


def _project_revision(project: Project) -> str:
    payload = json.dumps(
        project.normalized().to_dict(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_published_project(project: Project) -> Project:
    """Aplica el contrato adicional de publicación de V4 sin modificar V3."""

    try:
        normalized = project.normalized()
    except ValidationError as exc:
        raise BankError("invalid_bank", str(exc)) from exc

    if len(normalized.questions) != REQUIRED_QUESTION_COUNT:
        raise BankError(
            "invalid_bank",
            "El banco publicado de V4 debe contener exactamente 12 preguntas válidas.",
        )

    prompts = [_normalized_prompt(question.prompt) for question in normalized.questions]
    if len(set(prompts)) != len(prompts):
        raise BankError("invalid_bank", "El banco contiene preguntas duplicadas.")

    return normalized


class QuestionBankService:
    """Banco único V4 con revisión optimista y storage histórico `.juego`."""

    def __init__(
        self,
        path: str | Path,
        *,
        seed_path: str | Path | None = None,
        allow_writes: bool = True,
        storage_mode: str = "configured",
    ) -> None:
        self.path = Path(path)
        self.seed_path = Path(seed_path) if seed_path is not None else self.path
        self.allow_writes = bool(allow_writes)
        self.storage_mode = str(storage_mode)
        self._lock = threading.RLock()
        self._ensure_initialized()

    @property
    def writable(self) -> bool:
        return self.allow_writes and project_directory_is_writable(self.path)

    def _ensure_initialized(self) -> None:
        with self._lock:
            if self.path.exists():
                self._load_unlocked()
                return
            if not self.allow_writes:
                raise BankError(
                    "bank_unavailable",
                    "El banco configurado no existe y el almacenamiento está en modo sólo lectura.",
                )
            try:
                seed = validate_published_project(load_project(self.seed_path))
                save_project(self.path, seed, create_backup=False)
            except BankError:
                raise
            except (ProjectFileError, OSError) as exc:
                raise BankError(
                    "bank_unavailable",
                    f"No fue posible inicializar el banco: {exc}",
                ) from exc

    def _load_unlocked(self) -> Project:
        try:
            if self.allow_writes:
                project, _ = load_project_with_recovery(self.path)
            else:
                project = load_project(self.path)
        except ProjectFileError as exc:
            raise BankError("bank_unavailable", str(exc)) from exc
        return validate_published_project(project)

    def load(self) -> Project:
        with self._lock:
            return self._load_unlocked()

    def revision(self) -> str:
        with self._lock:
            return _project_revision(self._load_unlocked())

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            project = self._load_unlocked()
            return self._snapshot_unlocked(project)

    def _snapshot_unlocked(self, project: Project) -> dict[str, Any]:
        return {
            "title": project.title,
            "question_count": len(project.questions),
            "questions": [
                {
                    "prompt": question.prompt,
                    "answers": list(question.answers),
                    "correct_index": question.correct_index,
                }
                for question in project.questions
            ],
            "revision": _project_revision(project),
            "writable": self.writable,
            "storage_mode": self.storage_mode,
        }

    def _require_writable_unlocked(self) -> None:
        if not self.writable:
            raise BankError(
                "bank_read_only",
                "El banco está en modo sólo lectura. Configura almacenamiento persistente antes de publicar cambios.",
            )

    def _check_revision_unlocked(self, expected_revision: str) -> Project:
        current = self._load_unlocked()
        if _project_revision(current) != str(expected_revision).strip():
            raise BankError(
                "revision_conflict",
                "El banco cambió desde que abriste el editor. Recarga antes de guardar para evitar sobrescribir cambios.",
            )
        return current

    def publish(self, project: Project, *, expected_revision: str) -> dict[str, Any]:
        normalized = validate_published_project(project)
        with self._lock:
            self._require_writable_unlocked()
            self._check_revision_unlocked(expected_revision)
            try:
                save_project(self.path, normalized, create_backup=True)
                saved = self._load_unlocked()
            except ProjectFileError as exc:
                raise BankError("bank_write_failed", str(exc)) from exc
            return self._snapshot_unlocked(saved)

    def import_excel(self, path: str | Path, *, expected_revision: str) -> dict[str, Any]:
        with self._lock:
            self._require_writable_unlocked()
            self._check_revision_unlocked(expected_revision)
            try:
                imported = import_project_from_excel(path)
            except ExcelImportError as exc:
                raise BankError("invalid_bank", str(exc)) from exc
            normalized = validate_published_project(imported)
            try:
                save_project(self.path, normalized, create_backup=True)
                saved = self._load_unlocked()
            except ProjectFileError as exc:
                raise BankError("bank_write_failed", str(exc)) from exc
            return self._snapshot_unlocked(saved)
