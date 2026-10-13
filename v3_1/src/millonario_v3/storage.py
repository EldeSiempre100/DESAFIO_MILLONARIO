from __future__ import annotations

import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from .model import Project, ValidationError


MANIFEST_NAME = "proyecto.json"
BACKUP_SUFFIXES = (".bak", ".bak2", ".bak3")


class ProjectFileError(RuntimeError):
    """No fue posible abrir o guardar un archivo .juego."""


def backup_paths(path: str | Path) -> tuple[Path, ...]:
    project_path = Path(path)
    return tuple(
        project_path.with_suffix(project_path.suffix + suffix)
        for suffix in BACKUP_SUFFIXES
    )


def load_project(path: str | Path) -> Project:
    project_path = Path(path)
    if not project_path.exists():
        raise ProjectFileError(f"No existe el archivo: {project_path}")
    try:
        with zipfile.ZipFile(project_path, "r") as archive:
            raw = archive.read(MANIFEST_NAME)
        data = json.loads(raw.decode("utf-8"))
        return Project.from_dict(data)
    except (OSError, zipfile.BadZipFile, KeyError, json.JSONDecodeError, UnicodeError) as exc:
        raise ProjectFileError("El archivo .juego está dañado o incompleto.") from exc
    except ValidationError as exc:
        raise ProjectFileError(str(exc)) from exc


def load_project_with_recovery(path: str | Path) -> tuple[Project, Path | None]:
    project_path = Path(path)
    try:
        return load_project(project_path), None
    except ProjectFileError as original_error:
        for backup_path in backup_paths(project_path):
            if not backup_path.exists():
                continue
            try:
                project = load_project(backup_path)
                save_project(project_path, project, create_backup=False)
                return project, backup_path
            except ProjectFileError:
                continue
        raise original_error


def project_directory_is_writable(path: str | Path) -> bool:
    project_path = Path(path)
    directory = project_path.parent
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=".writable.",
            suffix=".tmp",
            dir=directory,
            delete=True,
        ):
            pass
    except OSError:
        return False
    return True


def save_project(
    path: str | Path,
    project: Project,
    *,
    create_backup: bool = True,
) -> Path:
    normalized = project.normalized()
    project_path = Path(path)
    if project_path.suffix.lower() != ".juego":
        project_path = project_path.with_suffix(".juego")
    project_path.parent.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(
        normalized.to_dict(),
        ensure_ascii=False,
        indent=2,
        sort_keys=False,
    ).encode("utf-8")

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=".tmp",
            prefix=f".{project_path.name}.",
            dir=project_path.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)

        with zipfile.ZipFile(
            temporary_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            archive.writestr(MANIFEST_NAME, payload)

        # Verifica el contenedor antes de sustituir el proyecto válido.
        load_project(temporary_path)

        if create_backup and project_path.exists():
            primary, secondary, tertiary = backup_paths(project_path)
            if secondary.exists():
                shutil.copy2(secondary, tertiary)
            if primary.exists():
                shutil.copy2(primary, secondary)
            shutil.copy2(project_path, primary)

        os.replace(temporary_path, project_path)
        temporary_path = None
        return project_path
    except (OSError, zipfile.BadZipFile, ValidationError, ProjectFileError) as exc:
        raise ProjectFileError(f"No se pudo guardar el proyecto: {exc}") from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
