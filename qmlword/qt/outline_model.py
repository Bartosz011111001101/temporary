"""Spłaszczone drzewo sekcji dla panelu nawigacji (z obsługą zwijania gałęzi)."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import (Property, QAbstractListModel, QByteArray, QModelIndex, QObject, Qt,
                            Signal, Slot)
from PySide6.QtQml import QmlElement

from .document_model import DocumentModel

QML_IMPORT_NAME = "QmlWord.Backend"
QML_IMPORT_MAJOR_VERSION = 1

_ROLES = {
    Qt.ItemDataRole.UserRole + 1: b"sectionId",
    Qt.ItemDataRole.UserRole + 2: b"title",
    Qt.ItemDataRole.UserRole + 3: b"level",
    Qt.ItemDataRole.UserRole + 4: b"depth",
    Qt.ItemDataRole.UserRole + 5: b"number",
    Qt.ItemDataRole.UserRole + 6: b"hasChildren",
    Qt.ItemDataRole.UserRole + 7: b"expanded",
    Qt.ItemDataRole.UserRole + 8: b"parentId",
    Qt.ItemDataRole.UserRole + 9: b"blockCount",
}
_FIELDS = {role: name.decode() for role, name in _ROLES.items()}


@QmlElement
class OutlineModel(QAbstractListModel):
    documentChanged = Signal()
    countChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._doc: DocumentModel | None = None
        self._collapsed: set[str] = set()
        self._rows: list[dict] = []

    # --- właściwości -----------------------------------------------------------
    def _get_document(self):
        return self._doc

    def _set_document(self, doc) -> None:
        if doc is self._doc:
            return
        if self._doc is not None:
            try:
                self._doc.structureChanged.disconnect(self._rebuild)
                self._doc.documentLoaded.disconnect(self._on_loaded)
            except (RuntimeError, TypeError):  # źródło już zniszczone (zamykanie aplikacji)
                pass
        self._doc = doc
        if doc is not None:
            doc.structureChanged.connect(self._rebuild)
            doc.documentLoaded.connect(self._on_loaded)
        self._rebuild()
        self.documentChanged.emit()

    document = Property(QObject, _get_document, _set_document, notify=documentChanged)

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._rows)

    @Property(int, notify=countChanged)
    def totalCount(self) -> int:
        return len(self._doc.outline_entries) if self._doc else 0

    # --- model -------------------------------------------------------------------
    def roleNames(self) -> dict:
        return {k: QByteArray(v) for k, v in _ROLES.items()}

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        row = self._rows[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return row["title"]
        name = _FIELDS.get(role)
        return row.get(name) if name else None

    def _on_loaded(self) -> None:
        self._collapsed.clear()
        self._rebuild()

    def _compute(self) -> list[dict]:
        if self._doc is None:
            return []
        entries = self._doc.outline_entries
        known = {e.id for e in entries}
        self._collapsed &= known
        rows: list[dict] = []
        hidden_depth: int | None = None
        for e in entries:
            if hidden_depth is not None:
                if e.depth > hidden_depth:
                    continue
                hidden_depth = None
            expanded = e.id not in self._collapsed
            rows.append({
                "sectionId": e.id, "title": e.title or "(bez tytułu)", "level": e.level,
                "depth": e.depth, "number": e.number, "hasChildren": e.has_children,
                "expanded": expanded, "parentId": e.parent_id, "blockCount": e.end - e.index,
            })
            if e.has_children and not expanded:
                hidden_depth = e.depth
        return rows

    def _rebuild(self) -> None:
        new_rows = self._compute()
        if [r["sectionId"] for r in new_rows] == [r["sectionId"] for r in self._rows]:
            for i, (old, new) in enumerate(zip(self._rows, new_rows)):
                if old != new:
                    self._rows[i] = new
                    idx = self.index(i)
                    self.dataChanged.emit(idx, idx, list(_ROLES))
            return
        self.beginResetModel()
        self._rows = new_rows
        self.endResetModel()
        self.countChanged.emit()

    # --- akcje ---------------------------------------------------------------------
    @Slot(str)
    def toggle(self, section_id: str) -> None:
        self.setExpanded(section_id, section_id in self._collapsed)

    @Slot(str, bool)
    def setExpanded(self, section_id: str, expanded: bool) -> None:
        if expanded:
            self._collapsed.discard(section_id)
        else:
            self._collapsed.add(section_id)
        self._rebuild()

    @Slot()
    def expandAll(self) -> None:
        self._collapsed.clear()
        self._rebuild()

    @Slot()
    def collapseAll(self) -> None:
        if self._doc is not None:
            self._collapsed = {e.id for e in self._doc.outline_entries if e.has_children}
        self._rebuild()

    @Slot(str, result=int)
    def rowOf(self, section_id: str) -> int:
        for i, r in enumerate(self._rows):
            if r["sectionId"] == section_id:
                return i
        return -1

    @Slot(int, result=str)
    def idAt(self, row: int) -> str:
        return self._rows[row]["sectionId"] if 0 <= row < len(self._rows) else ""

    @Slot(str)
    def reveal(self, section_id: str) -> None:
        """Rozwija przodków sekcji, żeby była widoczna w panelu."""
        if self._doc is None:
            return
        parents = {e.id: e.parent_id for e in self._doc.outline_entries}
        changed = False
        pid = parents.get(section_id, "")
        while pid:
            if pid in self._collapsed:
                self._collapsed.discard(pid)
                changed = True
            pid = parents.get(pid, "")
        if changed:
            self._rebuild()

    @Slot(str, str, result=bool)
    def isDescendant(self, section_id: str, maybe_ancestor: str) -> bool:
        if self._doc is None:
            return False
        parents = {e.id: e.parent_id for e in self._doc.outline_entries}
        pid = parents.get(section_id, "")
        while pid:
            if pid == maybe_ancestor:
                return True
            pid = parents.get(pid, "")
        return False
