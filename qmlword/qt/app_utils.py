"""Drobne funkcje systemowe dla QML (czcionki, ścieżki, schowek)."""
from __future__ import annotations

import os

from PySide6.QtCore import Property, QObject, QUrl, Slot
from PySide6.QtGui import QDesktopServices, QFontDatabase, QGuiApplication
from PySide6.QtQml import QmlElement, QmlSingleton

QML_IMPORT_NAME = "QmlWord.Backend"
QML_IMPORT_MAJOR_VERSION = 1

PREFERRED_FONTS = ["Calibri", "Cambria", "Georgia", "Segoe UI", "Times New Roman", "Arial",
                   "Verdana", "Garamond", "Consolas", "Courier New"]


@QmlElement
@QmlSingleton
class AppUtils(QObject):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        families = [f for f in QFontDatabase.families() if not f.startswith("@")]
        preferred = [f for f in PREFERRED_FONTS if f in families]
        self._fonts = preferred + sorted(f for f in families if f not in preferred)

    @Property("QVariantList", constant=True)
    def fontFamilies(self) -> list:
        return self._fonts

    @Property("QVariantList", constant=True)
    def fontSizes(self) -> list:
        return [8, 9, 10, 10.5, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 72]

    @Slot("QVariant", result=str)
    def toLocalFile(self, url) -> str:
        if isinstance(url, QUrl):
            return url.toLocalFile()
        text = str(url or "")
        return QUrl(text).toLocalFile() if text.startswith("file:") else text

    @Slot(str, result=QUrl)
    def fromLocalFile(self, path: str) -> QUrl:
        return QUrl.fromLocalFile(path)

    @Slot(str, result=bool)
    def fileExists(self, path: str) -> bool:
        return bool(path) and os.path.exists(path)

    @Slot(str, result=str)
    def baseName(self, path: str) -> str:
        return os.path.basename(path)

    @Slot(str, result=bool)
    def openExternal(self, url: str) -> bool:
        target = QUrl.fromUserInput(url)
        if target.scheme() not in ("http", "https", "mailto", "file"):
            return False
        return QDesktopServices.openUrl(target)

    @Slot(result=str)
    def clipboardText(self) -> str:
        return QGuiApplication.clipboard().text()

    @Slot(str, result=str)
    def normalizeUrl(self, text: str) -> str:
        text = text.strip()
        if not text:
            return ""
        url = QUrl.fromUserInput(text)
        return url.toString() if url.isValid() else text
