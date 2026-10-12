"""Natywny format dokumentu: czytelny, wersjonowany JSON."""
from __future__ import annotations

import json
from typing import Any

from ..model.blocks import Block
from ..model.document import DocumentData, DocumentMeta, PageSettings
from ..model.ops import normalize_document

FORMAT_ID = "qmlword-document"
SCHEMA_VERSION = 1
FILE_EXTENSION = "qwd.json"


class DocumentFormatError(Exception):
    """Błąd odczytu pliku z komunikatem dla użytkownika."""


def to_json_dict(doc: DocumentData) -> dict:
    return {
        "format": FORMAT_ID,
        "schemaVersion": SCHEMA_VERSION,
        "meta": doc.meta.to_json(),
        "page": doc.page.to_json(),
        "blocks": [b.to_json() for b in doc.blocks],
    }


def serialize(doc: DocumentData) -> bytes:
    return json.dumps(to_json_dict(doc), ensure_ascii=False, indent=2).encode("utf-8")


# Migracje: wersja -> funkcja podnosząca dane o jedną wersję.
MIGRATIONS: dict[int, Any] = {}


def from_json_dict(data: Any, warnings: list[str] | None = None) -> DocumentData:
    if warnings is None:
        warnings = []
    if not isinstance(data, dict):
        raise DocumentFormatError("Plik nie zawiera obiektu dokumentu.")
    fmt = data.get("format")
    if fmt is not None and fmt != FORMAT_ID:
        raise DocumentFormatError(f"To nie jest dokument tej aplikacji (format „{fmt}”).")
    if fmt is None:
        if "blocks" not in data:
            raise DocumentFormatError("Plik nie zawiera listy bloków dokumentu.")
        warnings.append("Brak identyfikatora formatu – plik wczytano na próbę.")

    version = data.get("schemaVersion", 1)
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        warnings.append("Nieprawidłowa wersja schematu – przyjęto wersję 1.")
        version = 1
    while version < SCHEMA_VERSION:
        migrate = MIGRATIONS.get(version)
        if migrate is None:
            break
        data = migrate(data)
        version += 1
    if version > SCHEMA_VERSION:
        warnings.append(
            f"Dokument zapisano w nowszej wersji formatu ({version}). "
            "Nieznane elementy zostaną zachowane, ale mogą nie być widoczne.")

    raw_blocks = data.get("blocks")
    if not isinstance(raw_blocks, list):
        raise DocumentFormatError("Lista bloków dokumentu jest uszkodzona.")
    blocks = []
    for item in raw_blocks:
        block = Block.from_json(item, warnings)
        if block is not None:
            blocks.append(block)
    blocks = normalize_document(tuple(blocks), warnings)
    # Ostrzeżenia mogą się powtarzać dla wielu bloków – zostawiamy unikalne.
    unique = list(dict.fromkeys(warnings))
    warnings.clear()
    warnings.extend(unique)
    return DocumentData(
        meta=DocumentMeta.from_json(data.get("meta")),
        page=PageSettings.from_json(data.get("page")),
        blocks=blocks,
    )


def parse(raw: bytes, warnings: list[str] | None = None) -> DocumentData:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DocumentFormatError("Plik nie jest poprawnym tekstem UTF-8.") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DocumentFormatError(
            f"Plik jest uszkodzony (błąd JSON w wierszu {exc.lineno}, kolumnie {exc.colno}).") from exc
    return from_json_dict(data, warnings)
