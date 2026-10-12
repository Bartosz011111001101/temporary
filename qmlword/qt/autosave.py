"""Kopia robocza i odzyskiwanie dokumentu po nieoczekiwanym zamknięciu.

Każda sesja zapisuje kopię do własnego pliku w katalogu danych aplikacji
i trzyma blokadę ``QLockFile``. Przy starcie kopie, których blokady nikt nie
trzyma (proces padł), są proponowane do odzyskania. Poprawne zamknięcie
lub zapis dokumentu usuwa kopię.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime

from PySide6.QtCore import (Property, QLockFile, QObject, QStandardPaths, QTimer, Signal, Slot)
from PySide6.QtQml import QmlElement

from ..io import json_format
from ..io.formats import atomic_write
from .document_model import DocumentModel

QML_IMPORT_NAME = "QmlWord.Backend"
QML_IMPORT_MAJOR_VERSION = 1


def recovery_dir() -> str:
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    path = os.path.join(base or os.path.expanduser("~/.qmlword"), "recovery")
    os.makedirs(path, exist_ok=True)
    return path


@QmlElement
class AutosaveManager(QObject):
    documentChanged = Signal()
    recoveryChanged = Signal()
    savedDraft = Signal(str)  # godzina zapisu kopii

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._doc: DocumentModel | None = None
        self._session = uuid.uuid4().hex[:12]
        self._dir = ""
        self._lock: QLockFile | None = None
        self._last_revision = -1
        self._candidates: list[dict] = []
        self._timer = QTimer(self)
        self._timer.setInterval(30_000)
        self._timer.timeout.connect(self.saveDraft)
        try:
            self._dir = recovery_dir()
            self._lock = QLockFile(os.path.join(self._dir, f"{self._session}.lock"))
            self._lock.setStaleLockTime(0)
            self._lock.tryLock(100)
            self._timer.start()
        except OSError:
            self._dir = ""  # brak miejsca na kopie – funkcja po cichu wyłączona

    def _get_document(self):
        return self._doc

    def _set_document(self, doc) -> None:
        if doc is self._doc:
            return
        self._doc = doc
        self.documentChanged.emit()

    document = Property(QObject, _get_document, _set_document, notify=documentChanged)

    @Property(int, notify=documentChanged)
    def intervalSeconds(self) -> int:
        return self._timer.interval() // 1000

    @property
    def _draft_path(self) -> str:
        return os.path.join(self._dir, f"{self._session}.{json_format.FILE_EXTENSION}")

    @property
    def _info_path(self) -> str:
        return os.path.join(self._dir, f"{self._session}.info.json")

    @Slot()
    def saveDraft(self) -> None:
        doc = self._doc
        if not self._dir or doc is None:
            return
        if not doc.modified:
            self.discardOwn()
            return
        if doc.revision == self._last_revision:
            return
        try:
            atomic_write(self._draft_path, json_format.serialize(doc.state))
            info = {"originalPath": doc.filePath, "savedAt": datetime.now().isoformat(timespec="seconds"),
                    "title": doc.fileName}
            atomic_write(self._info_path, json.dumps(info, ensure_ascii=False).encode("utf-8"))
            self._last_revision = doc.revision
            self.savedDraft.emit(datetime.now().strftime("%H:%M"))
        except OSError:
            pass  # kopia robocza nie może przerywać pracy

    @Slot()
    def discardOwn(self) -> None:
        for path in (self._draft_path, self._info_path):
            try:
                os.remove(path)
            except OSError:
                pass
        self._last_revision = -1

    # --- odzyskiwanie ------------------------------------------------------------
    @Slot(result="QVariantList")
    def findRecoverable(self) -> list:
        self._candidates = []
        if not self._dir:
            return []
        for name in os.listdir(self._dir):
            if not name.endswith(".info.json"):
                continue
            session = name[: -len(".info.json")]
            if session == self._session:
                continue
            lock = QLockFile(os.path.join(self._dir, f"{session}.lock"))
            lock.setStaleLockTime(0)
            if not lock.tryLock(0):
                continue  # inna działająca instancja aplikacji
            lock.unlock()
            draft = os.path.join(self._dir, f"{session}.{json_format.FILE_EXTENSION}")
            try:
                with open(os.path.join(self._dir, name), encoding="utf-8") as fh:
                    info = json.load(fh)
            except (OSError, ValueError):
                info = {}
            if os.path.exists(draft):
                self._candidates.append({
                    "session": session,
                    "draft": draft,
                    "originalPath": str(info.get("originalPath", "")),
                    "title": str(info.get("title", "Bez tytułu")),
                    "savedAt": str(info.get("savedAt", "")).replace("T", " "),
                })
        self.recoveryChanged.emit()
        return list(self._candidates)

    @Slot(str, result=bool)
    def recover(self, session: str) -> bool:
        item = next((c for c in self._candidates if c["session"] == session), None)
        if item is None or self._doc is None:
            return False
        warnings: list[str] = []
        try:
            with open(item["draft"], "rb") as fh:
                state = json_format.parse(fh.read(), warnings)
        except (OSError, json_format.DocumentFormatError) as exc:
            self._doc.errorOccurred.emit("Nie udało się odzyskać dokumentu", str(exc))
            return False
        self._doc.load_state(state, item["originalPath"], mark_modified=True)
        self.discard(session)
        return True

    @Slot(str)
    def discard(self, session: str) -> None:
        if not self._dir or not session or session == self._session:
            return
        for suffix in (f".{json_format.FILE_EXTENSION}", ".info.json", ".lock"):
            try:
                os.remove(os.path.join(self._dir, session + suffix))
            except OSError:
                pass
        self._candidates = [c for c in self._candidates if c["session"] != session]
        self.recoveryChanged.emit()

    @Slot()
    def shutdown(self) -> None:
        """Poprawne zamknięcie aplikacji – kopia nie jest już potrzebna."""
        self._timer.stop()
        self.discardOwn()
        if self._lock is not None:
            self._lock.unlock()
            try:
                os.remove(os.path.join(self._dir, f"{self._session}.lock"))
            except OSError:
                pass
