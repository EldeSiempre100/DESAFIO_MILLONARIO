from __future__ import annotations

from pathlib import Path

from millonario_v3.participation.models import SubmissionStatus
from millonario_v3.session import SessionState

from desafio_online.registry import QUESTION_DURATION_MS, RoomRegistry


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROJECT_PATH = REPOSITORY_ROOT / "v3_1" / "projects" / "demo.juego"


def make_room(*, seed: int = 219):
    return RoomRegistry(PROJECT_PATH).create(seed=seed)


def join_people(room, count: int = 4):
    avatars = ("star", "creative", "strategist", "curious")
    return [
        room.manager.join(
            f"Replay {index}",
            f"phase9-device-{index:02d}",
            avatars[index % len(avatars)],
        )
        for index in range(count)
    ]


def reach_round_intro(room, people):
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


def answer_active_question(room, people):
    active = next(
        person
        for person in people
        if person.participant.participant_id == room.active_player_id
    )
    correct = "ABCD"[room.question_session.question.correct_index]
    result, revealed = room.submit_regular_answer(
        token=active.token,
        opening_id=room.question_opening_id,
        answer=correct,
    )
    assert result["status"] == "accepted"
    assert revealed is True


def finish_short_session(room, people, *, questions_per_round: int | None = 1):
    if questions_per_round is not None:
        room.configure_questions_per_round(questions_per_round)
    reach_round_intro(room, people)
    used_lifelines = False
    for round_index in range(2):
        room.start_round()
        while room.state is SessionState.QUESTION_ACTIVE:
            if not used_lifelines:
                room.use_fifty()
                room.start_timed_lifeline("phone")
                room.finish_timed_lifeline()
                used_lifelines = True
            answer_active_question(room, people)
            room.advance_after_answer()
        assert room.state is SessionState.ROUND_SUMMARY
        room.advance_after_round()
        if round_index == 0:
            assert room.state is SessionState.ROUND_INTRO
    assert room.state is SessionState.SESSION_SUMMARY


def test_replay_keeps_room_identity_tokens_aliases_avatars_and_devices() -> None:
    room = make_room()
    people = join_people(room)
    identity_before = {
        person.participant.participant_id: {
            "token": person.token,
            "alias": person.participant.alias,
            "avatar": person.participant.avatar,
            "device_id": person.participant.device_id,
        }
        for person in people
    }
    room_code = room.room_code
    finish_short_session(room, people)

    room.repeat()

    assert room.room_code == room_code
    assert room.state is SessionState.LOBBY_OPEN
    assert set(room.manager.participants) == set(identity_before)
    for participant_id, before in identity_before.items():
        participant = room.manager.authenticate(before["token"])
        assert participant.participant_id == participant_id
        assert participant.alias == before["alias"]
        assert participant.avatar == before["avatar"]
        assert participant.device_id == before["device_id"]
        assert participant.role == "audience"


def test_replay_resets_game_state_scores_responses_lifelines_and_timers() -> None:
    room = make_room(seed=220)
    people = join_people(room)
    finish_short_session(room, people)
    old_game_id = room.game_id
    old_plan = room.plan_ids

    room.repeat()

    assert room.game_id != old_game_id
    assert room.state is SessionState.LOBBY_OPEN
    assert room.manager.status.value == "open"
    assert room.manager.current_opening is None
    assert room.orchestrator.selected_participants == ()
    assert room.preselected_ids == []
    assert room.selection_pool == []
    assert room.qualifier_results_data is None
    assert room.orchestrator.scores == [0, 0]
    assert room.orchestrator.lifeline_uses == [
        {"fifty": 0, "phone": 0, "audience": 0},
        {"fifty": 0, "phone": 0, "audience": 0},
    ]
    assert room.orchestrator.question_lifelines == set()
    assert room.question_session is None
    assert room.question_response is None
    assert room.question_result is None
    assert room.active_lifeline is None
    assert room.audience_results is None
    assert room.question_remaining_ms == QUESTION_DURATION_MS
    assert len(room.plan_ids) == 12
    assert room.plan_ids != old_plan


def test_replay_returns_everyone_to_new_qualifier_without_new_qr() -> None:
    room = make_room(seed=221)
    people = join_people(room)
    finish_short_session(room, people)
    room_code = room.room_code
    tokens = [person.token for person in people]

    room.repeat()
    room.configure_questions_per_round(3)
    qualifier = room.start_qualifier()

    assert room.room_code == room_code
    assert room.state is SessionState.QUALIFIER_OPEN
    assert qualifier["opening"]["duration_ms"] == 30_000
    assert len(room.manager.current_opening.eligible_ids) == len(people)
    for token in tokens:
        participant = room.manager.authenticate(token)
        mobile = room.player_snapshot(participant.participant_id)
        assert mobile["question"]["opening"]["type"] == "qualifier"
        assert mobile["question"]["opening"]["allowed_answers"] == list("ABCD")


def test_replay_preserves_previous_mode_until_moderator_changes_it_in_lobby() -> None:
    room = make_room(seed=222)
    people = join_people(room)
    room.configure_questions_per_round(3)
    finish_short_session(room, people, questions_per_round=None)

    room.repeat()

    assert room.questions_per_round == 3
    assert room.host_snapshot()["settings"]["questions_per_round"] == 3
    room.configure_questions_per_round(5)
    assert room.questions_per_round == 5
