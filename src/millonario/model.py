from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any


class ValidationError(ValueError):
    """El contenido del proyecto no cumple el contrato de la aplicación."""


@dataclass(frozen=True, slots=True)
class Question:
    prompt: str
    answers: tuple[str, str, str, str]
    correct_index: int

    def validate(self) -> None:
        if not self.prompt.strip():
            raise ValidationError("La pregunta no puede estar vacía.")
        if len(self.prompt.strip()) > 320:
            raise ValidationError("La pregunta no puede superar 320 caracteres.")
        if len(self.answers) != 4:
            raise ValidationError("Cada pregunta debe tener exactamente cuatro respuestas.")
        cleaned = [answer.strip() for answer in self.answers]
        if any(not answer for answer in cleaned):
            raise ValidationError("Las cuatro respuestas son obligatorias.")
        if any(len(answer) > 140 for answer in cleaned):
            raise ValidationError("Cada respuesta puede contener hasta 140 caracteres.")
        if len({answer.casefold() for answer in cleaned}) != 4:
            raise ValidationError("Las cuatro respuestas deben ser diferentes.")
        if not 0 <= self.correct_index <= 3:
            raise ValidationError("La respuesta correcta debe estar entre A y D.")

    def normalized(self) -> "Question":
        question = Question(
            prompt=self.prompt.strip(),
            answers=tuple(answer.strip() for answer in self.answers),  # type: ignore[arg-type]
            correct_index=int(self.correct_index),
        )
        question.validate()
        return question

    def to_dict(self) -> dict[str, Any]:
        normalized = self.normalized()
        return {
            "pregunta": normalized.prompt,
            "respuestas": list(normalized.answers),
            "correcta": normalized.correct_index,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Question":
        try:
            answers = tuple(str(item) for item in data["respuestas"])
            question = cls(
                prompt=str(data["pregunta"]),
                answers=answers,  # type: ignore[arg-type]
                correct_index=int(data["correcta"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError("La estructura de una pregunta es inválida.") from exc
        return question.normalized()


@dataclass(frozen=True, slots=True)
class Project:
    title: str
    questions: tuple[Question, ...]
    version: int = 1

    def validate(self) -> None:
        if self.version != 1:
            raise ValidationError(f"Versión de proyecto no compatible: {self.version}.")
        if not self.title.strip():
            raise ValidationError("El proyecto debe tener un nombre.")
        if not self.questions:
            raise ValidationError("El proyecto debe contener al menos una pregunta.")
        if len(self.questions) > 12:
            raise ValidationError("El banco puede contener como máximo 12 preguntas.")
        for question in self.questions:
            question.validate()

    def normalized(self) -> "Project":
        project = Project(
            title=self.title.strip(),
            questions=tuple(question.normalized() for question in self.questions),
            version=self.version,
        )
        project.validate()
        return project

    def replace_question(self, index: int, question: Question) -> "Project":
        if not 0 <= index < len(self.questions):
            raise IndexError("La pregunta seleccionada no existe.")
        updated = list(self.questions)
        updated[index] = question.normalized()
        return replace(self, questions=tuple(updated)).normalized()

    def add_question(self, question: Question, index: int | None = None) -> "Project":
        updated = list(self.questions)
        if len(updated) >= 12:
            raise ValidationError("El banco puede contener como máximo 12 preguntas.")
        insertion_index = len(updated) if index is None else index
        if not 0 <= insertion_index <= len(updated):
            raise IndexError("La posición de la nueva pregunta no es válida.")
        updated.insert(insertion_index, question.normalized())
        return replace(self, questions=tuple(updated)).normalized()

    def delete_question(self, index: int) -> "Project":
        if len(self.questions) == 1:
            raise ValidationError("El proyecto debe conservar al menos una pregunta.")
        if not 0 <= index < len(self.questions):
            raise IndexError("La pregunta seleccionada no existe.")
        updated = list(self.questions)
        del updated[index]
        return replace(self, questions=tuple(updated)).normalized()

    def move_question(self, index: int, destination: int) -> "Project":
        if not 0 <= index < len(self.questions):
            raise IndexError("La pregunta seleccionada no existe.")
        if not 0 <= destination < len(self.questions):
            raise IndexError("La posición de destino no es válida.")
        updated = list(self.questions)
        question = updated.pop(index)
        updated.insert(destination, question)
        return replace(self, questions=tuple(updated)).normalized()

    def to_dict(self) -> dict[str, Any]:
        normalized = self.normalized()
        return {
            "formato": "millonario-educativo",
            "version": normalized.version,
            "titulo": normalized.title,
            "preguntas": [question.to_dict() for question in normalized.questions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Project":
        if data.get("formato") != "millonario-educativo":
            raise ValidationError("El archivo no corresponde a este juego.")
        try:
            project = cls(
                title=str(data["titulo"]),
                questions=tuple(Question.from_dict(item) for item in data["preguntas"]),
                version=int(data["version"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, ValidationError):
                raise
            raise ValidationError("La estructura del proyecto es inválida.") from exc
        return project.normalized()


def default_project() -> Project:
    return Project(
        title="Preguntas de prueba",
        questions=(
            Question(
                prompt=(
                    "¿Qué función podrá realizar un EDN con Acreditación RIC "
                    "cuando un cliente solicite invertir en FFMM “Aporte”?"
                ),
                answers=(
                    "Invertir en la oferta de Fondos Mutuos desde PU",
                    "Invertir en cualquier FFMM.",
                    "Asesorar al cliente",
                    "Todas las anteriores",
                ),
                correct_index=0,
            ),
            Question(
                prompt="¿A qué perfil de cliente estaría recomendado el fondo Liquidez ASG?",
                answers=(
                    "Conservador, plazo hasta 30 días",
                    "Moderado, plazo de inversión hasta 6 meses.",
                    "Conservador, plazo 6 a 12 meses de inversión.",
                    "Conservador, plazo de inversión mayor a un año.",
                ),
                correct_index=0,
            ),
            Question(
                prompt=(
                    "Si un cliente recibe una orden de pago en USD, no quiere hacer "
                    "el cambio total a CLP y desea guardar dólares en un Fondo Mutuo "
                    "en USD, ¿qué corresponde realizar?"
                ),
                answers=(
                    "Intento tomar la inversión desde OWP",
                    "Solicito apoyo a la Mesa de Soporte Comercial",
                    "Lo paso con el agente o con el JP",
                    "Le comento que no tenemos disponible ese tipo de Fondo Mutuo",
                ),
                correct_index=1,
            ),
            Question(
                prompt="Operativamente, ¿cuál es la pestaña a seleccionar para invertir en FFMM (OWP)?",
                answers=(
                    "Invertir en Fondo Mutuo",
                    "Solicitudes de Inversión",
                    "Simular Alternativa de inversión",
                    "Ninguna de las anteriores.",
                ),
                correct_index=2,
            ),
            Question(
                prompt=(
                    "¿Qué se debe hacer si un cliente solicita un Fondo Mutuo que "
                    "no está dentro de la oferta simplificada de Fondos (PU)?"
                ),
                answers=(
                    "Le digo que la opción disponible es la única por el momento",
                    "Comento a mi Agente o JP la inquietud del cliente",
                    "Le comento que el mercado está muy riesgoso para otro tipo de fondos",
                    "Derivo al cliente con la Mesa de Soporte Comercial",
                ),
                correct_index=3,
            ),
            Question(
                prompt="¿Qué funciones podrá realizar un EDN sin ningún tipo de acreditación?",
                answers=(
                    "Entregar folletos informativos de FFMM",
                    "Entregar cartolas FFMM y APV",
                    "Realizar rescates",
                    "Todas las anteriores",
                ),
                correct_index=3,
            ),
        ),
    ).normalized()
