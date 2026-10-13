from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QMetaObject, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from .participative_controller import ParticipativeController


def _prepare_demo_screen(controller: ParticipativeController, target: str) -> None:
    """Prepara estados deterministas usados solo por las capturas de QA."""
    controller.startParticipation()
    manager = controller.participation.manager
    if manager is None:
        return
    joined = [
        manager.join(f"Participante {index + 1}", f"demo-device-{index}")
        for index in range(8)
    ]
    for participant in joined:
        manager.set_connected(participant.participant.participant_id, True)
    controller._poll_room()
    if target == "lobby":
        return
    controller.lockRoomAndPrepareQualifier()
    if target in {"qualifier_ready", "qualifier_open"}:
        return
    question = controller.orchestrator.plan.qualifier.question
    correct = "ABCD"[question.correct_index]
    opening_id = manager.current_opening.opening_id
    for index, participant in enumerate(joined):
        manager.submit_answer(
            token=participant.token,
            opening_id=opening_id,
            answer=correct if index < 5 else "ABCD"[(question.correct_index + 1) % 4],
        )
    controller.closeQualifier()
    if target == "qualifier_results":
        return
    controller.showCandidateSelection()
    if target == "player_selection":
        return
    controller.toggleCandidate(0)
    controller.toggleCandidate(1)
    controller.confirmCandidates()
    if target == "round_intro":
        return
    controller.startParticipativeRound()


def run(project_root: Path) -> int:
    QCoreApplication.setOrganizationName("Proyecto educativo privado")
    QCoreApplication.setApplicationName("Millonario educativo V3.1.4")
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"

    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    controller = ParticipativeController(project_root)
    engine.rootContext().setContextProperty("controller", controller)
    app.aboutToQuit.connect(controller.shutdown)

    qml_path = project_root / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1

    demo_screen = os.environ.get("MILLONARIO_V3_DEMO_SCREEN", "")
    auto_start_game = os.environ.get("MILLONARIO_START_GAME") == "1"
    if demo_screen:
        engine.rootObjects()[0].setProperty("menuVisible", False)
        _prepare_demo_screen(controller, demo_screen)
    elif auto_start_game:
        engine.rootObjects()[0].setProperty("menuVisible", False)
        controller.startParticipation()
    if os.environ.get("MILLONARIO_OPEN_EDITOR") == "1":
        QMetaObject.invokeMethod(engine.rootObjects()[0], "openEditor")
    if os.environ.get("MILLONARIO_OPEN_EDIT_OPTIONS") == "1":
        QMetaObject.invokeMethod(engine.rootObjects()[0], "openEditOptions")
    if os.environ.get("MILLONARIO_OPEN_IMPORT") == "1":
        QMetaObject.invokeMethod(engine.rootObjects()[0], "openImport")

    # La primera pintura no espera a que Windows inspeccione el MP3.
    if not auto_start_game:
        QTimer.singleShot(500, controller.startAudio)

    screenshot_path = os.environ.get("MILLONARIO_SCREENSHOT")
    smoke_test = os.environ.get("MILLONARIO_SMOKE_TEST") == "1"
    if screenshot_path or smoke_test:
        def finish_verification() -> None:
            if screenshot_path:
                window = engine.rootObjects()[0]
                screen = window.screen() or app.primaryScreen()
                pixmap = screen.grabWindow(int(window.winId()))
                pixmap.save(screenshot_path)
            app.quit()

        try:
            verification_delay = max(
                1000,
                min(30_000, int(os.environ.get("MILLONARIO_SMOKE_TEST_MS", "1800"))),
            )
        except ValueError:
            verification_delay = 1800
        QTimer.singleShot(verification_delay, finish_verification)

    return app.exec()
