from __future__ import annotations

import pytest

from millonario_v3.participation.models import SubmissionStatus
from millonario_v3.participation.room import RoomError, RoomManager


def make_room(max_participants: int = 30) -> RoomManager:
    return RoomManager(
        session_id="ses_test",
        room_code="4827",
        max_participants=max_participants,
    )


def test_join_identity_alias_capacity_and_lock() -> None:
    room = make_room(2)
    first = room.join("Camila", "device-1")
    assert room.authenticate(first.token).alias == "Camila"
    with pytest.raises(RoomError) as duplicate:
        room.join("camila", "device-2")
    assert duplicate.value.code == "alias_taken"

    room.join("Diego", "device-2")
    with pytest.raises(RoomError) as full:
        room.join("Elena", "device-3")
    assert full.value.code == "room_full"

    room.lock()
    with pytest.raises(RoomError) as locked:
        room.join("Fabian", "device-4")
    assert locked.value.code == "room_locked"


def test_same_device_can_recover_access_without_duplicate_participant() -> None:
    room = make_room()
    first = room.join("Gonzalo", "same-phone")
    recovered = room.join("Gonzalo", "same-phone")
    assert recovered.participant.participant_id == first.participant.participant_id
    assert recovered.token != first.token
    assert len(room.participants) == 1
    with pytest.raises(RoomError) as old_token:
        room.authenticate(first.token)
    assert old_token.value.code == "invalid_token"
    assert room.authenticate(recovered.token).alias == "Gonzalo"


def test_avatar_is_validated_exposed_and_updated_on_device_recovery() -> None:
    room = make_room()
    first = room.join("Camila", "phone-avatar", "creative")
    assert first.participant.avatar == "creative"
    assert first.participant.public_dict()["avatar_symbol"] == "😎"

    recovered = room.join("Camila", "phone-avatar", "strategist")
    assert recovered.participant.participant_id == first.participant.participant_id
    assert recovered.participant.avatar == "strategist"
    assert recovered.participant.public_dict()["avatar_label"] == "Estratega"

    fallback = room.join("Diego", "other-phone", "unknown-avatar")
    assert fallback.participant.avatar == "explorer"


@pytest.mark.parametrize("alias", ["<script>", "A", "Nombre/con/barra", "x" * 25])
def test_invalid_aliases_are_rejected(alias: str) -> None:
    with pytest.raises(RoomError) as error:
        make_room().join(alias, "device")
    assert error.value.code == "invalid_alias"


def test_only_first_answer_is_accepted_and_late_is_not_counted() -> None:
    room = make_room()
    joined = room.join("Camila", "device-1")
    second = room.join("Diego", "device-2")
    opening = room.open_remote(
        opening_type="qualifier",
        question_id="question-1",
        duration_ms=20_000,
    )
    accepted = room.submit_answer(
        token=joined.token,
        opening_id=opening.opening_id,
        answer="B",
    )
    duplicate = room.submit_answer(
        token=joined.token,
        opening_id=opening.opening_id,
        answer="C",
    )
    assert accepted.status is SubmissionStatus.ACCEPTED
    assert duplicate.status is SubmissionStatus.DUPLICATE
    assert opening.responses[joined.participant.participant_id].answer == "B"

    opening.opened_perf -= 30
    late = room.submit_answer(
        token=second.token,
        opening_id=opening.opening_id,
        answer="B",
    )
    assert late.status is SubmissionStatus.LATE
    assert len(opening.responses) == 1


def test_results_and_first_two_correct_use_server_order() -> None:
    room = make_room()
    joined = [room.join(f"Persona {index}", f"device-{index}") for index in range(6)]
    opening = room.open_remote(
        opening_type="qualifier",
        question_id="question-1",
        duration_ms=20_000,
    )
    for index, item in enumerate(joined):
        room.submit_answer(
            token=item.token,
            opening_id=opening.opening_id,
            answer="C" if index < 5 else "A",
        )
    results = room.close_opening(correct_index=2)
    assert results["counts"] == [1, 0, 5, 0]
    assert results["total"] == 6
    assert [candidate["alias"] for candidate in results["candidates"]] == [
        "Persona 0",
        "Persona 1",
    ]


def test_replay_keeps_devices_and_resets_roles() -> None:
    room = make_room()
    people = [room.join(f"Persona {index}", f"device-{index}") for index in range(3)]
    room.lock()
    room.set_selected(
        [people[0].participant.participant_id, people[1].participant.participant_id]
    )
    room.reset_for_replay(session_id="ses_replay")
    assert room.session_id == "ses_replay"
    assert room.status.value == "open"
    assert room.current_opening is None
    assert all(person.role == "audience" for person in room.participants.values())
    assert room.authenticate(people[2].token).alias == "Persona 2"


def test_selected_participants_can_be_excluded_from_public_lifeline() -> None:
    room = make_room()
    people = [room.join(f"Persona {index}", f"device-{index}") for index in range(4)]
    selected = [people[0].participant.participant_id, people[1].participant.participant_id]
    room.set_selected(selected)
    audience = [
        participant.participant_id
        for participant in room.participants.values()
        if participant.role == "audience"
    ]
    opening = room.open_remote(
        opening_type="audience",
        question_id="question-2",
        duration_ms=15_000,
        eligible_ids=audience,
    )
    assert opening.eligible_ids.isdisjoint(selected)
    blocked = room.submit_answer(
        token=people[0].token,
        opening_id=opening.opening_id,
        answer="A",
    )
    assert blocked.status is SubmissionStatus.FORBIDDEN
