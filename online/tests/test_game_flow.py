from __future__ import annotations

from pathlib import Path

import pytest

from millonario_v3.participation.models import SubmissionStatus
from millonario_v3.session import SessionState

from desafio_online.registry import RoomRegistry


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROJECT_PATH = REPOSITORY_ROOT / "v3_1" / "projects" / "demo.juego"


def make_room(*, seed: int = 7):
    return RoomRegistry(PROJECT_PATH).create(seed=seed)


def join_people(room, count: int = 4):
    return [
        room.manager.join(f"Persona {index}", f"device-{index:02d}")
        for index in range(count)
    ]


def reach_round_intro(room, people, *, correct_count: int = 2):
    qualifier = room.start_qualifier()
    correct = "ABCD"[room.qualifier_question.question.correct_index]
    wrong = "ABCD"[(room.qualifier_question.question.correct_index + 1) % 4]
    for index, person in enumerate(people):
        result = room.manager.submit_answer(
            token=person.token,
            opening_id=qualifier["opening"]["opening_id"],
            answer=correct if index < correct_count else wrong,
        )
        assert result.status is SubmissionStatus.ACCEPTED
    room.close_qualifier()
    room.begin_player_selection()
    room.confirm_players(room.preselected_ids)
    return list(room.orchestrator.selected_participants)


def answer_active_question(room, people, *, correct: bool = True):
    active = room.active_player_id
    token = next(
        person.token
        for person in people
        if person.participant.participant_id == active
    )
    correct_index = room.question_session.question.correct_index
    answer_index = correct_index if correct else (correct_index + 1) % 4
    result, revealed = room.submit_regular_answer(
        token=token,
        opening_id=room.question_opening_id,
        answer="ABCD"[answer_index],
    )
    assert result["status"] == "accepted"
    assert revealed is True


def test_room_creation_has_the_canonical_twelve_question_plan() -> None:
    room = make_room()
    assert room.state is SessionState.LOBBY_OPEN
    assert len(room.plan_ids) == 12
    assert len(set(room.plan_ids)) == 12
    assert len(room.orchestrator.plan.round_one) == 5
    assert len(room.orchestrator.plan.round_two) == 5
    assert room.orchestrator.plan.reserve.question_id in room.plan_ids


def test_multiple_enrollment_lobby_close_qualifier_ranking_and_selection() -> None:
    room = make_room()
    people = join_people(room, 5)
    room.manager.set_connected(people[4].participant.participant_id, True)
    qualifier = room.start_qualifier()
    assert room.state is SessionState.QUALIFIER_OPEN
    assert qualifier["opening"]["duration_ms"] == 30_000
    assert len(room.manager.current_opening.eligible_ids) == 5

    correct = "ABCD"[room.qualifier_question.question.correct_index]
    wrong = "ABCD"[(room.qualifier_question.question.correct_index + 1) % 4]
    answers = [wrong, correct, correct, correct, wrong]
    for person, answer in zip(people, answers, strict=True):
        room.manager.submit_answer(
            token=person.token,
            opening_id=qualifier["opening"]["opening_id"],
            answer=answer,
        )
    results = room.close_qualifier()
    assert room.state is SessionState.QUALIFIER_RESULTS
    assert results["total"] == 5
    assert [item["alias"] for item in results["ranking"]] == [
        "Persona 1",
        "Persona 2",
        "Persona 3",
    ]
    assert all(item["correct"] for item in results["ranking"])
    assert all(item["received_at"] for item in results["responses"])
    assert all(item["elapsed_ms"] >= 0 for item in results["responses"])
    assert room.preselected_ids == [
        people[1].participant.participant_id,
        people[2].participant.participant_id,
    ]

    room.begin_player_selection()
    selected = list(room.preselected_ids)
    room.confirm_players(selected)
    assert room.state is SessionState.ROUND_INTRO
    assert [room.manager.participants[item].role for item in selected] == [
        "selected",
        "selected",
    ]
    public_id = people[4].participant.participant_id
    assert room.manager.participants[public_id].role == "audience"
    assert room.manager.participants[public_id].connected is True
    assert room.player_snapshot(public_id)["game_role"] == "audience"


@pytest.mark.parametrize("correct_count", [0, 1])
def test_selection_fills_missing_correct_answers_safely(correct_count: int) -> None:
    room = make_room(seed=10 + correct_count)
    people = join_people(room, 4)
    reach_round_intro(room, people, correct_count=correct_count)
    assert len(room.orchestrator.selected_participants) == 2
    assert len(set(room.orchestrator.selected_participants)) == 2


def test_two_complete_rounds_have_five_questions_each() -> None:
    room = make_room()
    people = join_people(room, 4)
    selected = reach_round_intro(room, people)

    for round_index in range(2):
        room.start_round()
        assert room.active_player_id == selected[round_index]
        for question_index in range(5):
            assert room.state is SessionState.QUESTION_ACTIVE
            assert room.question_remaining_ms == 45_000
            answer_active_question(room, people, correct=question_index != 4)
            assert room.state is SessionState.ANSWER_REVEALED
            room.advance_after_answer()
        assert room.state is SessionState.ROUND_SUMMARY
        assert room.orchestrator.scores[round_index] == 4
        room.advance_after_round()

    assert room.state is SessionState.SESSION_SUMMARY
    assert room.orchestrator.scores == [4, 4]


def test_fifty_phone_and_audience_follow_roles_timers_and_limits() -> None:
    room = make_room()
    people = join_people(room, 5)
    selected = reach_round_intro(room, people)
    room.start_round()

    fifty = room.use_fifty()
    assert len(fifty["removed"]) == 2
    assert room.state is SessionState.QUESTION_ACTIVE
    assert all(
        index != room.question_session.question.correct_index
        for index in fifty["removed"]
    )
    active_player = next(
        person
        for person in people
        if person.participant.participant_id == room.active_player_id
    )
    mobile = room.player_snapshot(active_player.participant.participant_id)
    allowed = mobile["question"]["opening"]["allowed_answers"]
    assert len(allowed) == 2
    assert set(allowed) == {
        letter for index, letter in enumerate("ABCD") if index not in fifty["removed"]
    }
    removed_answer = "ABCD"[fifty["removed"][0]]
    rejected, revealed = room.submit_regular_answer(
        token=active_player.token,
        opening_id=room.question_opening_id,
        answer=removed_answer,
    )
    assert rejected["status"] == "forbidden"
    assert revealed is False
    with pytest.raises(Exception, match="pregunta actual"):
        room.use_fifty()

    phone = room.start_timed_lifeline("phone")
    assert room.state is SessionState.LIFELINE_ACTIVE
    assert phone["opening"]["duration_ms"] == 15_000
    room.finish_timed_lifeline()
    assert room.state is SessionState.QUESTION_ACTIVE

    audience = room.start_timed_lifeline("audience")
    assert audience["opening"]["duration_ms"] == 15_000
    public = next(
        person for person in people
        if person.participant.participant_id not in selected
    )
    player = next(
        person for person in people
        if person.participant.participant_id in selected
    )
    public_result = room.manager.submit_answer(
        token=public.token,
        opening_id=room.lifeline_opening_id,
        answer="B",
    )
    player_result = room.manager.submit_answer(
        token=player.token,
        opening_id=room.lifeline_opening_id,
        answer="B",
    )
    assert public_result.status is SubmissionStatus.ACCEPTED
    assert player_result.status is SubmissionStatus.FORBIDDEN
    finished = room.finish_timed_lifeline()
    assert finished["audience_results"]["counts"] == [0, 1, 0, 0]
    assert room.state is SessionState.QUESTION_ACTIVE


def test_three_uses_per_lifeline_are_allowed_but_fourth_is_rejected() -> None:
    room = make_room()
    people = join_people(room, 4)
    reach_round_intro(room, people)
    room.start_round()
    for use_number in range(3):
        room.start_timed_lifeline("phone")
        room.finish_timed_lifeline()
        answer_active_question(room, people)
        room.advance_after_answer()
        if use_number < 2:
            assert room.state is SessionState.QUESTION_ACTIVE
    assert room.state is SessionState.QUESTION_ACTIVE
    with pytest.raises(Exception, match="máximo de tres"):
        room.start_timed_lifeline("phone")


def test_late_answers_are_rejected_by_server_timers() -> None:
    room = make_room()
    people = join_people(room, 4)
    qualifier = room.start_qualifier(duration_ms=1_000)
    room.manager.current_opening.opened_perf -= 2
    late = room.manager.submit_answer(
        token=people[0].token,
        opening_id=qualifier["opening"]["opening_id"],
        answer="A",
    )
    assert late.status is SubmissionStatus.LATE
    room.close_qualifier()
    room.begin_player_selection()
    room.confirm_players(room.preselected_ids)
    room.start_round(duration_ms=1_000)
    room.question_started_perf -= 2
    active = next(
        person for person in people
        if person.participant.participant_id == room.active_player_id
    )
    result, revealed = room.submit_regular_answer(
        token=active.token,
        opening_id=room.question_opening_id,
        answer="A",
    )
    assert result["status"] == "late"
    assert revealed is False
    room.timeout_question()
    assert room.question_result["timed_out"] is True


def test_reconnection_keeps_role_and_replay_keeps_tokens_and_room() -> None:
    room = make_room(seed=41)
    people = join_people(room, 4)
    selected = reach_round_intro(room, people)
    room.start_round()
    selected_person = next(
        person for person in people
        if person.participant.participant_id == selected[0]
    )
    room.manager.set_connected(selected[0], False)
    reconnected = room.manager.reconnect(selected_person.token)
    assert reconnected.role == "selected"
    assert room.player_snapshot(selected[0])["is_active_player"] is True

    for round_index in range(2):
        if round_index == 1:
            room.start_round()
        while room.state is SessionState.QUESTION_ACTIVE:
            answer_active_question(room, people)
            room.advance_after_answer()
        assert room.state is SessionState.ROUND_SUMMARY
        room.advance_after_round()
    assert room.state is SessionState.SESSION_SUMMARY

    room_code = room.room_code
    old_plan = room.plan_ids
    room.repeat()
    assert room.room_code == room_code
    assert room.state is SessionState.LOBBY_OPEN
    assert len(room.plan_ids) == 12
    assert room.plan_ids != old_plan
    assert room.manager.authenticate(selected_person.token).participant_id == selected[0]
    assert all(person.role == "audience" for person in room.manager.participants.values())
