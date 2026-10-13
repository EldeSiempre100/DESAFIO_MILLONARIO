from __future__ import annotations

import hashlib
import json
import os
import random
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .model import Question


@dataclass(frozen=True, slots=True)
class RoundSelection:
    questions: tuple[Question, ...]
    round_number: int
    repeated_count: int


def question_fingerprint(question: Question) -> str:
    normalized = question.normalized()
    payload = "\n".join(
        (
            normalized.prompt.casefold(),
            *(answer.casefold() for answer in normalized.answers),
            str(normalized.correct_index),
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class RoundSelector:
    def __init__(
        self,
        history_path: str | Path,
        *,
        rng: random.Random | None = None,
    ) -> None:
        self.history_path = Path(history_path)
        self.rng = rng or random.Random()

    def _load(self) -> tuple[list[str], int]:
        try:
            data = json.loads(self.history_path.read_text(encoding="utf-8"))
            if int(data.get("version", 0)) != 1:
                return [], 0
            recent = [
                str(item)
                for item in data.get("recientes", [])
                if isinstance(item, str)
            ]
            round_number = max(0, int(data.get("ronda", 0)))
            return recent, round_number
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return [], 0

    def _save(self, recent: list[str], round_number: int) -> None:
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {
                "version": 1,
                "ronda": round_number,
                "recientes": recent,
            },
            ensure_ascii=False,
            indent=2,
        )
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                prefix=f".{self.history_path.name}.",
                suffix=".tmp",
                dir=self.history_path.parent,
                delete=False,
            ) as temporary:
                temporary.write(payload)
                temporary_path = Path(temporary.name)
            os.replace(temporary_path, self.history_path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def reset(self) -> None:
        try:
            self.history_path.unlink(missing_ok=True)
        except OSError:
            pass

    def select(
        self,
        questions: tuple[Question, ...],
        *,
        count: int = 4,
    ) -> RoundSelection:
        if not questions:
            raise ValueError("No existen preguntas para iniciar una ronda.")
        round_size = min(max(1, count), len(questions))
        fingerprints = [question_fingerprint(question) for question in questions]
        by_fingerprint = dict(zip(fingerprints, questions, strict=True))

        stored_recent, stored_round = self._load()
        recent: list[str] = []
        for fingerprint in stored_recent:
            if fingerprint in by_fingerprint and fingerprint not in recent:
                recent.append(fingerprint)

        available = [
            fingerprint for fingerprint in fingerprints if fingerprint not in recent
        ]
        self.rng.shuffle(available)
        selected = available[:round_size]
        repeated_count = 0

        if len(selected) < round_size:
            repeated_candidates = [
                fingerprint
                for fingerprint in recent
                if fingerprint not in selected
            ]
            needed = round_size - len(selected)
            selected.extend(repeated_candidates[:needed])
            repeated_count = min(needed, len(repeated_candidates))

        for fingerprint in selected:
            if fingerprint in recent:
                recent.remove(fingerprint)
            recent.append(fingerprint)

        round_number = stored_round + 1
        try:
            self._save(recent, round_number)
        except OSError:
            # En una unidad de solo lectura el juego sigue funcionando,
            # aunque no pueda recordar la ronda para el siguiente inicio.
            pass
        return RoundSelection(
            questions=tuple(by_fingerprint[fingerprint] for fingerprint in selected),
            round_number=round_number,
            repeated_count=repeated_count,
        )
