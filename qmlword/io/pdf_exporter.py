"""Eksport do PDF przez QPdfWriter (bez zewnętrznych zależności)."""
from __future__ import annotations

import os

from PySide6.QtCore import QMarginsF, QSizeF
from PySide6.QtGui import QPageLayout, QPageSize, QPainter, QPdfWriter

from ..model.document import DocumentData
from .formats import DocumentExporter, ExportError
from .text_document_builder import PagedDocument

PAGE_SIZE_IDS = {
    "A4": QPageSize.PageSizeId.A4,
    "A5": QPageSize.PageSizeId.A5,
    "Letter": QPageSize.PageSizeId.Letter,
    "Legal": QPageSize.PageSizeId.Legal,
}
PDF_DPI = 300


class PdfExporter(DocumentExporter):
    format_id = "pdf"
    label = "Dokument PDF"
    extensions = ("pdf",)

    def write(self, doc: DocumentData, path: str, base_dir: str = "") -> None:
        directory = os.path.dirname(os.path.abspath(path))
        if not os.path.isdir(directory):
            raise ExportError("Folder docelowy nie istnieje.")
        if os.path.exists(path) and not os.access(path, os.W_OK):
            raise ExportError("Plik PDF jest tylko do odczytu lub otwarty w innym programie.")

        writer = QPdfWriter(path)
        writer.setResolution(PDF_DPI)
        writer.setCreator("QmlWord")
        writer.setTitle(doc.meta.title or os.path.splitext(os.path.basename(path))[0])
        writer.setPageSize(QPageSize(PAGE_SIZE_IDS.get(doc.page.size, QPageSize.PageSizeId.A4)))
        writer.setPageOrientation(QPageLayout.Orientation.Landscape if doc.page.landscape
                                  else QPageLayout.Orientation.Portrait)
        writer.setPageMargins(QMarginsF(0, 0, 0, 0))

        painter = QPainter()
        if not painter.begin(writer):
            raise ExportError("Nie można utworzyć pliku PDF. Sprawdź, czy nie jest otwarty w innym programie.")
        try:
            paged = PagedDocument(doc, base_dir, PDF_DPI, writer)
            for index in range(paged.page_count()):
                if index and not writer.newPage():
                    raise ExportError("Nie udało się dodać kolejnej strony PDF.")
                paged.paint_page(painter, index)
        finally:
            painter.end()
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            raise ExportError("Plik PDF nie został zapisany.")
