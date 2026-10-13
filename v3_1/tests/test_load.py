from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from millonario_v3.participation.models import SubmissionStatus
from millonario_v3.participation.room import RoomError, RoomManager


def test_thirty_participants_burst_duplicates_and_three_audience_openings() -> None:
    room = RoomManager(
        session_id="ses_load",
        room_code="3000",
        max_participants=30,
    )
    joined = []
    rejected = 0
    for index in range(36):
        try:
            joined.append(room.join(f"Persona {index:02d}", f"device-{index}"))
        except RoomError as error:
            assert error.code == "room_full"
            rejected += 1
    assert len(joined) == 30
    assert rejected == 6

    room.lock()
    qualifier = room.open_remote(
        opening_type="qualifier",
        question_id="q-load",
        duration_ms=20_000,
    )

    def answer_once(item):
        return room.submit_answer(
            token=item.token,
            opening_id=qualifier.opening_id,
            answer="B",
        ).status

    with ThreadPoolExecutor(max_workers=30) as executor:
        statuses = list(executor.map(answer_once, joined))
    assert statuses.count(SubmissionStatus.ACCEPTED) == 30

    with ThreadPoolExecutor(max_workers=30) as executor:
        duplicate_statuses = list(executor.map(answer_once, joined))
    assert duplicate_statuses.count(SubmissionStatus.DUPLICATE) == 30
    assert room.close_opening(correct_index=1)["total"] == 30

    selected_ids = [
        joined[0].participant.participant_id,
        joined[1].participant.participant_id,
    ]
    room.set_selected(selected_ids)
    audience = joined[2:]
    for use_no in range(3):
        opening = room.open_remote(
            opening_type="audience",
            question_id=f"round-question-{use_no}",
            duration_ms=15_000,
            eligible_ids=[item.participant.participant_id for item in audience],
        )

        def audience_answer(item):
            return room.submit_answer(
                token=item.token,
                opening_id=opening.opening_id,
                answer="ABCD"[use_no % 4],
            ).status

        with ThreadPoolExecutor(max_workers=28) as executor:
            audience_statuses = list(executor.map(audience_answer, audience))
        assert audience_statuses.count(SubmissionStatus.ACCEPTED) == 28
        assert room.close_opening()["total"] == 28

    with pytest.raises(RoomError) as locked:
        room.join("Persona extra", "device-extra")
    assert locked.value.code == "room_locked"
