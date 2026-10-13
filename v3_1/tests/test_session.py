from __future__ import annotations

import pytest

from millonario_v3.model import Project, Question
from millonario_v3.session import (
    QuestionPlan,
    SessionError,
    SessionOrchestrator,
    SessionState,
)


def make_project(count: int = 12) -> Project:
    return Project(
        title="Banco de prueba",
        questions=tuple(
            Question(
                prompt=f"Pregunta {index}",
                answers=(
                    f"A {index}",
                    f"B {index}",
                    f"C {index}",
                    f"D {index}",
                ),
                correct_index=index % 4,
            )
            for index in range(count)
        ),
    ).normalized()


def test_question_plan_uses_twelve_questions_without_repetition() -> None:
    plan = QuestionPlan.create(make_project(), seed=42)
    assert len(plan.round_one) == 5
    assert len(plan.round_two) == 5
    assert len(plan.all_ids) == 12
    assert len(set(plan.all_ids)) == 12


def test_question_plan_requires_exactly_twelve() -> None:
    with pytest.raises(SessionError, match="exactamente 12"):
        QuestionPlan.create(make_project(11), seed=1)


def test_full_two_round_flow_and_lifeline_limits() -> None:
    session = SessionOrchestrator()
    session.begin(make_project(), seed=7)
    session.lobby_opened()
    session.lock_lobby()
    session.prepare_qualifier()
    session.open_qualifier()
    session.qualifier_results()
    session.begin_player_selection()
    session.select_players(["p1", "p2"])

    for round_index in range(2):
        assert session.state is SessionState.ROUND_INTRO
        for question_index in range(5):
            session.start_round_question()
            assert session.current_question.question.prompt
            if question_index < 3:
                assert session.use_lifeline("audience") == question_index + 1
                session.finish_lifeline()
            session.reveal_answer(correct=True)
            complete = session.advance_after_answer()
            assert complete is (question_index == 4)
        assert session.scores[round_index] == 5
        finished = session.advance_after_round()
        assert finished is (round_index == 1)

    assert session.state is SessionState.SESSION_SUMMARY


def test_same_lifeline_cannot_be_used_twice_on_one_question() -> None:
    session = SessionOrchestrator()
    session.begin(make_project(), seed=7)
    session.lobby_opened()
    session.lock_lobby()
    session.prepare_qualifier()
    session.open_qualifier()
    session.qualifier_results()
    session.begin_player_selection()
    session.select_players(["p1", "p2"])
    session.start_round_question()
    session.use_lifeline("phone")
    session.finish_lifeline()
    with pytest.raises(SessionError, match="pregunta actual"):
        session.use_lifeline("phone")
