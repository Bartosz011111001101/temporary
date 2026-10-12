"""Rejestr formatów plików.

Dodanie nowego formatu (np. DOCX) sprowadza się do napisania klasy
``DocumentImporter`` i/lub ``DocumentExporter`` i dopisania jej do rejestru.
Interfejs QML pobiera filtry plików z rejestru, więc nie trzeba go zmieniać.
"""
from __future__ import annotations

import os
import tempfile
from abc import ABC, abstractmethod

from ..model.document import DocumentData
from . import json_format


class ExportError(Exception):
    """Błąd zapisu/eksportu z komunikatem dla użytkownika."""


class DocumentImporter(ABC):
    format_id: str
    label: str
    extensions: tuple[str, ...]

    @abstractmethod
    def read(self, path: str, warnings: list[str]) -> DocumentData: ...

    def name_filter(self) -> str:
        return f"{self.label} ({' '.join('*.' + e for e in self.extensions)})"


class DocumentExporter(ABC):
    format_id: str
    label: str
    extensions: tuple[str, ...]

    @abstractmethod
    def write(self, doc: DocumentData, path: str, base_dir: str) -> None: ...

    def name_filter(self) -> str:
        return f"{self.label} ({' '.join('*.' + e for e in self.extensions)})"


def atomic_write(path: str, data: bytes) -> None:
    """Zapis przez plik tymczasowy, żeby awaria nie zostawiła połowy dokumentu."""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(prefix=".zapis-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class JsonDocumentFormat(DocumentImporter, DocumentExporter):
    format_id = "json"
    label = "Dokument QmlWord"
    extensions = ("qwd.json", "json")

    def read(self, path: str, warnings: list[str]) -> DocumentData:
        try:
            with open(path, "rb") as fh:
                raw = fh.read()
        except FileNotFoundError as exc:
            raise json_format.DocumentFormatError("Plik nie istnieje.") from exc
        except PermissionError as exc:
            raise json_format.DocumentFormatError("Brak uprawnień do odczytu pliku.") from exc
        except OSError as exc:
            raise json_format.DocumentFormatError(f"Nie można odczytać pliku: {exc.strerror}.") from exc
        return json_format.parse(raw, warnings)

    def write(self, doc: DocumentData, path: str, base_dir: str = "") -> None:
        try:
            atomic_write(path, json_format.serialize(doc))
        except PermissionError as exc:
            raise ExportError("Brak uprawnień do zapisu w tym miejscu.") from exc
        except OSError as exc:
            raise ExportError(f"Nie można zapisać pliku: {exc.strerror or exc}.") from exc


class FormatRegistry:
    def __init__(self) -> None:
        self.importers: list[DocumentImporter] = []
        self.exporters: list[DocumentExporter] = []

    def register_importer(self, importer: DocumentImporter) -> None:
        self.importers.append(importer)

    def register_exporter(self, exporter: DocumentExporter) -> None:
        self.exporters.append(exporter)

    def exporter(self, format_id: str) -> DocumentExporter | None:
        return next((e for e in self.exporters if e.format_id == format_id), None)

    def importer_for(self, path: str) -> DocumentImporter | None:
        lower = path.lower()
        for importer in self.importers:
            if any(lower.endswith("." + ext) for ext in importer.extensions):
                return importer
        return self.importers[0] if self.importers else None


def default_registry() -> FormatRegistry:
    from .pdf_exporter import PdfExporter

    registry = FormatRegistry()
    native = JsonDocumentFormat()
    registry.register_importer(native)
    registry.register_exporter(native)
    registry.register_exporter(PdfExporter())
    return registry
