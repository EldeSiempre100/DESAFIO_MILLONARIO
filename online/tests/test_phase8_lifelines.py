from __future__ import annotations

from pathlib import Path

import pytest

from millonario_v3.participation.models import SubmissionStatus
from millonario_v3.participation.room import RoomError
from millonario_v3.session import SessionState

from desafio_online.registry import LIFELINE_DURATION_MS, QUESTION_DURATION_MS, RoomRegistry


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROJECT_PATH = REPOSITORY_ROOT / "v3_1" / "projects" / "demo.juego"


def make_room(*, seed: int = 118):
    return RoomRegistry(PROJECT_PATH).create(seed=seed)


def join_people(room, count: int = 5):
    return [
        room.manager.join(f"Fase8 {index}", f"phase8-device-{index:02d}")
        for index in range(count)
    ]


def reach_question(room, people):
    qualifier = room.start_qualifier()
    correct = "ABCD"[room.qualifier_question.question.correct_index]
    for person in people:
        result = room.manager.submit_answer(
            token=person.token,
            opening_id=qualifier["opening"]["opening_id"],
            answer=correct,
        )
        assert result.status is SubmissionStatus.ACCEPTED
    room.close_qualifier()
    room.begin_player_selection()
    room.confirm_players(room.preselected_ids)
    room.start_round()


def active_person(room, people):
    return next(
        person
        for person in people
        if person.participant.participant_id == room.active_player_id
    )


def public_people(room, people):
    selected = set(room.orchestrator.selected_participants)
    return [
        person
        for person in people
        if person.participant.participant_id not in selected
    ]


def test_fifty_fifty_updates_allowed_answers_and_server_rejects_removed_letter() -> None:
    room = make_room()
    people = join_people(room)
    reach_question(room, people)

    payload = room.use_fifty()
    removed = payload["removed"]
    correct_index = room.question_session.question.correct_index

    assert len(removed) == 2
    assert correct_index not in removed
    assert len(set(removed)) == 2
    assert room.state is SessionState.QUESTION_ACTIVE

    mobile = room.player_snapshot(active_person(room, people).participant.participant_id)
    allowed = mobile["question"]["opening"]["allowed_answers"]
    assert set(allowed) == {
        letter for index, letter in enumerate("ABCD") if index not in removed
    }

    rejected, revealed = room.submit_regular_answer(
        token=active_person(room, people).token,
        opening_id=room.question_opening_id,
        answer="ABCD"[removed[0]],
    )
    assert rejected["status"] == "forbidden"
    assert revealed is False

    with pytest.raises(RoomError, match="pregunta actual"):
        room.use_fifty()


def test_phone_lifeline_freezes_question_timer_for_fifteen_seconds_window() -> None:
    room = make_room(seed=119)
    people = join_people(room)
    reach_question(room, people)

    room.question_started_perf -= 7
    phone = room.start_timed_lifeline("phone")
    paused_remaining = room.question_remaining_ms

    assert room.state is SessionState.LIFELINE_ACTIVE
    assert room.active_lifeline == "phone"
    assert phone["opening"]["duration_ms"] == LIFELINE_DURATION_MS
    assert room.question_started_perf == 0
    assert QUESTION_DURATION_MS - 8_500 <= paused_remaining <= QUESTION_DURATION_MS - 6_000

    room.finish_timed_lifeline(expected_opening_id=room.lifeline_opening_id)

    assert room.state is SessionState.QUESTION_ACTIVE
    assert room.active_lifeline is None
    assert room.question_remaining_ms == paused_remaining
    assert room.question_started_perf > 0


def test_audience_lifeline_excludes_players_aggregates_votes_and_returns_to_question() -> None:
    room = make_room(seed=120)
    people = join_people(room, 5)
    reach_question(room, people)

    audience = room.start_timed_lifeline("audience")
    publics = public_people(room, people)
    selected_ids = set(room.orchestrator.selected_participants)

    assert audience["opening"]["duration_ms"] == LIFELINE_DURATION_MS
    assert audience["opening"]["allowed_answers"] == list("ABCD")
    assert room.state is SessionState.LIFELINE_ACTIVE

    for person in people:
        mobile = room.player_snapshot(person.participant.participant_id)
        if person.participant.participant_id in selected_ids:
            assert mobile["question"] is None
        else:
            assert mobile["question"]["opening"]["type"] == "audience"
            assert mobile["question"]["opening"]["allowed_answers"] == list("ABCD")

    for person, answer in zip(publics, ("A", "B", "B"), strict=True):
        result = room.manager.submit_answer(
            token=person.token,
            opening_id=room.lifeline_opening_id,
            answer=answer,
        )
        assert result.status is SubmissionStatus.ACCEPTED

    selected = next(person for person in people if person.participant.participant_id in selected_ids)
    forbidden = room.manager.submit_answer(
        token=selected.token,
        opening_id=room.lifeline_opening_id,
        answer="D",
    )
    assert forbidden.status is SubmissionStatus.FORBIDDEN

    finished = room.finish_timed_lifeline(expected_opening_id=room.lifeline_opening_id)

    assert room.state is SessionState.QUESTION_ACTIVE
    assert finished["audience_results"]["counts"] == [1, 2, 0, 0]
    assert finished["audience_results"]["percentages"] == [33, 67, 0, 0]
    assert finished["audience_results"]["total"] == 3
    assert room.lifeline_payload()["audience_results"]["counts"] == [1, 2, 0, 0]
    for person in publics:
        assert room.player_snapshot(person.participant.participant_id)["question"] is None


def test_phase8_audio_policy_is_idempotent_and_does_not_replay_transition_after_lifelines() -> None:
    policy = (REPOSITORY_ROOT / "online" / "static" / "phase4_audio.js").read_text(encoding="utf-8")

    assert "eventId > previousId" in policy
    assert "sessionStorage.setItem(storageKey, String(eventId))" in policy

    lifeline_started = policy.split('name === "lifeline_started"', 1)[1].split(
        'name === "lifeline_finished"', 1
    )[0]
    assert 'gameAudio.playVoice(data.last_event.lifeline === "phone" ? "call" : "audience")' in lifeline_started
    assert "stopMusic" not in lifeline_started
    assert "cancelQuestionSequence" not in lifeline_started

    lifeline_finished = policy.split('name === "lifeline_finished"', 1)[1].split(
        "AMBIENT_EVENTS.has(name)", 1
    )[0]
    assert 'gameAudio.startMusic("question")' in lifeline_finished
    assert "beginQuestionSequence" not in lifeline_finished
    assert 'gameAudio.play("transition")' not in lifeline_finished
    assert 'gameAudio.startMusic("transition")' not in lifeline_finished
