"""Import HTML (schowek z edytorów tekstu i przeglądarek) do bloków dokumentu.

HTML przepuszczamy przez ``QTextDocument`` (Qt rozumie nagłówki, listy, tabele,
formatowanie znaków), a potem zamieniamy jego strukturę na nasze bloki.
Listy z edytorów tekstu bywają „udawane” (akapity z ``mso-list`` i ręcznym znacznikiem)
– zamieniamy je wcześniej na prawdziwe ``<ul>/<ol>``.
"""
from __future__ import annotations

import base64
import html as html_lib
import os
import re
from dataclasses import replace
from typing import Callable
from urllib.parse import unquote, urlparse

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QTextDocument, QTextListFormat, QTextTable

from ..model.blocks import (Block, ParagraphFormat, TableCell, TableData, TextRun, normalize_runs,
                            runs_from_json)
from .qt_text import OBJECT_REPLACEMENT, block_runs

KEEP_IN_MERGE = {"text", "bold", "italic", "underline", "strike", "link", "vertical", "smallCaps"}

def _alignment(flags) -> str:
    if flags & Qt.AlignmentFlag.AlignJustify:
        return "justify"
    if flags & Qt.AlignmentFlag.AlignHCenter:
        return "center"
    if flags & Qt.AlignmentFlag.AlignRight:
        return "right"
    return "left"

_LIST_STYLES = {
    QTextListFormat.Style.ListDisc: ("bullet", "disc"),
    QTextListFormat.Style.ListCircle: ("bullet", "circle"),
    QTextListFormat.Style.ListSquare: ("bullet", "square"),
    QTextListFormat.Style.ListDecimal: ("number", "decimal"),
    QTextListFormat.Style.ListLowerAlpha: ("number", "lowerAlpha"),
    QTextListFormat.Style.ListUpperAlpha: ("number", "upperAlpha"),
    QTextListFormat.Style.ListLowerRoman: ("number", "lowerRoman"),
    QTextListFormat.Style.ListUpperRoman: ("number", "upperRoman"),
}

_MSO_PARA = re.compile(r"<p\b([^>]*mso-list:[^>]*)>(.*?)</p>", re.IGNORECASE | re.DOTALL)
_MSO_IGNORE = re.compile(
    r"(?:<!--\[if !supportLists\]-->|<!\[if !supportLists\]>)(.*?)(?:<!--\[endif\]-->|<!\[endif\]>)",
    re.IGNORECASE | re.DOTALL)


def _convert_word_lists(html: str) -> str:
    def repl(match: re.Match) -> str:
        attrs, inner = match.group(1), match.group(2)
        level_match = re.search(r"level(\d+)", attrs)
        level = int(level_match.group(1)) if level_match else 1
        marker_html = ""
        m = _MSO_IGNORE.search(inner)
        if m:
            marker_html = m.group(1)
            inner = inner[:m.start()] + inner[m.end():]
        marker = html_lib.unescape(re.sub(r"<[^>]+>", "", marker_html)).replace(" ", " ").strip()
        tag, kind = "ul", ""
        if re.match(r"^[0-9]+[.)]?$", marker):
            tag = "ol"
        elif re.match(r"^[ivxlcdm]+[.)]$", marker):
            tag, kind = "ol", "i"
        elif re.match(r"^[IVXLCDM]+[.)]$", marker):
            tag, kind = "ol", "I"
        elif re.match(r"^[a-z][.)]$", marker):
            tag, kind = "ol", "a"
        elif re.match(r"^[A-Z][.)]$", marker):
            tag, kind = "ol", "A"
        type_attr = f' type="{kind}"' if kind else ""
        return f'<{tag}{type_attr} style="-qt-list-indent:{level}"><li>{inner}</li></{tag}>'
    return _MSO_PARA.sub(repl, html)


def _clean_runs(runs: list[dict], mode: str) -> tuple:
    if mode == "merge":
        runs = [{k: v for k, v in r.items() if k in KEEP_IN_MERGE} for r in runs]
    return normalize_runs(runs_from_json(runs))


def _image_from_name(name: str, store_image: Callable[[QImage], str] | None) -> str:
    if name.startswith("data:"):
        try:
            payload = base64.b64decode(name.split(",", 1)[1])
        except (IndexError, ValueError):
            return ""
        image = QImage.fromData(payload)
        return store_image(image) if store_image and not image.isNull() else ""
    if name.startswith("file:"):
        path = unquote(urlparse(name).path)
        if re.match(r"^/[A-Za-z]:", path):
            path = path[1:]
        return path if os.path.exists(path) else ""
    return name if os.path.isabs(name) and os.path.exists(name) else ""


class _Importer:
    def __init__(self, mode: str, store_image: Callable[[QImage], str] | None) -> None:
        self.mode = mode
        self.store_image = store_image
        self.blocks: list[Block] = []

    def paragraph(self, block) -> None:
        align = _alignment(block.blockFormat().alignment())
        # Obrazy wewnątrz akapitu stają się osobnymi blokami.
        runs: list[dict] = []
        it = block.begin()
        while not it.atEnd():
            frag = it.fragment()
            fmt = frag.charFormat()
            if fmt.isImageFormat():
                self._flush_text(block, runs, align)
                runs = []
                path = _image_from_name(fmt.toImageFormat().name(), self.store_image)
                if path:
                    self.blocks.append(Block.new_image(path))
            else:
                text = frag.text().replace(" ", "\n").replace(OBJECT_REPLACEMENT, "")
                if text:
                    runs.extend(block_runs(block, frag.position(), frag.position() + frag.length()))
            it += 1
        self._flush_text(block, runs, align)

    def _flush_text(self, block, runs: list[dict], align: str) -> None:
        clean = _clean_runs(runs, self.mode)
        level = block.blockFormat().headingLevel()
        text_list = block.textList()
        if 1 <= level <= 6:
            if not clean:
                return
            # Pogrubienie wynikające z samego nagłówka HTML jest już w stylu – nie zapisujemy go jawnie.
            clean = tuple(replace(r, bold=None) if r.bold else r for r in clean)
            b = Block.heading(level, runs=normalize_runs(clean))
            self.blocks.append(replace(b, para=replace(b.para, align=align)))
            return
        if text_list is not None:
            kind, style = _LIST_STYLES.get(text_list.format().style(), ("bullet", ""))
            indent = max(0, text_list.format().indent() - 1)
            self.blocks.append(Block.paragraph(runs=clean, para=ParagraphFormat(
                list=kind, list_style=style if style not in ("disc", "decimal") else "", indent=min(indent, 8))))
            return
        self.blocks.append(Block.paragraph(runs=clean, para=ParagraphFormat(align=align)))

    def table(self, table: QTextTable) -> None:
        rows, cols = table.rows(), table.columns()
        grid = [[TableCell() for _ in range(cols)] for _ in range(rows)]
        for r in range(rows):
            for c in range(cols):
                cell = table.cellAt(r, c)
                if cell.row() != r or cell.column() != c:
                    continue
                runs: list[dict] = []
                block = cell.firstCursorPosition().block()
                end = cell.lastCursorPosition().position()
                first = True
                while block.isValid() and block.position() <= end:
                    if not first:
                        runs.append({"text": "\n"})
                    runs.extend(block_runs(block))
                    first = False
                    block = block.next()
                grid[r][c] = TableCell(runs=_clean_runs(runs, self.mode), row_span=cell.rowSpan(),
                                       col_span=cell.columnSpan())
        data = TableData(cells=tuple(tuple(row) for row in grid), header_row=False).normalized()
        self.blocks.append(Block(id=Block.new_table(1, 1).id, type="table", table=data))

    def frame(self, frame) -> None:
        it = frame.begin()
        while not it.atEnd():
            child = it.currentFrame()
            if child is not None:
                if isinstance(child, QTextTable):
                    self.table(child)
                else:
                    self.frame(child)
            else:
                block = it.currentBlock()
                if block.isValid():
                    self.paragraph(block)
            it += 1


def html_to_blocks(html: str, mode: str = "source",
                   store_image: Callable[[QImage], str] | None = None) -> tuple:
    """mode: "source" – formatowanie źródła, "merge" – tylko struktura i wyróżnienia."""
    doc = QTextDocument()
    doc.setHtml(_convert_word_lists(html))
    importer = _Importer(mode, store_image)
    importer.frame(doc.rootFrame())
    # Qt dokleja pusty akapit za każdą tabelą – usuwamy go.
    blocks = [b for i, b in enumerate(importer.blocks)
              if not (b.type == "paragraph" and not b.runs and i > 0 and importer.blocks[i - 1].type == "table")]
    # Puste akapity na brzegach fragmentu (typowe dla schowka) pomijamy.
    while blocks and blocks[0].type == "paragraph" and not blocks[0].runs:
        blocks.pop(0)
    while blocks and blocks[-1].type == "paragraph" and not blocks[-1].runs:
        blocks.pop()
    return tuple(blocks)


def text_to_blocks(text: str) -> tuple:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return tuple(Block.paragraph(line) for line in lines) or (Block.paragraph(),)


def blocks_plain_runs(blocks: tuple) -> tuple:
    """Spłaszcza bloki do jednej listy przebiegów (wklejanie do komórki tabeli)."""
    out: list[TextRun] = []
    for i, b in enumerate(blocks):
        if i:
            out.append(TextRun(text="\n"))
        if b.is_text:
            out.extend(b.runs)
        else:
            text = b.plain_text()
            if text:
                out.append(TextRun(text=text))
    return normalize_runs(out)


__all__ = ["html_to_blocks", "text_to_blocks", "blocks_plain_runs"]
