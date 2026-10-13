from __future__ import annotations

import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMetaObject, QObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from millonario.controller import GameController


class QmlIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QGuiApplication.instance() or QGuiApplication([])

    def test_main_view_loads_and_editor_can_be_opened(self) -> None:
        root_dir = Path(__file__).resolve().parents[1]
        engine = QQmlApplicationEngine()
        controller = GameController(root_dir)
        engine.rootContext().setContextProperty("controller", controller)
        engine.load(QUrl.fromLocalFile(str(root_dir / "qml" / "Main.qml")))

        self.assertEqual(len(engine.rootObjects()), 1)
        root = engine.rootObjects()[0]
        editor = root.findChild(QObject, "editorShade")
        menu = root.findChild(QObject, "menuView")
        self.assertIsNotNone(editor)
        self.assertIsNotNone(menu)
        self.assertFalse(editor.property("visible"))
        self.assertTrue(menu.property("visible"))

        self.assertTrue(QMetaObject.invokeMethod(root, "openEditor"))
        self.app.processEvents()
        self.assertTrue(editor.property("visible"))

        editor.setProperty("visible", False)
        self.assertTrue(QMetaObject.invokeMethod(root, "startFromMenu"))
        self.app.processEvents()
        self.assertFalse(menu.property("visible"))

        controller.shutdown()
        engine.deleteLater()


if __name__ == "__main__":
    unittest.main()
