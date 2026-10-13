from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QMetaObject, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from .controller import GameController


def run(project_root: Path) -> int:
    QCoreApplication.setOrganizationName("Proyecto educativo privado")
    QCoreApplication.setApplicationName("Millonario educativo")
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"

    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    controller = GameController(project_root)
    engine.rootContext().setContextProperty("controller", controller)
    app.aboutToQuit.connect(controller.shutdown)

    qml_path = project_root / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1

    auto_start_game = os.environ.get("MILLONARIO_START_GAME") == "1"
    if auto_start_game:
        engine.rootObjects()[0].setProperty("menuVisible", False)
        controller.startGame()
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

        QTimer.singleShot(1800, finish_verification)

    return app.exec()
