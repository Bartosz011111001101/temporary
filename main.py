"""QmlWord – edytor dokumentów (Qt 6 / QML + backend w Pythonie).

Uruchomienie:  python main.py [plik.qwd.json]
Opcje deweloperskie:
  --screenshot PLIK.png   zapisuje zrzut okna po załadowaniu i kończy działanie
  --preview               startuje w trybie podglądu stron
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl, qInstallMessageHandler, QtMsgType
from PySide6.QtGui import QFont, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

# Import rejestruje typy QML (dekoratory @QmlElement) w module „QmlWord.Backend”.
from qmlword.qt import (app_utils, autosave, document_model, outline_model,  # noqa: F401
                        page_preview, rich_text, search)

ROOT = Path(__file__).resolve().parent


def _message_handler(mode: QtMsgType, context, message: str) -> None:
    if mode == QtMsgType.QtDebugMsg and "qml:" not in message:
        return
    try:
        where = f" ({context.file}:{context.line})" if context.file else ""
    except UnicodeDecodeError:  # ścieżki z polskimi znakami w kodowaniu lokalnym
        where = f" (linia {context.line})"
    print(f"[{mode.name}] {message}{where}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="QmlWord – edytor dokumentów")
    parser.add_argument("file", nargs="?", help="dokument do otwarcia")
    parser.add_argument("--screenshot", help="zapisz zrzut okna i zakończ (diagnostyka)")
    parser.add_argument("--preview", action="store_true", help="uruchom w trybie podglądu stron")
    args, qt_args = parser.parse_known_args()

    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Fusion")
    qInstallMessageHandler(_message_handler)
    app = QGuiApplication([sys.argv[0], *qt_args])
    app.setOrganizationName("QmlWord")
    app.setApplicationName("QmlWord")
    app.setApplicationDisplayName("QmlWord")
    app.setWindowIcon(QIcon(str(ROOT / "qml" / "icons" / "app.svg")))
    font = QFont("Segoe UI")
    font.setPointSizeF(9.5)
    app.setFont(font)
    QQuickStyle.setStyle("Fusion")

    engine = QQmlApplicationEngine()
    start_file = ""
    if args.file:
        start_file = QUrl.fromLocalFile(str(Path(args.file).resolve())).toString()
    engine.setInitialProperties({
        "startupFile": start_file,
        "screenshotPath": str(Path(args.screenshot).resolve()) if args.screenshot else "",
        "previewMode": bool(args.preview),
    })
    engine.load(QUrl.fromLocalFile(str(ROOT / "qml" / "Main.qml")))
    if not engine.rootObjects():
        print("Nie udało się załadować interfejsu (Main.qml). Szczegóły powyżej.", file=sys.stderr)
        return 1
    code = app.exec()
    # Silnik QML usuwamy przed zakończeniem interpretera (porządek niszczenia timerów/obiektów).
    del engine
    return code


if __name__ == "__main__":
    sys.exit(main())
