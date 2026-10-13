from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import StrEnum

from .model import Question


class GameState(StrEnum):
    READY = "ready"
    PLAYING = "playing"
    ANSWERED = "answered"


@dataclass(slots=True)
class GameSession:
    question: Question
    rng: random.Random = field(default_factory=random.Random)
    state: GameState = GameState.READY
    selected_index: int = -1
    hidden_indices: set[int] = field(default_factory=set)
    used_lifelines: set[str] = field(default_factory=set)

    def start(self, *, reset_lifelines: bool = True) -> None:
        self.state = GameState.PLAYING
        self.selected_index = -1
        self.hidden_indices.clear()
        if reset_lifelines:
            self.used_lifelines.clear()

    def answer(self, index: int) -> bool:
        if self.state is not GameState.PLAYING:
            raise RuntimeError("La pregunta no está disponible para responder.")
        if not 0 <= index <= 3:
            raise ValueError("La respuesta debe estar entre A y D.")
        if index in self.hidden_indices:
            raise ValueError("La respuesta fue eliminada por el comodín 50:50.")
        self.selected_index = index
        self.state = GameState.ANSWERED
        return index == self.question.correct_index

    def use_fifty_fifty(self) -> tuple[int, int]:
        if self.state is not GameState.PLAYING:
            raise RuntimeError("El comodín solo puede usarse durante la pregunta.")
        if "fifty" in self.used_lifelines:
            raise RuntimeError("El comodín 50:50 ya fue utilizado.")
        candidates = [
            index for index in range(4) if index != self.question.correct_index
        ]
        removed = tuple(sorted(self.rng.sample(candidates, 2)))
        self.hidden_indices.update(removed)
        self.used_lifelines.add("fifty")
        return removed  # type: ignore[return-value]

    def use_timed_lifeline(self, name: str) -> None:
        if name not in {"phone", "audience"}:
            raise ValueError("Comodín desconocido.")
        if self.state is not GameState.PLAYING:
            raise RuntimeError("El comodín solo puede usarse durante la pregunta.")
        if name in self.used_lifelines:
            raise RuntimeError("El comodín ya fue utilizado.")
        self.used_lifelines.add(name)
