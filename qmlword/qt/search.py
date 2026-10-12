"""Znajdź i zamień: wyniki, przechodzenie między nimi, zamiana bieżącego i wszystkich."""
from __future__ import annotations

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtQml import QmlElement

from ..model import find
from ..model.find import Match, find_matches  # noqa: F401 - używane też w testach
from .document_model import DocumentModel

QML_IMPORT_NAME = "QmlWord.Backend"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
class SearchController(QObject):
    documentChanged = Signal()
    queryChanged = Signal()
    resultsChanged = Signal()
    optionsChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._doc: DocumentModel | None = None
        self._query = ""
        self._replacement = ""
        self._case = False
        self._whole = False
        self._find_fmt: dict = {}
        self._replace_fmt: dict = {}
        self._matches: list[Match] = []
        self._current = -1
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._refresh)

    # --- właściwości ---------------------------------------------------------------
    def _get_document(self):
        return self._doc

    def _set_document(self, doc) -> None:
        if doc is self._doc:
            return
        if self._doc is not None:
            try:
                self._doc.contentChanged.disconnect(self._schedule)
                self._doc.documentLoaded.disconnect(self._schedule)
            except (RuntimeError, TypeError):  # źródło już zniszczone (zamykanie aplikacji)
                pass
        self._doc = doc
        if doc is not None:
            doc.contentChanged.connect(self._schedule)
            doc.documentLoaded.connect(self._schedule)
        self.documentChanged.emit()
        self._refresh()

    document = Property(QObject, _get_document, _set_document, notify=documentChanged)

    def _get_query(self) -> str:
        return self._query

    def _set_query(self, value: str) -> None:
        if value == self._query:
            return
        self._query = value
        self._current = -1
        self.queryChanged.emit()
        self._refresh()

    query = Property(str, _get_query, _set_query, notify=queryChanged)

    def _get_replacement(self) -> str:
        return self._replacement

    def _set_replacement(self, value: str) -> None:
        if value != self._replacement:
            self._replacement = value
            self.optionsChanged.emit()

    replacement = Property(str, _get_replacement, _set_replacement, notify=optionsChanged)

    def _get_case(self) -> bool:
        return self._case

    def _set_case(self, value: bool) -> None:
        if value != self._case:
            self._case = value
            self.optionsChanged.emit()
            self._refresh()

    caseSensitive = Property(bool, _get_case, _set_case, notify=optionsChanged)

    def _get_whole(self) -> bool:
        return self._whole

    def _set_whole(self, value: bool) -> None:
        if value != self._whole:
            self._whole = value
            self.optionsChanged.emit()
            self._refresh()

    wholeWords = Property(bool, _get_whole, _set_whole, notify=optionsChanged)

    def _get_find_fmt(self) -> dict:
        return dict(self._find_fmt)

    def _set_find_fmt(self, value) -> None:
        value = find.clean_format(dict(value or {}))
        if value != self._find_fmt:
            self._find_fmt = value
            self.optionsChanged.emit()
            self._refresh()

    findFormat = Property("QVariantMap", _get_find_fmt, _set_find_fmt, notify=optionsChanged)

    def _get_replace_fmt(self) -> dict:
        return dict(self._replace_fmt)

    def _set_replace_fmt(self, value) -> None:
        value = find.clean_format(dict(value or {}))
        value.pop("style", None)
        if value != self._replace_fmt:
            self._replace_fmt = value
            self.optionsChanged.emit()

    replaceFormat = Property("QVariantMap", _get_replace_fmt, _set_replace_fmt, notify=optionsChanged)

    @Property(int, notify=resultsChanged)
    def count(self) -> int:
        return len(self._matches)

    @Property(int, notify=resultsChanged)
    def current(self) -> int:
        return self._current

    @Property(bool, notify=resultsChanged)
    def active(self) -> bool:
        return bool(self._query or self._find_fmt)

    @Property(str, notify=resultsChanged)
    def label(self) -> str:
        if not self._query and not self._find_fmt:
            return ""
        if not self._matches:
            return "Brak wyników"
        if self._current < 0:
            n = len(self._matches)
            return f"{n} {'wynik' if n == 1 else 'wyniki' if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else 'wyników'}"
        return f"{self._current + 1} z {len(self._matches)}"

    # --- wyszukiwanie -----------------------------------------------------------------
    def _schedule(self) -> None:
        if self._query or self._find_fmt:
            self._timer.start()

    def _refresh(self) -> None:
        self._matches = find_matches(self._doc.state.blocks, self._query, self._case, self._whole,
                                     self._find_fmt) if self._doc else []
        if self._current >= len(self._matches):
            self._current = len(self._matches) - 1
        self.resultsChanged.emit()

    def _ensure_fresh(self) -> None:
        if self._timer.isActive():
            self._timer.stop()
        if self._doc is not None:
            self._doc.flush()
        self._refresh()

    def _go(self, index: int) -> None:
        if not self._matches or self._doc is None:
            return
        self._current = index % len(self._matches)
        m = self._matches[self._current]
        self.resultsChanged.emit()
        self._doc.requestFocus(m.block_id, m.start, m.end, m.row, m.col)

    @Slot()
    def next(self) -> None:  # noqa: A003
        self._ensure_fresh()
        self._go(self._current + 1)

    @Slot()
    def previous(self) -> None:
        self._ensure_fresh()
        self._go(self._current - 1 if self._current >= 0 else -1)

    @Slot()
    def clear(self) -> None:
        self._set_query("")

    @Slot()
    def clearFormats(self) -> None:
        self._set_find_fmt({})
        self._set_replace_fmt({})

    # --- zamiana ----------------------------------------------------------------------
    @Slot(result=bool)
    def replaceCurrent(self) -> bool:
        """Zamienia bieżący wynik (albo przechodzi do pierwszego) i idzie do następnego."""
        self._ensure_fresh()
        if not self._matches or self._doc is None:
            return False
        if self._current < 0:
            self._go(0)
            return False
        m = self._matches[self._current]
        replaced = self._doc.applyReplace([m], self._replacement, self._replace_fmt, "Zamień")
        self._refresh()
        if self._matches:
            # Kolejny wynik za miejscem zamiany (w kolejności dokumentu).
            order = {b.id: i for i, b in enumerate(self._doc.state.blocks)}
            key = (order.get(m.block_id, 0), m.row, m.col, m.start + len(self._replacement))
            nxt = next((k for k, x in enumerate(self._matches)
                        if (order.get(x.block_id, 0), x.row, x.col, x.start) >= key), 0)
            self._go(nxt)
        else:
            self._current = -1
            self.resultsChanged.emit()
        return replaced > 0

    @Slot(result=int)
    def replaceAll(self) -> int:
        self._ensure_fresh()
        if not self._matches or self._doc is None:
            return 0
        count = self._doc.applyReplace(list(self._matches), self._replacement, self._replace_fmt, "Zamień wszystko")
        self._current = -1
        self._refresh()
        return count
