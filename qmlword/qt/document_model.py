"""Model dokumentu dla QML: lista bloków + stos cofania + operacje na plikach.

Każda zmiana to nowa, niemutowalna migawka ``DocumentData`` wrzucana na
``QUndoStack``. Przy nakładaniu migawki liczymy minimalną różnicę względem
widoku (zmiana treści / przeniesienie / wstawienie / usunięcie wierszy), żeby
delegaty QML – a więc i aktywne edytory – nie były niepotrzebnie odtwarzane.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import replace
from datetime import datetime
from typing import Any, Callable

from PySide6.QtCore import (Property, QAbstractListModel, QByteArray, QMimeData, QModelIndex, QObject,
                            QStandardPaths, Qt, QTimer, QUrl, Signal, Slot)
from PySide6.QtGui import QGuiApplication, QImage, QUndoCommand, QUndoStack
from PySide6.QtQml import QmlElement

from ..io import json_format
from ..io.formats import ExportError, FormatRegistry, default_registry
from ..io.json_format import DocumentFormatError
from ..io.html_import import blocks_plain_runs, html_to_blocks, text_to_blocks
from ..io.text_document_builder import fragment_html, resolve_image_path
from ..model import find, lists, ops, range_ops, styles, table_ops, table_style, text_ops
from ..model.blocks import (CAPTION, HEADING, IMAGE, PAGE_BREAK, PARAGRAPH, PLACEHOLDER, TABLE,
                            Block, ImageData, ParagraphFormat, TextRun, clamp_number, deep_merge,
                            normalize_runs, plain_runs)
from ..model.document import DocumentData, DocumentMeta, PageSettings, now_iso

QML_IMPORT_NAME = "QmlWord.Backend"
QML_IMPORT_MAJOR_VERSION = 1

MERGE_WINDOW_S = 2.0

ROLE_NAMES = {
    Qt.ItemDataRole.UserRole + 1: b"blockId",
    Qt.ItemDataRole.UserRole + 2: b"blockType",
    Qt.ItemDataRole.UserRole + 3: b"blockData",
    Qt.ItemDataRole.UserRole + 4: b"listNumber",
    Qt.ItemDataRole.UserRole + 5: b"captionLabel",
    Qt.ItemDataRole.UserRole + 6: b"captionNumber",
    Qt.ItemDataRole.UserRole + 7: b"hasCaption",
    Qt.ItemDataRole.UserRole + 8: b"imageUrl",
    Qt.ItemDataRole.UserRole + 9: b"sectionId",
    Qt.ItemDataRole.UserRole + 10: b"listMarker",
    Qt.ItemDataRole.UserRole + 11: b"borderJoin",
}
(R_ID, R_TYPE, R_DATA, R_LIST, R_CAP_LABEL, R_CAP_NUM, R_HAS_CAP, R_IMAGE, R_SECTION,
 R_MARKER, R_JOIN) = ROLE_NAMES
DERIVED_ROLES = [R_LIST, R_CAP_LABEL, R_CAP_NUM, R_HAS_CAP, R_SECTION, R_MARKER, R_JOIN]
CLIPBOARD_MIME = "application/x-qmlword-blocks"


def runs_from_qml(value: Any) -> tuple:
    if not isinstance(value, (list, tuple)):
        return ()
    return normalize_runs(TextRun.from_json(dict(item) if not isinstance(item, (str, dict)) else item)
                          for item in value)


def to_local_path(value: Any) -> str:
    if isinstance(value, QUrl):
        return value.toLocalFile() if value.isLocalFile() else value.toString()
    text = str(value or "")
    if text.startswith("file:"):
        return QUrl(text).toLocalFile()
    return text


class SnapshotCommand(QUndoCommand):
    """Komenda cofania przechowująca stan przed i po (bloki są współdzielone)."""

    def __init__(self, model: "DocumentModel", before: DocumentData, after: DocumentData,
                 text: str, merge_key: str = "", editor_block: str = "") -> None:
        super().__init__(text)
        self.model = model
        self.before = before
        self.after = after
        self.merge_key = merge_key
        self.editor_block = editor_block
        self.stamp = time.monotonic()
        self.first = True

    def id(self) -> int:  # noqa: A003 - API Qt
        return 1 if self.merge_key else -1

    def mergeWith(self, other: QUndoCommand) -> bool:
        if not isinstance(other, SnapshotCommand) or other.merge_key != self.merge_key:
            return False
        if other.stamp - self.stamp > MERGE_WINDOW_S:
            return False
        self.after = other.after
        self.stamp = other.stamp
        return True

    def redo(self) -> None:
        self.model._apply(self.after, self.editor_block if self.first else "")
        self.first = False

    def undo(self) -> None:
        self.model._apply(self.before, "")


@QmlElement
class DocumentModel(QAbstractListModel):
    # --- sygnały ---------------------------------------------------------------
    flushRequested = Signal()
    blockReset = Signal(str)                          # treść bloku zmieniona spoza jego edytora
    focusRequested = Signal(str, int, int, int, int)  # id, początek, koniec, wiersz, kolumna
    structureChanged = Signal()                       # zmienił się spis sekcji
    contentChanged = Signal()
    notice = Signal(str)                              # krótki komunikat (np. odrzucone przeniesienie)
    errorOccurred = Signal(str, str)                  # tytuł, treść
    warningsOccurred = Signal(str, "QVariantList")
    fileChanged = Signal()
    modifiedChanged = Signal()
    undoStateChanged = Signal()
    pageChanged = Signal()
    metaChanged = Signal()
    revisionChanged = Signal()
    statsChanged = Signal()
    documentLoaded = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._registry: FormatRegistry = default_registry()
        self._state = DocumentData.create_default()
        self._rows: tuple = self._state.blocks
        self._derived: list[tuple] = []
        self._outline_key: list = []
        self._outline: list[ops.OutlineEntry] = []
        self._path = ""
        self._revision = 0
        self._applying = False
        self._flushing = False
        self._last_error = ""
        self._word_count = 0
        self._undo = QUndoStack(self)
        self._undo.setUndoLimit(500)
        self._undo.cleanChanged.connect(self.modifiedChanged)
        self._undo.canUndoChanged.connect(self.undoStateChanged)
        self._undo.canRedoChanged.connect(self.undoStateChanged)
        self._undo.undoTextChanged.connect(self.undoStateChanged)
        self._undo.redoTextChanged.connect(self.undoStateChanged)
        self._recompute_derived(emit=False)

    # =====================================================================
    # QAbstractListModel
    # =====================================================================
    def roleNames(self) -> dict:
        return {k: QByteArray(v) for k, v in ROLE_NAMES.items()}

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        row = index.row()
        if not index.isValid() or not 0 <= row < len(self._rows):
            return None
        block = self._rows[row]
        if role == R_ID:
            return block.id
        if role == R_TYPE:
            return block.type
        if role == R_DATA:
            return block.to_json()
        if role == R_IMAGE:
            return self._image_url(block.image.path) if block.type == IMAGE else QUrl()
        if role in DERIVED_ROLES and row < len(self._derived):
            list_no, label, number, has_cap, section, marker, join = self._derived[row]
            return {R_LIST: list_no, R_CAP_LABEL: label, R_CAP_NUM: number, R_HAS_CAP: has_cap,
                    R_SECTION: section, R_MARKER: marker, R_JOIN: join}[role]
        if role == Qt.ItemDataRole.DisplayRole:
            return block.plain_text()
        return None

    # =====================================================================
    # Nakładanie migawek
    # =====================================================================
    def _apply(self, new_state: DocumentData, editor_block: str) -> None:
        old_state = self._state
        self._applying = True
        try:
            self._state = new_state
            self._sync_rows(old_state.blocks, new_state.blocks, editor_block)
            if old_state.page != new_state.page:
                self.pageChanged.emit()
            if old_state.meta != new_state.meta:
                self.metaChanged.emit()
            self._recompute_derived(emit=True)
            self._revision += 1
            self.revisionChanged.emit()
            self.contentChanged.emit()
        finally:
            self._applying = False

    def _sync_rows(self, old: tuple, new: tuple, editor_block: str) -> None:
        old_ids = [b.id for b in old]
        new_ids = [b.id for b in new]
        if old_ids != new_ids:
            n_old, n_new = len(old_ids), len(new_ids)
            p = 0
            while p < min(n_old, n_new) and old_ids[p] == new_ids[p]:
                p += 1
            s = 0
            while s < min(n_old, n_new) - p and old_ids[n_old - 1 - s] == new_ids[n_new - 1 - s]:
                s += 1
            mid_old = old_ids[p:n_old - s]
            mid_new = new_ids[p:n_new - s]
            k = self._rotation(mid_old, mid_new)
            if k > 0:
                # Przeniesienie: wiersze [p+k, koniec środka] trafiają na pozycję p.
                self.beginMoveRows(QModelIndex(), p + k, p + len(mid_old) - 1, QModelIndex(), p)
                self._rows = new
                self.endMoveRows()
            else:
                if mid_old:
                    self.beginRemoveRows(QModelIndex(), p, p + len(mid_old) - 1)
                    self._rows = old[:p] + old[n_old - s:]
                    self.endRemoveRows()
                if mid_new:
                    self.beginInsertRows(QModelIndex(), p, p + len(mid_new) - 1)
                    self._rows = new
                    self.endInsertRows()
        self._rows = new
        old_by_id = {b.id: b for b in old}
        for row, block in enumerate(new):
            before = old_by_id.get(block.id)
            if before is None or before is block or before == block:
                continue
            idx = self.index(row)
            self.dataChanged.emit(idx, idx, [R_DATA, R_TYPE, R_IMAGE, Qt.ItemDataRole.DisplayRole])
            if block.id != editor_block:
                self.blockReset.emit(block.id)

    @staticmethod
    def _rotation(a: list, b: list) -> int:
        """k > 0, jeśli b jest rotacją a o k pozycji (czyli pojedynczym przeniesieniem)."""
        if len(a) != len(b) or len(a) < 2 or set(a) != set(b):
            return 0
        k = a.index(b[0])
        if k and b == a[k:] + a[:k]:
            return k
        return 0

    def _recompute_derived(self, emit: bool) -> None:
        blocks = self._rows
        infos = lists.list_infos(blocks)
        captions = ops.caption_info(blocks)
        derived = []
        section = ""
        words = 0

        def border_key(b) -> tuple | None:
            if not b.is_text or (b.para.border == "none" and not b.para.shading):
                return None
            return (b.para.border, b.para.border_color, b.para.border_width, b.para.shading)

        keys = [border_key(b) for b in blocks]
        for i, b in enumerate(blocks):
            if b.type == HEADING:
                section = b.id
            label, number = captions.get(b.id, ("", 0))
            has_cap = b.is_captionable and b.id in captions
            join = 0
            if keys[i] is not None:
                # 1 = ta sama ramka co blok wyżej, 2 = ta sama co blok niżej (rysujemy jedną ramkę).
                join = (1 if i > 0 and keys[i - 1] == keys[i] else 0) | \
                       (2 if i + 1 < len(blocks) and keys[i + 1] == keys[i] else 0)
            derived.append((infos[i].number, label, number, has_cap, section, infos[i].marker, join))
            words += len(b.plain_text().split())
        old = self._derived
        self._derived = derived
        if emit:
            for row, value in enumerate(derived):
                if row >= len(old) or old[row] != value:
                    idx = self.index(row)
                    self.dataChanged.emit(idx, idx, DERIVED_ROLES)
        outline_key = [(b.id, b.level, b.plain_text()) for b in blocks if b.type == HEADING]
        if outline_key != self._outline_key or not emit:
            self._outline_key = outline_key
            self._outline = ops.outline(blocks)
            if emit:
                self.structureChanged.emit()
        else:
            self._outline = ops.outline(blocks)
        if words != self._word_count:
            self._word_count = words
            self.statsChanged.emit()

    # =====================================================================
    # Rdzeń edycji
    # =====================================================================
    def _commit(self, new_state: DocumentData, text: str, merge_key: str = "",
                editor_block: str = "") -> bool:
        if new_state is self._state or new_state == self._state:
            return False
        self._undo.push(SnapshotCommand(self, self._state, new_state, text, merge_key, editor_block))
        return True

    def _commit_blocks(self, blocks: tuple | None, text: str, merge_key: str = "",
                       editor_block: str = "") -> bool:
        if blocks is None:
            return False
        return self._commit(replace(self._state, blocks=ops.ensure_not_empty(tuple(blocks))),
                            text, merge_key, editor_block)

    def _flush(self) -> None:
        """Prosi edytory o zatwierdzenie oczekującego tekstu przed operacją strukturalną."""
        if self._flushing or self._applying:
            return
        self._flushing = True
        try:
            self.flushRequested.emit()
        finally:
            self._flushing = False

    def _run(self, text: str, fn: Callable[[tuple], tuple | None]) -> bool:
        self._flush()
        try:
            return self._commit_blocks(fn(self._state.blocks), text)
        except ops.OperationError as exc:
            self.notice.emit(str(exc))
            return False

    def _block(self, block_id: str) -> Block | None:
        i = ops.index_of(self._state.blocks, block_id)
        return self._state.blocks[i] if i >= 0 else None

    def _replace_block(self, block_id: str, text: str, fn: Callable[[Block], Block],
                       merge_key: str = "", editor_block: str = "") -> bool:
        if not merge_key:
            self._flush()
        blocks = self._state.blocks
        i = ops.index_of(blocks, block_id)
        if i < 0:
            return False
        try:
            new_block = fn(blocks[i])
        except ops.OperationError as exc:
            self.notice.emit(str(exc))
            return False
        if new_block == blocks[i]:
            return False
        return self._commit_blocks(blocks[:i] + (new_block,) + blocks[i + 1:], text, merge_key, editor_block)

    def _focus(self, block_id: str, start: int = 0, end: int = -1, row: int = -1, col: int = -1) -> None:
        self.focusRequested.emit(block_id, start, start if end < 0 else end, row, col)

    # =====================================================================
    # Właściwości dla QML
    # =====================================================================
    @Property(str, notify=fileChanged)
    def filePath(self) -> str:
        return self._path

    @Property(QUrl, notify=fileChanged)
    def fileUrl(self) -> QUrl:
        return QUrl.fromLocalFile(self._path) if self._path else QUrl()

    @Property(QUrl, notify=fileChanged)
    def folderUrl(self) -> QUrl:
        return QUrl.fromLocalFile(os.path.dirname(self._path)) if self._path else QUrl()

    @Property(str, notify=fileChanged)
    def fileName(self) -> str:
        return os.path.basename(self._path) if self._path else "Bez tytułu"

    @Property(str, notify=fileChanged)
    def suggestedName(self) -> str:
        if self._path:
            return os.path.splitext(os.path.basename(self._path))[0].removesuffix(".qwd")
        title = self._state.meta.title.strip() or self._first_title()
        return (title or "Dokument")[:60]

    def _first_title(self) -> str:
        for b in self._state.blocks:
            if b.type in (PARAGRAPH, HEADING) and b.plain_text().strip():
                return b.plain_text().strip().replace("/", "-").replace("\\", "-").replace(":", "")
        return ""

    @Property(bool, notify=modifiedChanged)
    def modified(self) -> bool:
        return not self._undo.isClean()

    @Property(bool, notify=undoStateChanged)
    def canUndo(self) -> bool:
        return self._undo.canUndo()

    @Property(bool, notify=undoStateChanged)
    def canRedo(self) -> bool:
        return self._undo.canRedo()

    @Property(str, notify=undoStateChanged)
    def undoText(self) -> str:
        return self._undo.undoText()

    @Property(str, notify=undoStateChanged)
    def redoText(self) -> str:
        return self._undo.redoText()

    @Property(int, notify=revisionChanged)
    def revision(self) -> int:
        return self._revision

    @Property(int, notify=statsChanged)
    def wordCount(self) -> int:
        return self._word_count

    @Property(int, notify=revisionChanged)
    def blockCount(self) -> int:
        return len(self._rows)

    @Property(str, notify=revisionChanged)
    def lastError(self) -> str:
        return self._last_error

    @Property("QVariantMap", notify=pageChanged)
    def page(self) -> dict:
        p = self._state.page
        w, h = p.size_mm()
        return {
            "size": p.size, "landscape": p.landscape,
            "marginTop": p.margin_top, "marginBottom": p.margin_bottom,
            "marginLeft": p.margin_left, "marginRight": p.margin_right,
            "widthMm": w, "heightMm": h,
        }

    @Property("QVariantMap", notify=metaChanged)
    def meta(self) -> dict:
        m = self._state.meta
        return {"title": m.title, "author": m.author, "created": m.created, "modified": m.modified,
                "fontFamily": m.font_family, "fontSize": m.font_size}

    @Property("QVariantMap", notify=metaChanged)
    def textStyles(self) -> dict:
        return styles.all_text_styles(self._state.meta)

    @Property("QVariantList", constant=True)
    def openFilters(self) -> list:
        return [i.name_filter() for i in self._registry.importers] + ["Wszystkie pliki (*)"]

    @Property("QVariantList", constant=True)
    def saveFilters(self) -> list:
        native = self._registry.exporter("json")
        return [native.name_filter()] if native else []

    @Property(str, constant=True)
    def nativeExtension(self) -> str:
        return json_format.FILE_EXTENSION

    # --- dostęp do stanu z Pythona (podgląd, wyszukiwanie, autozapis) ---------
    @property
    def state(self) -> DocumentData:
        return self._state

    @property
    def base_dir(self) -> str:
        return os.path.dirname(self._path) if self._path else ""

    @property
    def outline_entries(self) -> list[ops.OutlineEntry]:
        return self._outline

    # =====================================================================
    # Zapytania
    # =====================================================================
    @Slot(str, result=int)
    def indexOf(self, block_id: str) -> int:
        return ops.index_of(self._rows, block_id)

    @Slot(int, result=str)
    def blockIdAt(self, row: int) -> str:
        return self._rows[row].id if 0 <= row < len(self._rows) else ""

    @Slot(str, result="QVariantMap")
    def blockData(self, block_id: str) -> dict:
        b = self._block(block_id)
        return b.to_json() if b else {}

    @Slot(str, result=str)
    def blockType(self, block_id: str) -> str:
        b = self._block(block_id)
        return b.type if b else ""

    @Slot(str, result=str)
    def sectionOf(self, block_id: str) -> str:
        i = ops.index_of(self._rows, block_id)
        return self._derived[i][4] if 0 <= i < len(self._derived) else ""

    @Slot(str, result=int)
    def plainTextLength(self, block_id: str) -> int:
        b = self._block(block_id)
        return len(b.plain_text().strip()) if b else 0

    @Slot(str, result=str)
    def captionOf(self, target_id: str) -> str:
        return ops.caption_of(self._rows, target_id)

    @Slot(str, result="QVariantMap")
    def captionInfo(self, block_id: str) -> dict:
        i = ops.index_of(self._rows, block_id)
        if i < 0:
            return {}
        label, number = self._derived[i][1], self._derived[i][2]
        return {"label": label, "number": number}

    @Slot(str, result="QVariantMap")
    def sectionInfo(self, section_id: str) -> dict:
        for e in self._outline:
            if e.id == section_id:
                return {"id": e.id, "title": e.title, "level": e.level, "depth": e.depth,
                        "number": e.number, "parentId": e.parent_id, "hasChildren": e.has_children,
                        "blockCount": e.end - e.index}
        return {}

    @Slot(str, result=QUrl)
    def imageUrl(self, path: str) -> QUrl:
        return self._image_url(path)

    def _image_url(self, path: str) -> QUrl:
        if not path:
            return QUrl()
        return QUrl.fromLocalFile(resolve_image_path(path, self.base_dir))

    @Slot(str, int, result=str)
    def moveBlockProblem(self, block_id: str, dest: int) -> str:
        """Pusty tekst = przeniesienie dozwolone; inaczej powód odmowy."""
        try:
            plan = ops.plan_block_move(self._rows, block_id, dest)
        except ops.OperationError as exc:
            return str(exc)
        return "" if plan is not None else "noop"

    @Slot(str, str, str, result=str)
    def moveSectionProblem(self, section_id: str, target_id: str, mode: str) -> str:
        try:
            result = ops.move_section(self._rows, section_id, target_id, mode)
        except ops.OperationError as exc:
            return str(exc)
        return "" if result is not None else "noop"

    @Slot(str, result=int)
    def movableCount(self, block_id: str) -> int:
        i = ops.index_of(self._rows, block_id)
        return ops.movable_unit(self._rows, i)[1] if i >= 0 else 0

    # =====================================================================
    # Edycja tekstu (wywoływana przez edytory)
    # =====================================================================
    @Slot()
    def flush(self) -> None:
        self._flush()

    @Slot(str, "QVariantList")
    def setBlockRuns(self, block_id: str, runs) -> None:
        if self._applying:
            # Zatwierdzenie z niszczonego delegata w trakcie nakładania migawki – odkładamy.
            QTimer.singleShot(0, lambda: self.setBlockRuns(block_id, runs))
            return
        new_runs = runs_from_qml(runs)
        current = self._block(block_id)
        was_placeholder = current is not None and current.type == PLACEHOLDER

        def change(b: Block) -> Block:
            if b.type == PLACEHOLDER:
                return replace(Block.paragraph(runs=new_runs), id=b.id)
            if not b.is_text:
                return b
            return replace(b, runs=new_runs)

        if was_placeholder:
            # Pusty blok staje się akapitem – widok podmieni edytor, więc przenosimy kursor.
            self._replace_block(block_id, "Pisanie", change)
            self._focus(block_id, len("".join(r.text for r in new_runs)))
            return
        self._replace_block(block_id, "Pisanie", change, merge_key=f"text:{block_id}", editor_block=block_id)

    @Slot(str, "QVariantList", result=str)
    def setBlockParagraphs(self, block_id: str, paragraphs) -> str:
        """Edytor zawiera kilka akapitów (np. po wklejeniu) – rozbij je na osobne bloki."""
        paras = [runs_from_qml(p) for p in (paragraphs or [])] or [()]
        blocks = self._state.blocks
        i = ops.index_of(blocks, block_id)
        if i < 0:
            return ""
        template = blocks[i]
        if template.type == PLACEHOLDER:
            template = replace(Block.paragraph(), id=template.id)
        if not template.is_text:
            return ""
        first = replace(template, runs=paras[0])
        rest = []
        for runs in paras[1:]:
            if template.type == PARAGRAPH:
                rest.append(Block.paragraph(runs=runs, style=template.style, para=template.para))
            else:
                rest.append(Block.paragraph(runs=runs))
        self._commit_blocks(blocks[:i] + (first, *rest) + blocks[i + 1:], "Wklejanie akapitów",
                            editor_block="")
        last = (rest[-1] if rest else first)
        self._focus(last.id, len("".join(r.text for r in last.runs)))
        return last.id

    @Slot(str, "QVariantList", "QVariantList", result=str)
    def splitBlock(self, block_id: str, before, after) -> str:
        """Enter w akapicie: tekst za kursorem trafia do nowego bloku pod spodem."""
        blocks = self._state.blocks
        i = ops.index_of(blocks, block_id)
        if i < 0:
            return ""
        current = blocks[i]
        if current.type == PLACEHOLDER:
            current = replace(Block.paragraph(), id=current.id)
        if not current.is_text:
            return ""
        before_runs, after_runs = runs_from_qml(before), runs_from_qml(after)
        if current.type == PARAGRAPH and current.style == "body":
            new_block = Block.paragraph(runs=after_runs, para=current.para)
        else:
            # Po nagłówku lub tytule zaczynamy zwykły akapit.
            new_block = Block.paragraph(runs=after_runs)
        new_blocks = blocks[:i] + (replace(current, runs=before_runs), new_block) + blocks[i + 1:]
        self._commit_blocks(new_blocks, "Nowy akapit")
        self._focus(new_block.id, 0)
        return new_block.id

    @Slot(str, "QVariantList", result=bool)
    def mergeWithPrevious(self, block_id: str, runs) -> bool:
        """Backspace na początku akapitu: dołącz tekst do poprzedniego bloku tekstowego."""
        self._flush()
        blocks = self._state.blocks
        i = ops.index_of(blocks, block_id)
        if i <= 0:
            return False
        current = blocks[i]
        prev = blocks[i - 1]
        own_runs = runs_from_qml(runs)
        if prev.is_text:
            pos = len("".join(r.text for r in prev.runs))
            merged = replace(prev, runs=normalize_runs((*prev.runs, *own_runs)))
            self._commit_blocks(blocks[:i - 1] + (merged,) + blocks[i + 1:], "Scalenie akapitów")
            self._focus(prev.id, pos)
            return True
        if not own_runs:
            # Pusty akapit za tabelą/obrazem – po prostu go usuwamy.
            self._commit_blocks(blocks[:i] + blocks[i + 1:], "Usunięcie akapitu")
            self._focus(prev.id, 0)
            return True
        return False

    @Slot(str, result=bool)
    def removeEmptyAndFocusNext(self, block_id: str) -> bool:
        """Delete na końcu pustego akapitu."""
        blocks = self._state.blocks
        i = ops.index_of(blocks, block_id)
        if i < 0 or i + 1 >= len(blocks):
            return False
        nxt = blocks[i + 1]
        self._commit_blocks(blocks[:i] + blocks[i + 1:], "Usunięcie akapitu")
        self._focus(nxt.id, 0)
        return True

    # =====================================================================
    # Wstawianie i usuwanie bloków
    # =====================================================================
    def _make_block(self, kind: str, options: dict) -> tuple[Block, ...]:
        if kind in ("paragraph", "body"):
            return (Block.paragraph(str(options.get("text", ""))),)
        if kind == "title":
            return (Block.paragraph(str(options.get("text", "")), style="title"),)
        if kind == "heading":
            level = int(options.get("level", 1))
            return (Block.heading(level, str(options.get("text", "")) or "Nowa sekcja"),)
        if kind == "table":
            rows = int(options.get("rows", 3))
            cols = int(options.get("cols", 3))
            table = Block.new_table(rows, cols, bool(options.get("headerRow", True)))
            if options.get("caption"):
                return (table, Block.new_caption(table.id, str(options.get("captionText", ""))))
            return (table,)
        if kind == "image":
            path = self._store_image_path(to_local_path(options.get("path", "")))
            image = Block.new_image(path)
            if options.get("caption"):
                return (image, Block.new_caption(image.id, str(options.get("captionText", ""))))
            return (image,)
        if kind == "pageBreak":
            return (Block.page_break(),)
        if kind == "placeholder":
            return (Block.placeholder(),)
        raise ops.OperationError(f"Nieznany typ elementu: {kind}")

    _INSERT_LABELS = {"paragraph": "Wstawienie akapitu", "title": "Wstawienie tytułu",
                      "heading": "Wstawienie sekcji", "table": "Wstawienie tabeli",
                      "image": "Wstawienie obrazu", "pageBreak": "Wstawienie podziału strony",
                      "placeholder": "Wstawienie pustego bloku"}

    @Slot(int, str, "QVariantMap", result=str)
    def insertBlock(self, index: int, kind: str, options) -> str:
        self._flush()
        options = dict(options or {})
        try:
            new_blocks = self._make_block(kind, options)
        except ops.OperationError as exc:
            self.notice.emit(str(exc))
            return ""
        blocks = self._state.blocks
        index = ops.adjust_drop_index(blocks, index if index >= 0 else len(blocks))
        # Wstawienie w miejsce pustego bloku zastępuje go.
        if 0 <= index - 1 < len(blocks) and options.get("replaceEmpty") and blocks[index - 1].type == PLACEHOLDER:
            index -= 1
            blocks = blocks[:index] + blocks[index + 1:]
        result = blocks[:index] + new_blocks + blocks[index:]
        self._commit_blocks(result, self._INSERT_LABELS.get(kind, "Wstawienie"))
        first = new_blocks[0]
        if first.type == HEADING:
            self._focus(first.id, 0, len(first.plain_text()))
        elif first.type == TABLE:
            self._focus(first.id, 0, 0, 0, 0)
        else:
            self._focus(first.id, len(first.plain_text()))
        return first.id

    @Slot(str, str, "QVariantMap", result=str)
    def insertAfter(self, block_id: str, kind: str, options) -> str:
        i = ops.index_of(self._rows, block_id)
        if i < 0:
            return self.insertBlock(len(self._rows), kind, options)
        start, count = ops.movable_unit(self._rows, i, whole_section=False)
        return self.insertBlock(start + count, kind, options)

    @Slot(str, str, "QVariantMap", result=str)
    def insertBefore(self, block_id: str, kind: str, options) -> str:
        i = ops.index_of(self._rows, block_id)
        if i < 0:
            return self.insertBlock(0, kind, options)
        start, _count = ops.movable_unit(self._rows, i, whole_section=False)
        return self.insertBlock(start, kind, options)

    @Slot(str, str, "QVariantMap", result=str)
    def replacePlaceholder(self, block_id: str, kind: str, options) -> str:
        self._flush()
        blocks = self._state.blocks
        i = ops.index_of(blocks, block_id)
        if i < 0:
            return ""
        try:
            new_blocks = self._make_block(kind, dict(options or {}))
        except ops.OperationError as exc:
            self.notice.emit(str(exc))
            return ""
        self._commit_blocks(blocks[:i] + new_blocks + blocks[i + 1:], self._INSERT_LABELS.get(kind, "Wstawienie"))
        first = new_blocks[0]
        self._focus(first.id, 0, len(first.plain_text()) if first.type == HEADING else 0, 0 if first.type == TABLE else -1, 0 if first.type == TABLE else -1)
        return first.id

    @Slot(str, result=bool)
    def removeBlock(self, block_id: str) -> bool:
        blocks = self._state.blocks
        i = ops.index_of(blocks, block_id)
        focus_id = blocks[i - 1].id if i > 0 else (blocks[i + 1].id if i + 1 < len(blocks) else "")
        b = blocks[i] if i >= 0 else None
        label = {TABLE: "Usunięcie tabeli", IMAGE: "Usunięcie obrazu", CAPTION: "Usunięcie podpisu",
                 HEADING: "Usunięcie nagłówka"}.get(b.type if b else "", "Usunięcie bloku")
        ok = self._run(label, lambda bl: ops.remove_block(bl, block_id))
        if ok and focus_id:
            prev = self._block(focus_id)
            self._focus(focus_id, len(prev.plain_text()) if prev and prev.is_text else 0)
        return ok

    @Slot(str, result=bool)
    def removeSection(self, section_id: str) -> bool:
        return self._run("Usunięcie sekcji", lambda bl: ops.remove_section(bl, section_id))

    @Slot(str, result=str)
    def duplicateBlock(self, block_id: str) -> str:
        self._flush()
        blocks = self._state.blocks
        i = ops.index_of(blocks, block_id)
        if i < 0:
            return ""
        start, count = ops.movable_unit(blocks, i, whole_section=False)
        unit = blocks[start:start + count]
        copies = []
        id_map = {}
        for b in unit:
            nb = replace(b, id=Block.paragraph().id)
            id_map[b.id] = nb.id
            copies.append(nb)
        copies = [replace(b, caption=replace(b.caption, target_id=id_map.get(b.caption.target_id, "")))
                  if b.type == CAPTION else b for b in copies]
        self._commit_blocks(blocks[:start + count] + tuple(copies) + blocks[start + count:], "Duplikowanie")
        return copies[0].id

    # =====================================================================
    # Przenoszenie
    # =====================================================================
    @Slot(str, int, result=bool)
    def moveBlock(self, block_id: str, dest: int) -> bool:
        b = self._block(block_id)
        label = "Przeniesienie sekcji" if b and b.type == HEADING else "Przeniesienie elementu"
        return self._run(label, lambda bl: ops.move_block(bl, block_id, dest))

    @Slot(str, int, result=bool)
    def moveBlockBy(self, block_id: str, direction: int) -> bool:
        """Klawiaturowe przenoszenie bloku (Alt+Shift+↑/↓) o jedną jednostkę."""
        blocks = self._rows
        i = ops.index_of(blocks, block_id)
        if i < 0:
            return False
        start, count = ops.movable_unit(blocks, i)
        if direction < 0:
            if start == 0:
                return False
            prev_start, _ = ops.movable_unit(blocks, start - 1, whole_section=False)
            return self.moveBlock(block_id, prev_start)
        end = start + count
        if end >= len(blocks):
            return False
        _ns, ncount = ops.movable_unit(blocks, end, whole_section=False)
        return self.moveBlock(block_id, end + ncount)

    @Slot(str, str, str, result=bool)
    def moveSection(self, section_id: str, target_id: str, mode: str) -> bool:
        return self._run("Przeniesienie sekcji", lambda bl: ops.move_section(bl, section_id, target_id, mode))

    @Slot(str, int, result=bool)
    def moveSectionStep(self, section_id: str, direction: int) -> bool:
        ok = self._run("Przeniesienie sekcji", lambda bl: ops.move_section_sibling(bl, section_id, direction))
        if not ok:
            self.notice.emit("Sekcja jest już na skraju swojego poziomu.")
        return ok

    @Slot(str, int, result=bool)
    def changeSectionLevel(self, section_id: str, delta: int) -> bool:
        return self._run("Zmiana poziomu sekcji", lambda bl: ops.change_section_level(bl, section_id, delta))

    @Slot(str, bool, result=str)
    def addSection(self, ref_id: str, as_child: bool) -> str:
        self._flush()
        try:
            blocks, new_id = ops.add_section(self._state.blocks, ref_id, as_child)
        except ops.OperationError as exc:
            self.notice.emit(str(exc))
            return ""
        self._commit_blocks(blocks, "Dodanie podsekcji" if as_child else "Dodanie sekcji")
        b = self._block(new_id)
        self._focus(new_id, 0, len(b.plain_text()) if b else 0)
        return new_id

    # =====================================================================
    # Formatowanie bloków
    # =====================================================================
    @Slot(str, str, result=bool)
    def setStyle(self, block_id: str, style: str) -> bool:
        def change(b: Block) -> Block:
            if b.type == PLACEHOLDER:
                b = replace(Block.paragraph(), id=b.id)
            if not b.is_text:
                raise ops.OperationError("Styl akapitu można ustawić tylko dla tekstu.")
            if style in ("body", "title"):
                para = b.para
                if b.type == HEADING or b.style != style:
                    para = replace(ParagraphFormat() if style == "body" else
                                   ParagraphFormat(space_before=0, space_after=14, line_height=1.0),
                                   align=b.para.align)
                return replace(b, type=PARAGRAPH, style=style, description="", para=para)
            if style.startswith("h") and style[1:].isdigit():
                level = int(style[1:])
                para = b.para if b.type == HEADING else ParagraphFormat(
                    space_before=14, space_after=4, line_height=1.1, align=b.para.align)
                return replace(b, type=HEADING, level=level, style="body", para=replace(para, list="none", indent=0))
            raise ops.OperationError("Nieznany styl akapitu.")

        return self._replace_block(block_id, "Zmiana stylu", change)

    @Slot(str, "QVariantMap", result=bool)
    def setParagraph(self, block_id: str, patch) -> bool:
        patch = dict(patch or {})

        def change(b: Block) -> Block:
            if not b.is_text:
                raise ops.OperationError("Formatowanie akapitu dotyczy tylko tekstu.")
            merged = ParagraphFormat.from_json({**b.para.to_json(), **patch}, b.para)
            if b.type == HEADING:
                merged = replace(merged, list="none")
            return replace(b, para=merged)

        label = "Lista" if "list" in patch else "Wyrównanie" if "align" in patch else "Formatowanie akapitu"
        return self._replace_block(block_id, label, change)

    @Slot(str, int, result=bool)
    def changeIndent(self, block_id: str, delta: int) -> bool:
        b = self._block(block_id)
        if not b or not b.is_text:
            return False
        return self.setParagraph(block_id, {"indent": max(0, min(8, b.para.indent + delta))})

    @Slot(str, str, result=bool)
    def setHeadingTitle(self, block_id: str, text: str) -> bool:
        def change(b: Block) -> Block:
            if b.type != HEADING:
                raise ops.OperationError("To nie jest sekcja.")
            if b.plain_text() == text:
                return b
            return replace(b, runs=plain_runs(text.replace("\n", " ")))

        return self._replace_block(block_id, "Zmiana nazwy sekcji", change)

    @Slot(str, str, result=bool)
    def setDescription(self, block_id: str, text: str) -> bool:
        def change(b: Block) -> Block:
            if b.type != HEADING:
                raise ops.OperationError("Opis można dodać tylko do sekcji.")
            return replace(b, description=text)

        return self._replace_block(block_id, "Opis sekcji", change, merge_key=f"desc:{block_id}",
                                   editor_block=block_id)

    @Slot(str, str, result=bool)
    def setCaptionText(self, block_id: str, text: str) -> bool:
        def change(b: Block) -> Block:
            if b.type != CAPTION:
                raise ops.OperationError("To nie jest podpis.")
            return replace(b, caption=replace(b.caption, text=text))

        return self._replace_block(block_id, "Edycja podpisu", change, merge_key=f"cap:{block_id}",
                                   editor_block=block_id)

    @Slot(str, result=str)
    def addCaption(self, target_id: str) -> str:
        self._flush()
        blocks = self._state.blocks
        i = ops.index_of(blocks, target_id)
        if i < 0 or not blocks[i].is_captionable:
            self.notice.emit("Podpis można dodać tylko do tabeli lub obrazu.")
            return ""
        existing = ops.caption_index_for(blocks, i)
        if existing >= 0:
            self._focus(blocks[existing].id, 0)
            return blocks[existing].id
        caption = Block.new_caption(target_id)
        self._commit_blocks(blocks[:i + 1] + (caption,) + blocks[i + 1:], "Dodanie podpisu")
        self._focus(caption.id, 0)
        return caption.id

    @Slot(str, "QVariantMap", result=bool)
    def setImage(self, block_id: str, patch) -> bool:
        patch = dict(patch or {})
        if "path" in patch:
            patch["path"] = self._store_image_path(to_local_path(patch["path"]))

        def change(b: Block) -> Block:
            if b.type != IMAGE:
                raise ops.OperationError("To nie jest obraz.")
            return replace(b, image=ImageData.from_json(deep_merge(b.image.to_json(), patch)))

        merge = f"img:{block_id}:{','.join(sorted(patch))}" if set(patch) <= {"width", "alt", "crop", "border"} else ""
        return self._replace_block(block_id, "Zmiana obrazu", change, merge_key=merge)

    def _store_image_path(self, path: str) -> str:
        """Obraz w katalogu dokumentu zapisujemy ścieżką względną (przenośność)."""
        if not path:
            return ""
        path = os.path.normpath(path)
        base = self.base_dir
        if base and os.path.isabs(path):
            try:
                rel = os.path.relpath(path, base)
            except ValueError:  # inny dysk
                return path
            if not rel.startswith(".."):
                return rel.replace("\\", "/")
        return path

    # =====================================================================
    # Tabele
    # =====================================================================
    def _table_op(self, block_id: str, text: str, fn, merge_key: str = "", editor_block: str = "") -> bool:
        def change(b: Block) -> Block:
            if b.type != TABLE:
                raise ops.OperationError("To nie jest tabela.")
            return replace(b, table=table_ops.recompute_formulas(fn(b.table)))

        return self._replace_block(block_id, text, change, merge_key, editor_block)

    @Slot(str, int, int, "QVariantList")
    def setCellRuns(self, block_id: str, row: int, col: int, runs) -> None:
        if self._applying:
            QTimer.singleShot(0, lambda: self.setCellRuns(block_id, row, col, runs))
            return
        new_runs = runs_from_qml(runs)
        b = self._block(block_id)
        has_formulas = b is not None and b.type == TABLE and any(c.formula for r in b.table.cells for c in r)
        # Tabela z formułami: wyniki zmieniają się w innych komórkach, więc odświeżamy cały blok.
        self._table_op(block_id, "Edycja komórki", lambda t: table_ops.set_cell_runs(t, row, col, new_runs),
                       merge_key=f"cell:{block_id}:{row}:{col}", editor_block="" if has_formulas else block_id)

    @Slot(str, int, result=bool)
    def tableInsertRow(self, block_id: str, at: int) -> bool:
        return self._table_op(block_id, "Wstawienie wiersza", lambda t: table_ops.insert_row(t, at))

    @Slot(str, int, result=bool)
    def tableRemoveRow(self, block_id: str, row: int) -> bool:
        return self._table_op(block_id, "Usunięcie wiersza", lambda t: table_ops.remove_row(t, row))

    @Slot(str, int, result=bool)
    def tableInsertColumn(self, block_id: str, at: int) -> bool:
        return self._table_op(block_id, "Wstawienie kolumny", lambda t: table_ops.insert_column(t, at))

    @Slot(str, int, result=bool)
    def tableRemoveColumn(self, block_id: str, col: int) -> bool:
        return self._table_op(block_id, "Usunięcie kolumny", lambda t: table_ops.remove_column(t, col))

    @Slot(str, int, int, int, int, result=bool)
    def tableMerge(self, block_id: str, r1: int, c1: int, r2: int, c2: int) -> bool:
        return self._table_op(block_id, "Scalenie komórek", lambda t: table_ops.merge_cells(t, r1, c1, r2, c2))

    @Slot(str, int, int, result=bool)
    def tableSplit(self, block_id: str, row: int, col: int) -> bool:
        return self._table_op(block_id, "Podział komórki", lambda t: table_ops.split_cell(t, row, col))

    @Slot(str, int, int, int, int, str, result=bool)
    def tableSetAlign(self, block_id: str, r1: int, c1: int, r2: int, c2: int, align: str) -> bool:
        return self._table_op(block_id, "Wyrównanie komórek",
                              lambda t: table_ops.set_cells_align(t, r1, c1, r2, c2, align))

    @Slot(str, int, int, int, int, str, result=bool)
    def tableSetBackground(self, block_id: str, r1: int, c1: int, r2: int, c2: int, color: str) -> bool:
        return self._table_op(block_id, "Tło komórek",
                              lambda t: table_ops.set_cells_background(t, r1, c1, r2, c2, color))

    @Slot(str, "QVariantList", result=bool)
    def tableSetColumnWidths(self, block_id: str, widths) -> bool:
        values = [float(w) for w in (widths or [])]
        return self._table_op(block_id, "Szerokość kolumn", lambda t: table_ops.set_column_widths(t, values),
                              merge_key=f"colw:{block_id}")

    @Slot(str, int, float, result=bool)
    def tableSetRowHeight(self, block_id: str, row: int, height: float) -> bool:
        return self._table_op(block_id, "Wysokość wiersza", lambda t: table_ops.set_row_height(t, row, height),
                              merge_key=f"rowh:{block_id}:{row}")

    @Slot(str, "QVariantMap", result=bool)
    def tableSetOptions(self, block_id: str, options) -> bool:
        options = dict(options or {})

        def fn(t):
            style = options.get("style", t.style)
            return replace(t, header_row=bool(options.get("headerRow", t.header_row)),
                           repeat_header=bool(options.get("repeatHeader", t.repeat_header)),
                           style=style if style in table_style.STYLE_LABELS else t.style,
                           banded_rows=bool(options.get("bandedRows", t.banded_rows)),
                           first_column=bool(options.get("firstColumn", t.first_column)))

        return self._table_op(block_id, "Ustawienia tabeli", fn)


    # =====================================================================
    # Wielkość liter, krawędzie, sortowanie, formuły, konwersje
    # =====================================================================
    @Slot(str, int, int, int, int, str, result=bool)
    def changeCase(self, block_id: str, row: int, col: int, start: int, end: int, mode: str) -> bool:
        """Zmiana wielkości liter w zaznaczeniu jednego bloku lub komórki."""
        if start == end:
            return False
        if row >= 0:
            return self._table_op(block_id, "Wielkość liter", lambda t: table_ops.set_cell_runs(
                t, row, col, text_ops.change_case(t.cells[t.anchor_of(row, col)[0]][t.anchor_of(row, col)[1]].runs,
                                                  start, end, mode)))

        def change(b: Block) -> Block:
            if not b.is_text:
                raise ops.OperationError("Wielkość liter można zmienić tylko w tekście.")
            return replace(b, runs=text_ops.change_case(b.runs, start, end, mode))

        ok = self._replace_block(block_id, "Wielkość liter", change)
        if ok:
            self._focus(block_id, start, end)
        return ok

    @Slot(str, int, int, int, int, str, result=bool)
    def tableSetBorders(self, block_id: str, r1: int, c1: int, r2: int, c2: int, preset: str) -> bool:
        return self._table_op(block_id, "Obramowanie komórek",
                              lambda t: table_ops.set_cells_borders(t, r1, c1, r2, c2, preset))

    @Slot(str, int, bool, result=bool)
    def tableSort(self, block_id: str, col: int, descending: bool) -> bool:
        return self._table_op(block_id, "Sortowanie tabeli", lambda t: table_ops.sort_rows(t, col, descending))

    @Slot(str, int, int, str, result=bool)
    def tableSetFormula(self, block_id: str, row: int, col: int, formula: str) -> bool:
        return self._table_op(block_id, "Formuła", lambda t: table_ops.set_cell_formula(t, row, col, formula))

    @Slot(str, int, int, result=str)
    def cellFormula(self, block_id: str, row: int, col: int) -> str:
        b = self._block(block_id)
        if b is None or b.type != TABLE or not (0 <= row < b.table.rows and 0 <= col < b.table.cols):
            return ""
        ar, ac = b.table.anchor_of(row, col)
        return b.table.cells[ar][ac].formula

    @Slot(str, result="QVariantList")
    def tableAppearance(self, block_id: str) -> list:
        b = self._block(block_id)
        return table_style.appearance(b.table) if b is not None and b.type == TABLE else []

    @Property("QVariantList", constant=True)
    def tableStyles(self) -> list:
        return [{"key": k, "label": v} for k, v in table_style.STYLE_LABELS.items()]

    @Property("QVariantMap", constant=True)
    def listStyleLabels(self) -> dict:
        return {"bullet": lists.BULLET_LABELS, "number": lists.NUMBER_LABELS}

    @Slot(str, str, result=str)
    def tableToText(self, block_id: str, separator: str) -> str:
        self._flush()
        try:
            blocks, first = range_ops.table_to_text(self._state.blocks, block_id, separator or "\t")
        except ops.OperationError as exc:
            self.notice.emit(str(exc))
            return ""
        self._commit_blocks(blocks, "Tabela na tekst")
        self._focus(first, 0)
        return first

    # =====================================================================
    # Zaznaczenie obejmujące wiele bloków
    # =====================================================================
    def _span(self, a_id: str, a_pos: int, f_id: str, f_pos: int) -> range_ops.Span | None:
        try:
            return range_ops.normalize_span(self._state.blocks, a_id, a_pos, f_id, f_pos)
        except ops.OperationError as exc:
            self.notice.emit(str(exc))
            return None

    @Slot(str, result=int)
    def blockLength(self, block_id: str) -> int:
        b = self._block(block_id)
        return range_ops.block_length(b) if b else 0

    @Slot(str, int, str, int, result=str)
    def rangeText(self, a_id: str, a_pos: int, f_id: str, f_pos: int) -> str:
        self._flush()
        span = self._span(a_id, a_pos, f_id, f_pos)
        return range_ops.range_plain_text(self._state.blocks, span) if span else ""

    @Slot(str, int, str, int, result=bool)
    def copyRange(self, a_id: str, a_pos: int, f_id: str, f_pos: int) -> bool:
        self._flush()
        span = self._span(a_id, a_pos, f_id, f_pos)
        if span is None:
            return False
        self._set_clipboard(range_ops.extract_range(self._state.blocks, span),
                            range_ops.range_plain_text(self._state.blocks, span))
        return True

    @Slot(str, int, str, int, result=bool)
    def cutRange(self, a_id: str, a_pos: int, f_id: str, f_pos: int) -> bool:
        return self.copyRange(a_id, a_pos, f_id, f_pos) and self._delete_span(a_id, a_pos, f_id, f_pos, "Wycinanie")

    @Slot(str, int, str, int, result=bool)
    def deleteRange(self, a_id: str, a_pos: int, f_id: str, f_pos: int) -> bool:
        return self._delete_span(a_id, a_pos, f_id, f_pos, "Usunięcie zaznaczenia")

    def _delete_span(self, a_id: str, a_pos: int, f_id: str, f_pos: int, label: str) -> bool:
        self._flush()
        span = self._span(a_id, a_pos, f_id, f_pos)
        if span is None:
            return False
        blocks, focus_id, pos = range_ops.delete_range(self._state.blocks, span)
        self._commit_blocks(blocks, label)
        self._focus(focus_id, pos)
        return True

    @Slot(str, int, str, int, str, result=bool)
    def replaceRange(self, a_id: str, a_pos: int, f_id: str, f_pos: int, text: str) -> bool:
        """Pisanie przy zaznaczeniu wielu bloków: usuwa zaznaczenie i wstawia znaki."""
        self._flush()
        span = self._span(a_id, a_pos, f_id, f_pos)
        if span is None:
            return False
        blocks, focus_id, pos = range_ops.delete_range(self._state.blocks, span)
        i = ops.index_of(blocks, focus_id)
        if i >= 0 and blocks[i].is_text and text:
            b = blocks[i]
            runs = text_ops.replace_in_runs(b.runs, pos, pos, text)
            blocks = blocks[:i] + (replace(b, runs=runs),) + blocks[i + 1:]
            pos += len(text)
        self._commit_blocks(blocks, "Pisanie")
        self._focus(focus_id, pos)
        return True

    @Slot(str, int, str, int, "QVariantMap", result=bool)
    def formatRange(self, a_id: str, a_pos: int, f_id: str, f_pos: int, props) -> bool:
        self._flush()
        span = self._span(a_id, a_pos, f_id, f_pos)
        if span is None:
            return False
        return self._commit_blocks(range_ops.format_range(self._state.blocks, span, dict(props or {})),
                                   "Formatowanie")

    @Slot(str, int, str, int, str, result=bool)
    def caseRange(self, a_id: str, a_pos: int, f_id: str, f_pos: int, mode: str) -> bool:
        self._flush()
        span = self._span(a_id, a_pos, f_id, f_pos)
        if span is None:
            return False
        return self._commit_blocks(range_ops.case_range(self._state.blocks, span, mode), "Wielkość liter")

    @Slot(str, int, str, int, "QVariantMap", result=bool)
    def paragraphRange(self, a_id: str, a_pos: int, f_id: str, f_pos: int, patch) -> bool:
        self._flush()
        span = self._span(a_id, a_pos, f_id, f_pos)
        if span is None:
            return False
        patch = dict(patch or {})
        blocks = list(self._state.blocks)
        for i in range_ops.text_blocks_in_span(self._state.blocks, span):
            b = blocks[i]
            merged = ParagraphFormat.from_json({**b.para.to_json(), **patch}, b.para)
            blocks[i] = replace(b, para=replace(merged, list="none") if b.type == HEADING else merged)
        return self._commit_blocks(tuple(blocks), "Formatowanie akapitów")

    @Slot(str, int, str, int, str, result=bool)
    def styleRange(self, a_id: str, a_pos: int, f_id: str, f_pos: int, style: str) -> bool:
        self._flush()
        span = self._span(a_id, a_pos, f_id, f_pos)
        if span is None:
            return False
        ids = [self._state.blocks[i].id for i in range_ops.text_blocks_in_span(self._state.blocks, span)]
        self._undo.beginMacro("Zmiana stylu")
        try:
            for block_id in ids:
                self.setStyle(block_id, style)
        finally:
            self._undo.endMacro()
        return bool(ids)

    @Slot(str, int, str, int, str, result=str)
    def textToTable(self, a_id: str, a_pos: int, f_id: str, f_pos: int, separator: str) -> str:
        self._flush()
        span = self._span(a_id, a_pos, f_id, f_pos)
        if span is None:
            return ""
        try:
            blocks, table_id = range_ops.text_to_table(self._state.blocks, span.start_index, span.end_index,
                                                       separator or "\t")
        except ops.OperationError as exc:
            self.notice.emit(str(exc))
            return ""
        self._commit_blocks(blocks, "Tekst na tabelę")
        self._focus(table_id, 0, 0, 0, 0)
        return table_id

    # =====================================================================
    # Znajdź i zamień (wywoływane przez SearchController)
    # =====================================================================
    def applyReplace(self, matches: list, replacement: str, fmt: dict, label: str) -> int:
        self._flush()
        blocks, count = find.replace_matches(self._state.blocks, matches, replacement, fmt)
        if count:
            self._commit_blocks(blocks, label)
            self.notice.emit("Zamieniono 1 wystąpienie." if count == 1 else f"Zamieniono wystąpień: {count}.")
        return count

    # =====================================================================
    # Schowek
    # =====================================================================
    def _set_clipboard(self, fragment: tuple, plain: str) -> None:
        mime = QMimeData()
        mime.setData(CLIPBOARD_MIME, json.dumps([b.to_json() for b in fragment], ensure_ascii=False).encode("utf-8"))
        try:
            mime.setHtml(fragment_html(replace(self._state, blocks=fragment), self.base_dir))
        except Exception:  # noqa: BLE001 - HTML to tylko dodatek dla innych programów
            pass
        mime.setText(plain)
        QGuiApplication.clipboard().setMimeData(mime)

    @Slot(str, result=bool)
    def copyBlock(self, block_id: str) -> bool:
        self._flush()
        blocks = self._state.blocks
        i = ops.index_of(blocks, block_id)
        if i < 0:
            return False
        start, count = ops.movable_unit(blocks, i)
        span = range_ops.Span(start, 0, start + count - 1, range_ops.block_length(blocks[start + count - 1]))
        self._set_clipboard(range_ops.extract_range(blocks, span), range_ops.range_plain_text(blocks, span))
        self.notice.emit("Skopiowano do schowka.")
        return True

    @Slot(str, result=bool)
    def cutBlock(self, block_id: str) -> bool:
        b = self._block(block_id)
        if b is None or not self.copyBlock(block_id):
            return False
        if b.type == HEADING:
            return self.removeSection(block_id)
        return self.removeBlock(block_id)

    def _store_pasted_image(self, image: QImage) -> str:
        if self.base_dir:
            folder = os.path.join(self.base_dir, "obrazy")
        else:
            base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
            folder = os.path.join(base or os.path.expanduser("~/.qmlword"), "obrazy")
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError:
            return ""
        name = f"wklejony-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.png"
        path = os.path.join(folder, name)
        if not image.save(path, "PNG"):
            return ""
        return self._store_image_path(path)

    def _clipboard_fragment(self, mode: str) -> tuple | None:
        md = QGuiApplication.clipboard().mimeData()
        if md is None:
            return None
        if mode != "plain" and md.hasFormat(CLIPBOARD_MIME):
            try:
                raw = json.loads(bytes(md.data(CLIPBOARD_MIME)).decode("utf-8"))
                blocks = tuple(b for b in (Block.from_json(item) for item in raw) if b is not None)
                if mode == "merge":
                    blocks = html_to_blocks(fragment_html(replace(self._state, blocks=blocks), self.base_dir), "merge")
                return range_ops.fresh_ids(blocks)
            except (ValueError, TypeError):
                pass
        if mode != "plain" and md.hasImage() and not md.hasText():
            image = QImage(md.imageData())
            path = self._store_pasted_image(image) if not image.isNull() else ""
            return (Block.new_image(path),) if path else None
        if mode != "plain" and md.hasHtml():
            blocks = html_to_blocks(md.html(), mode, self._store_pasted_image)
            if blocks:
                return range_ops.fresh_ids(blocks)
        if md.hasText():
            return text_to_blocks(md.text())
        return None

    @Slot(str, int, int, int, int, str, result=bool)
    def paste(self, block_id: str, start: int, end: int, row: int, col: int, mode: str) -> bool:
        """Wklejanie w miejscu kursora; mode: source | merge | plain."""
        self._flush()
        fragment = self._clipboard_fragment(mode)
        if not fragment:
            self.notice.emit("Schowek nie zawiera tekstu ani obrazu do wklejenia.")
            return False
        if row >= 0:
            runs = blocks_plain_runs(fragment)
            if mode == "plain":
                runs = tuple(replace(r, **{f: v for f, v in (("bold", None), ("italic", None), ("underline", None),
                                                               ("strike", None), ("color", ""), ("highlight", ""),
                                                               ("font_family", ""), ("font_size", 0.0), ("link", ""),
                                                               ("vertical", ""), ("small_caps", None))})
                             for r in runs)
            length = text_ops.runs_length(runs)

            def fn(t):
                ar, ac = t.anchor_of(row, col)
                cell_runs = t.cells[ar][ac].runs
                left, rest = text_ops.split_runs(cell_runs, start)
                _, right = text_ops.split_runs(rest, max(0, end - start))
                return table_ops.set_cell_runs(t, row, col, normalize_runs((*left, *runs, *right)))

            ok = self._table_op(block_id, "Wklejanie", fn)
            if ok:
                self._focus(block_id, start + length, start + length, row, col)
            return ok
        try:
            blocks, focus_id, pos = range_ops.insert_fragment(self._state.blocks, block_id, start, end, fragment)
        except ops.OperationError:
            # Kursor nie w tekście (np. zaznaczona tabela) – wklejamy pod blokiem.
            i = ops.index_of(self._state.blocks, block_id)
            if i < 0:
                return False
            s0, count = ops.movable_unit(self._state.blocks, i, whole_section=False)
            blocks = self._state.blocks[:s0 + count] + fragment + self._state.blocks[s0 + count:]
            focus_id, pos = fragment[-1].id, range_ops.block_length(fragment[-1])
        self._commit_blocks(blocks, "Wklejanie")
        self._focus(focus_id, pos)
        return True

    @Slot(str, int, str, int, str, result=bool)
    def pasteRange(self, a_id: str, a_pos: int, f_id: str, f_pos: int, mode: str) -> bool:
        self._flush()
        fragment = self._clipboard_fragment(mode)
        span = self._span(a_id, a_pos, f_id, f_pos)
        if not fragment or span is None:
            return False
        blocks, focus_id, pos = range_ops.delete_range(self._state.blocks, span)
        i = ops.index_of(blocks, focus_id)
        if i >= 0 and (blocks[i].is_text or blocks[i].type == PLACEHOLDER):
            blocks, focus_id, pos = range_ops.insert_fragment(blocks, focus_id, pos, pos, fragment)
        else:
            blocks = blocks[:i + 1] + fragment + blocks[i + 1:]
            focus_id, pos = fragment[-1].id, range_ops.block_length(fragment[-1])
        self._commit_blocks(blocks, "Wklejanie")
        self._focus(focus_id, pos)
        return True

    @Property(bool, constant=True)
    def clipboardAvailable(self) -> bool:
        return True

    # =====================================================================
    # Strona i metadane
    # =====================================================================
    @Slot("QVariantMap", result=bool)
    def setPageSettings(self, values) -> bool:
        self._flush()
        p = self._state.page
        values = dict(values or {})
        page = PageSettings.from_json(deep_merge(p.to_json(), {
            "size": values.get("size", p.size),
            "orientation": "landscape" if values.get("landscape", p.landscape) else "portrait",
            "margins": {
                "top": values.get("marginTop", p.margin_top),
                "bottom": values.get("marginBottom", p.margin_bottom),
                "left": values.get("marginLeft", p.margin_left),
                "right": values.get("marginRight", p.margin_right),
            },
        }))
        return self._commit(replace(self._state, page=page), "Ustawienia strony")

    @Slot("QVariantMap", result=bool)
    def setMeta(self, values) -> bool:
        self._flush()
        m = self._state.meta
        values = dict(values or {})
        meta = replace(m,
                       title=str(values.get("title", m.title)),
                       author=str(values.get("author", m.author)),
                       font_family=str(values.get("fontFamily", m.font_family)) or m.font_family,
                       font_size=clamp_number(values.get("fontSize", m.font_size), 6, 72, m.font_size))
        return self._commit(replace(self._state, meta=meta), "Właściwości dokumentu")

    # =====================================================================
    # Cofanie / ponawianie
    # =====================================================================
    @Slot()
    def undo(self) -> None:
        self._flush()
        if self._undo.canUndo():
            self._undo.undo()

    @Slot()
    def redo(self) -> None:
        self._flush()
        if self._undo.canRedo():
            self._undo.redo()

    @Slot(str, int, int, int, int)
    def requestFocus(self, block_id: str, start: int, end: int, row: int, col: int) -> None:
        self.focusRequested.emit(block_id, start, end, row, col)

    # =====================================================================
    # Pliki
    # =====================================================================
    def _reset_to(self, state: DocumentData, path: str) -> None:
        self.beginResetModel()
        # Ścieżka musi być ustawiona przed końcem resetu – względne ścieżki obrazów
        # są rozwiązywane względem katalogu dokumentu już przy pierwszym odczycie roli.
        self._path = path
        self._state = state
        self._rows = state.blocks
        self._derived = []
        self._outline_key = []
        self._recompute_derived(emit=False)
        self.endResetModel()
        self._undo.clear()
        self._undo.setClean()
        self._revision += 1
        self.structureChanged.emit()
        self.fileChanged.emit()
        self.modifiedChanged.emit()
        self.pageChanged.emit()
        self.metaChanged.emit()
        self.revisionChanged.emit()
        self.statsChanged.emit()
        self.contentChanged.emit()
        self.documentLoaded.emit()

    def _set_error(self, title: str, message: str) -> None:
        self._last_error = message
        self.errorOccurred.emit(title, message)

    @Slot()
    def newDocument(self) -> None:
        self._reset_to(DocumentData.create_default(), "")
        self._focus(self._rows[0].id, 0)

    @Slot("QVariant", result=bool)
    def openFile(self, url) -> bool:
        path = to_local_path(url)
        if not path:
            return False
        importer = self._registry.importer_for(path)
        warnings: list[str] = []
        try:
            state = importer.read(path, warnings)
        except DocumentFormatError as exc:
            self._set_error("Nie udało się otworzyć dokumentu", f"{os.path.basename(path)}\n\n{exc}")
            return False
        except Exception as exc:  # noqa: BLE001 - nie pozwalamy aplikacji upaść na złym pliku
            self._set_error("Nie udało się otworzyć dokumentu", f"Nieoczekiwany błąd: {exc}")
            return False
        self._reset_to(state, os.path.abspath(path))
        if warnings:
            self.warningsOccurred.emit("Dokument wczytano z poprawkami", warnings)
        return True

    def load_state(self, state: DocumentData, path: str, mark_modified: bool) -> None:
        """Wczytanie stanu z kopii odzyskiwania."""
        self._reset_to(state, path)
        if mark_modified:
            # Pusta zmiana nie ma sensu – oznaczamy brud przez sztuczny „niezapisany” stan.
            self._undo.resetClean()
            self.modifiedChanged.emit()

    @Slot(result=bool)
    def save(self) -> bool:
        if not self._path:
            return False
        return self._write(self._path)

    @Slot("QVariant", result=bool)
    def saveAs(self, url) -> bool:
        path = to_local_path(url)
        if not path:
            return False
        if not path.lower().endswith("." + json_format.FILE_EXTENSION) and not path.lower().endswith(".json"):
            path += "." + json_format.FILE_EXTENSION
        old_base = self.base_dir
        new_base = os.path.dirname(os.path.abspath(path))
        if old_base != new_base:
            self._rebase_images(old_base, new_base)
        if self._write(path):
            self._path = os.path.abspath(path)
            self.fileChanged.emit()
            # Ścieżki względne obrazów liczą się teraz od nowego katalogu.
            for row, b in enumerate(self._rows):
                if b.type == IMAGE:
                    idx = self.index(row)
                    self.dataChanged.emit(idx, idx, [R_IMAGE])
            return True
        return False

    def _rebase_images(self, old_base: str, new_base: str) -> None:
        changed = False
        blocks = []
        for b in self._state.blocks:
            if b.type == IMAGE and b.image.path:
                absolute = resolve_image_path(b.image.path, old_base)
                try:
                    rel = os.path.relpath(absolute, new_base)
                    new_path = rel.replace("\\", "/") if not rel.startswith("..") else absolute
                except ValueError:
                    new_path = absolute
                if new_path != b.image.path:
                    b = replace(b, image=replace(b.image, path=new_path))
                    changed = True
            blocks.append(b)
        if changed:
            # Bez wpisu na stos cofania – to techniczna zmiana towarzysząca „Zapisz jako”.
            self._state = replace(self._state, blocks=tuple(blocks))
            self._rows = self._state.blocks

    def _write(self, path: str) -> bool:
        self._flush()
        exporter = self._registry.exporter("json")
        state = replace(self._state, meta=replace(self._state.meta, modified=now_iso(),
                                                  created=self._state.meta.created or now_iso()))
        try:
            exporter.write(state, path, os.path.dirname(path))
        except ExportError as exc:
            self._set_error("Nie udało się zapisać dokumentu", f"{path}\n\n{exc}")
            return False
        except Exception as exc:  # noqa: BLE001
            self._set_error("Nie udało się zapisać dokumentu", f"Nieoczekiwany błąd: {exc}")
            return False
        self._state = replace(self._state, meta=state.meta)
        self._undo.setClean()
        self.metaChanged.emit()
        return True

    @Slot("QVariant", result=bool)
    def exportPdf(self, url) -> bool:
        self._flush()
        path = to_local_path(url)
        if not path:
            return False
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        exporter = self._registry.exporter("pdf")
        try:
            exporter.write(self._state, path, self.base_dir)
        except ExportError as exc:
            self._set_error("Eksport PDF nie powiódł się", str(exc))
            return False
        except Exception as exc:  # noqa: BLE001
            self._set_error("Eksport PDF nie powiódł się", f"Nieoczekiwany błąd: {exc}")
            return False
        self.notice.emit(f"Wyeksportowano: {os.path.basename(path)}")
        return True
