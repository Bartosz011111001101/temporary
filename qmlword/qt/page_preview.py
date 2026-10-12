"""Podgląd stron: te same strony, które trafią do PDF (pełna paginacja Qt)."""
from __future__ import annotations

from PySide6.QtCore import Property, QObject, QRectF, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtQml import QmlElement
from PySide6.QtQuick import QQuickPaintedItem

from ..io.text_document_builder import PagedDocument
from .document_model import DocumentModel

QML_IMPORT_NAME = "QmlWord.Backend"
QML_IMPORT_MAJOR_VERSION = 1

PREVIEW_DPI = 96.0


@QmlElement
class PageLayout(QObject):
    """Buduje (leniwie) spaginowany dokument dla bieżącej rewizji modelu."""

    documentChanged = Signal()
    layoutChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._doc: DocumentModel | None = None
        self._paged: PagedDocument | None = None
        self._revision = -1
        self._active = False
        self._device = QImage(1, 1, QImage.Format.Format_ARGB32)
        self._device.setDotsPerMeterX(round(PREVIEW_DPI / 0.0254))
        self._device.setDotsPerMeterY(round(PREVIEW_DPI / 0.0254))

    def _get_document(self):
        return self._doc

    def _set_document(self, doc) -> None:
        if doc is self._doc:
            return
        if self._doc is not None:
            try:
                self._doc.revisionChanged.disconnect(self._invalidate)
            except (RuntimeError, TypeError):  # źródło już zniszczone (zamykanie aplikacji)
                pass
        self._doc = doc
        if doc is not None:
            doc.revisionChanged.connect(self._invalidate)
        self._invalidate()
        self.documentChanged.emit()

    document = Property(QObject, _get_document, _set_document, notify=documentChanged)

    def _get_active(self) -> bool:
        return self._active

    def _set_active(self, value: bool) -> None:
        if value != self._active:
            self._active = value
            self.layoutChanged.emit()

    # Liczymy układ tylko gdy podgląd jest widoczny (budowa kosztuje przy długich dokumentach).
    active = Property(bool, _get_active, _set_active, notify=layoutChanged)

    def _invalidate(self) -> None:
        self._paged = None
        if self._active:
            self.layoutChanged.emit()

    def paged(self) -> PagedDocument | None:
        if self._doc is None:
            return None
        if self._paged is None or self._revision != self._doc.revision:
            self._paged = PagedDocument(self._doc.state, self._doc.base_dir, PREVIEW_DPI, self._device)
            self._revision = self._doc.revision
        return self._paged

    @Property(int, notify=layoutChanged)
    def pageCount(self) -> int:
        if not self._active:
            return 0
        paged = self.paged()
        return paged.page_count() if paged else 0

    @Property(float, notify=layoutChanged)
    def pageWidth(self) -> float:
        paged = self.paged() if self._active else None
        return paged.page_width if paged else 794.0

    @Property(float, notify=layoutChanged)
    def pageHeight(self) -> float:
        paged = self.paged() if self._active else None
        return paged.page_height if paged else 1123.0

    @Slot()
    def refresh(self) -> None:
        self._paged = None
        self.layoutChanged.emit()


@QmlElement
class PagePreview(QQuickPaintedItem):
    """Jedna strona podglądu.

    Stronę rysujemy do ``QImage`` w wątku GUI (``_render``), a ``paint()`` – wołane
    przez Qt z wątku renderującego – tylko kopiuje gotowy obraz. Dzięki temu wątek
    renderujący nie dotyka ``QTextDocument`` i nie czeka na interpreter Pythona.
    """

    layoutObjectChanged = Signal()
    pageIndexChanged = Signal()
    pixelRatioChanged = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._layout: PageLayout | None = None
        self._page = 0
        self._ratio = 1.0
        self._image = QImage()
        self._pending = False
        self.setAntialiasing(True)
        self.setFillColor(QColor("white"))
        self.widthChanged.connect(self._schedule)
        self.heightChanged.connect(self._schedule)

    def _get_layout(self):
        return self._layout

    def _set_layout(self, layout) -> None:
        if layout is self._layout:
            return
        if self._layout is not None:
            self._layout.layoutChanged.disconnect(self._schedule)
        self._layout = layout
        if layout is not None:
            layout.layoutChanged.connect(self._schedule)
        self.layoutObjectChanged.emit()
        self._schedule()

    pageLayout = Property(QObject, _get_layout, _set_layout, notify=layoutObjectChanged)

    def _get_page(self) -> int:
        return self._page

    def _set_page(self, value: int) -> None:
        if value != self._page:
            self._page = value
            self.pageIndexChanged.emit()
            self._schedule()

    pageIndex = Property(int, _get_page, _set_page, notify=pageIndexChanged)

    def _get_ratio(self) -> float:
        return self._ratio

    def _set_ratio(self, value: float) -> None:
        value = max(1.0, min(4.0, float(value or 1.0)))
        if value != self._ratio:
            self._ratio = value
            self.pixelRatioChanged.emit()
            self._schedule()

    # Ustawiane z QML (Screen.devicePixelRatio) – bez sięgania po okno z Pythona.
    pixelRatio = Property(float, _get_ratio, _set_ratio, notify=pixelRatioChanged)

    def _schedule(self, *_args) -> None:
        if not self._pending:
            self._pending = True
            QTimer.singleShot(0, self._render)

    def _render(self) -> None:
        self._pending = False
        paged = self._layout.paged() if self._layout is not None and self._layout.active else None
        if paged is None or self._page >= paged.page_count() or self.width() < 2 or self.height() < 2:
            self._image = QImage()
            self.update()
            return
        dpr = self._ratio
        image = QImage(int(self.width() * dpr), int(self.height() * dpr), QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(QColor("white"))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        scale = image.width() / paged.page_width if paged.page_width else 1.0
        painter.scale(scale, scale)
        paged.paint_page(painter, self._page)
        painter.setPen(QColor("#d0d4d9"))
        painter.drawRect(QRectF(0, 0, paged.page_width - 1, paged.page_height - 1))
        painter.end()
        image.setDevicePixelRatio(dpr)
        self._image = image
        self.update()

    def paint(self, painter: QPainter) -> None:
        if not self._image.isNull():
            painter.drawImage(QRectF(0, 0, self.width(), self.height()), self._image)
