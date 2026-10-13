from __future__ import annotations

import re
import unicodedata
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

from .model import Project, Question, ValidationError


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CELL_REFERENCE = re.compile(r"([A-Z]+)")
REQUIRED_HEADERS = (
    "pregunta",
    "alternativa a",
    "alternativa b",
    "alternativa c",
    "alternativa d",
    "respuesta correcta",
)


class ExcelImportError(RuntimeError):
    """El archivo Excel no cumple el formato de banco de preguntas."""


def _normalized_text(value: object) -> str:
    return " ".join(str(value).strip().split())


def _normalized_header(value: object) -> str:
    text = unicodedata.normalize("NFKD", _normalized_text(value).casefold())
    return "".join(character for character in text if not unicodedata.combining(character))


def _column_index(reference: str) -> int:
    match = CELL_REFERENCE.match(reference.upper())
    if not match:
        raise ExcelImportError(f"Referencia de celda inválida: {reference}.")
    result = 0
    for character in match.group(1):
        result = result * 26 + (ord(character) - ord("A") + 1)
    return result - 1


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return [
        "".join(node.text or "" for node in item.findall(f".//{{{MAIN_NS}}}t"))
        for item in root.findall(f"{{{MAIN_NS}}}si")
    ]


def _questions_sheet_path(archive: zipfile.ZipFile) -> str:
    try:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(
            archive.read("xl/_rels/workbook.xml.rels")
        )
    except KeyError as exc:
        raise ExcelImportError("El archivo Excel no contiene un libro válido.") from exc

    relationship_targets = {
        relation.attrib["Id"]: relation.attrib["Target"]
        for relation in relationships.findall(f"{{{PACKAGE_REL_NS}}}Relationship")
    }
    for sheet in workbook.findall(f".//{{{MAIN_NS}}}sheet"):
        if _normalized_header(sheet.attrib.get("name", "")) != "preguntas":
            continue
        relationship_id = sheet.attrib.get(f"{{{REL_NS}}}id", "")
        target = relationship_targets.get(relationship_id)
        if not target:
            break
        pure_target = PurePosixPath(target.lstrip("/"))
        if pure_target.parts and pure_target.parts[0] == "xl":
            return pure_target.as_posix()
        return (PurePosixPath("xl") / pure_target).as_posix()
    raise ExcelImportError("No se encontró una hoja llamada “Preguntas”.")


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t", "")
    if cell_type == "inlineStr":
        return "".join(
            node.text or "" for node in cell.findall(f".//{{{MAIN_NS}}}t")
        )
    value_node = cell.find(f"{{{MAIN_NS}}}v")
    value = "" if value_node is None else value_node.text or ""
    if cell_type == "s" and value:
        try:
            return shared_strings[int(value)]
        except (ValueError, IndexError) as exc:
            raise ExcelImportError("La tabla de textos del Excel está dañada.") from exc
    return value


def _sheet_rows(
    archive: zipfile.ZipFile,
    sheet_path: str,
    shared_strings: list[str],
) -> list[tuple[int, dict[int, str]]]:
    try:
        root = ET.fromstring(archive.read(sheet_path))
    except KeyError as exc:
        raise ExcelImportError("No fue posible leer la hoja “Preguntas”.") from exc

    rows: list[tuple[int, dict[int, str]]] = []
    for row in root.findall(f".//{{{MAIN_NS}}}row"):
        row_number = int(row.attrib.get("r", len(rows) + 1))
        values: dict[int, str] = {}
        for cell in row.findall(f"{{{MAIN_NS}}}c"):
            reference = cell.attrib.get("r", "")
            values[_column_index(reference)] = _normalized_text(
                _cell_value(cell, shared_strings)
            )
        rows.append((row_number, values))
    return rows


def _header_mapping(
    rows: list[tuple[int, dict[int, str]]],
) -> tuple[int, dict[str, int]]:
    for row_number, values in rows[:20]:
        mapping = {
            _normalized_header(value): column
            for column, value in values.items()
            if value
        }
        if all(header in mapping for header in REQUIRED_HEADERS):
            return row_number, mapping
    headers = ", ".join(REQUIRED_HEADERS)
    raise ExcelImportError(
        f"No se encontraron las columnas obligatorias: {headers}."
    )


def import_project_from_excel(path: str | Path) -> Project:
    excel_path = Path(path)
    if excel_path.suffix.casefold() != ".xlsx":
        raise ExcelImportError("El banco debe ser un archivo Excel .xlsx.")
    if not excel_path.exists():
        raise ExcelImportError("El archivo Excel seleccionado no existe.")

    try:
        with zipfile.ZipFile(excel_path, "r") as archive:
            shared_strings = _shared_strings(archive)
            sheet_path = _questions_sheet_path(archive)
            rows = _sheet_rows(archive, sheet_path, shared_strings)
    except (OSError, zipfile.BadZipFile, ET.ParseError) as exc:
        raise ExcelImportError("El archivo Excel está dañado o incompleto.") from exc

    header_row, mapping = _header_mapping(rows)
    active_column = mapping.get("activa")
    questions: list[Question] = []

    for row_number, values in rows:
        if row_number <= header_row:
            continue
        prompt = values.get(mapping["pregunta"], "")
        answers = tuple(
            values.get(mapping[f"alternativa {letter.casefold()}"], "")
            for letter in "ABCD"
        )
        correct_letter = values.get(mapping["respuesta correcta"], "").upper()
        active = (
            values.get(active_column, "").casefold()
            if active_column is not None
            else "si"
        )

        if not prompt and not any(answers) and not correct_letter:
            continue
        if active in {"no", "n", "false", "0"}:
            continue
        if active not in {"", "si", "sí", "s", "true", "1"}:
            raise ExcelImportError(
                f"Fila {row_number}: la columna Activa debe contener SI o NO."
            )
        if correct_letter not in "ABCD" or len(correct_letter) != 1:
            raise ExcelImportError(
                f"Fila {row_number}: la respuesta correcta debe ser A, B, C o D."
            )
        try:
            question = Question(
                prompt=prompt,
                answers=answers,  # type: ignore[arg-type]
                correct_index="ABCD".index(correct_letter),
            ).normalized()
        except ValidationError as exc:
            raise ExcelImportError(f"Fila {row_number}: {exc}") from exc
        questions.append(question)

    if len(questions) < 4:
        raise ExcelImportError("El banco debe contener al menos 4 preguntas activas.")
    if len(questions) > 12:
        raise ExcelImportError("El banco puede contener como máximo 12 preguntas activas.")
    prompts = [question.prompt.casefold() for question in questions]
    if len(set(prompts)) != len(prompts):
        raise ExcelImportError("El banco contiene preguntas duplicadas.")

    return Project(
        title=f"Banco importado · {excel_path.stem}",
        questions=tuple(questions),
    ).normalized()
