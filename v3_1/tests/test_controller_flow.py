from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication

from millonario_v3.participation.network import NetworkInfo
from millonario_v3.participation.room import RoomManager
from millonario_v3.participative_controller import ParticipativeController


class SilentAudio:
    def __getattr__(self, _name):
        return lambda *args, **kwargs: None


class FakeParticipation:
    def __init__(self, tmp_path: Path) -> None:
        self.manager = None
        self.network = None
        self.qr_path = tmp_path / "room.svg"
        self.qr_path.write_text("<svg/>", encoding="utf-8")
        self.events: list[tuple[str, dict | None]] = []

    @property
    def running(self) -> bool:
        return self.manager is not None

    @property
    def room_url(self) -> str:
        return self.network.local_url if self.network else ""

    def start(self, *, session_id, room_code, max_participants, **_kwargs):
        self.manager = RoomManager(
            session_id=session_id,
            room_code=room_code,
            max_participants=max_participants,
        )
        self.network = NetworkInfo(
            ip="192.168.8.100",
            port=8787,
            local_url=f"http://192.168.8.100:8787/sala/{room_code}",
        )
        return self.network

    def stop(self):
        self.manager = None

    def broadcast(self, event_type, payload=None, **_kwargs):
        self.events.append((event_type, payload))

    def broadcast_snapshot(self):
        return None


@pytest.fixture(scope="module", autouse=True)
def qt_application():
    app = QCoreApplication.instance() or QCoreApplication([])
    yield app


def test_complete_participative_flow(tmp_path) -> None:
    source_root = Path(__file__).resolve().parents[1]
    project_root = tmp_path / "v3"
    project_root.mkdir()
    for name in ("projects", "templates", "assets"):
        (project_root / name).mkdir()
    (project_root / "assets" / "audio").mkdir()
    (project_root / "assets" / "images").mkdir()
    (project_root / "data" / "sessions").mkdir(parents=True)
    (project_root / "data" / "runtime").mkdir(parents=True)
    (project_root / "mobile").mkdir()
    (project_root / "projects" / "demo.juego").write_bytes(
        (source_root / "projects" / "demo.juego").read_bytes()
    )
    (project_root / "templates" / "Banco_preguntas_V2.xlsx").write_bytes(
        (source_root / "templates" / "Banco_preguntas_V2.xlsx").read_bytes()
    )

    controller = ParticipativeController(project_root)
    controller.audio = SilentAudio()
    fake = FakeParticipation(tmp_path)
    controller.participation = fake
    controller.startParticipation()
    assert controller.screen == "lobby"

    joined = [
        fake.manager.join(f"Persona {index}", f"phone-{index}")
        for index in range(6)
    ]
    controller._poll_room()
    controller.lockRoomAndPrepareQualifier()
    assert controller.screen == "qualifier_open"
    assert fake.manager.current_opening is not None
    assert fake.manager.current_opening.duration_ms == 30_000
    assert fake.events[-1][0] == "qualifier.opened"
    assert controller.countdown == 30
    qualifier = controller.orchestrator.plan.qualifier.question
    correct = "ABCD"[qualifier.correct_index]
    for index, person in enumerate(joined):
        fake.manager.submit_answer(
            token=person.token,
            opening_id=fake.manager.current_opening.opening_id,
            answer=correct if index < 4 else "ABCD"[(qualifier.correct_index + 1) % 4],
        )
    controller._countdown = 1
    controller._timer_mode = "qualifier"
    controller._tick_countdown()
    assert controller.screen == "qualifier_results"
    assert len(controller.candidateItems) == 2

    controller.showCandidateSelection()
    assert controller.selectedCandidateCount == 2
    controller.confirmCandidates()
    assert controller.screen == "round_intro"

    for round_index in range(2):
        controller.startParticipativeRound()
        assert controller.screen == "round_question"
        for question_index in range(5):
            correct_index = controller.session.question.correct_index
            controller.selectParticipativeAnswer(correct_index)
            controller.nextParticipativeQuestion()
        assert controller.screen == "round_summary"
        controller.advanceAfterRound()
        assert controller.screen == (
            "round_intro" if round_index == 0 else "session_summary"
        )

    assert controller.firstPlayerScore == 5
    assert controller.secondPlayerScore == 5
    assert any(event[0] == "session.finished" for event in fake.events)
    controller.repeatParticipativeGame()
    assert controller.screen == "lobby"
    assert len(fake.manager.participants) == 6
    assert all(
        participant.role == "audience"
        for participant in fake.manager.participants.values()
    )
    assert any(event[0] == "session.restarted" for event in fake.events)
    controller.shutdown()
