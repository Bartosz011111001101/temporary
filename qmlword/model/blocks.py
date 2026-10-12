"""Typowany, niemutowalny model bloków dokumentu.

Każdy blok i jego części są zamrożonymi dataclassami. Zmiana bloku oznacza
utworzenie nowego obiektu (``dataclasses.replace``), dzięki czemu migawki
stanu do cofania/ponawiania współdzielą niezmienione bloki.
"""
from __future__ import annotations

import math
import re
import secrets
from dataclasses import dataclass, field, replace
from typing import Any, Iterable

MAX_HEADING_LEVEL = 6
MAX_INDENT = 8

ALIGNMENTS = ("left", "center", "right", "justify")
LIST_TYPES = ("none", "bullet", "number")
BULLET_STYLES = ("disc", "circle", "square")
NUMBER_STYLES = ("decimal", "decimalParen", "lowerAlpha", "upperAlpha", "lowerRoman", "upperRoman", "multilevel")
VERTICAL_ALIGNS = ("super", "sub")
TAB_ALIGNS = ("left", "center", "right", "decimal")
TAB_LEADERS = ("none", "dot", "dash", "line")
BORDER_KINDS = ("none", "box", "top", "bottom", "topBottom", "left")
IMAGE_WRAPS = ("inline", "left", "right")
TABLE_STYLES = ("grid", "light", "striped", "accent", "plain")
CELL_BORDERS = ("", "none", "thin", "thick")
PARAGRAPH_STYLES = ("body", "title")

PARAGRAPH = "paragraph"
HEADING = "heading"
TABLE = "table"
IMAGE = "image"
CAPTION = "caption"
PAGE_BREAK = "pageBreak"
PLACEHOLDER = "placeholder"
UNKNOWN = "unknown"

KNOWN_TYPES = (PARAGRAPH, HEADING, TABLE, IMAGE, CAPTION, PAGE_BREAK, PLACEHOLDER)
TEXT_TYPES = (PARAGRAPH, HEADING)
CAPTIONABLE_TYPES = (TABLE, IMAGE)

_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def generate_id() -> str:
    return "b" + secrets.token_hex(6)


def sanitize_color(value: Any) -> str:
    if isinstance(value, str) and _COLOR_RE.match(value):
        return value.lower()
    return ""


def clamp_number(value: Any, lo: float, hi: float, fallback: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return fallback
    if math.isnan(value) or math.isinf(value):
        return fallback
    return max(lo, min(hi, float(value)))


def clamp_int(value: Any, lo: int, hi: int, fallback: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return fallback
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return fallback
    return max(lo, min(hi, int(value)))


def _opt_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _str(value: Any, default: str = "") -> str:
    return value if isinstance(value, str) else default


def _cell_border(value: Any) -> str:
    return value if value in CELL_BORDERS else ""


# ---------------------------------------------------------------------------
# Tekst sformatowany
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TextRun:
    """Fragment tekstu o jednolitym formacie. Wartości puste = dziedzicz ze stylu."""

    text: str = ""
    bold: bool | None = None
    italic: bool | None = None
    underline: bool | None = None
    strike: bool | None = None
    color: str = ""
    highlight: str = ""
    font_family: str = ""
    font_size: float = 0.0
    link: str = ""
    vertical: str = ""            # "" | "super" | "sub"
    small_caps: bool | None = None

    def format_key(self) -> tuple:
        return (self.bold, self.italic, self.underline, self.strike, self.color,
                self.highlight, self.font_family, round(self.font_size, 2), self.link,
                self.vertical, self.small_caps)

    def same_format(self, other: "TextRun") -> bool:
        return self.format_key() == other.format_key()

    def to_json(self) -> dict:
        out: dict[str, Any] = {"text": self.text}
        for key in ("bold", "italic", "underline", "strike"):
            value = getattr(self, key)
            if value is not None:
                out[key] = value
        if self.color:
            out["color"] = self.color
        if self.highlight:
            out["highlight"] = self.highlight
        if self.font_family:
            out["fontFamily"] = self.font_family
        if self.font_size > 0:
            out["fontSize"] = self.font_size
        if self.link:
            out["link"] = self.link
        if self.vertical:
            out["vertical"] = self.vertical
        if self.small_caps is not None:
            out["smallCaps"] = self.small_caps
        return out

    @staticmethod
    def from_json(data: Any) -> "TextRun":
        if isinstance(data, str):
            return TextRun(text=data)
        if not isinstance(data, dict):
            return TextRun()
        size = clamp_number(data.get("fontSize"), 4, 144, 0.0)
        return TextRun(
            text=_str(data.get("text")),
            bold=_opt_bool(data.get("bold")),
            italic=_opt_bool(data.get("italic")),
            underline=_opt_bool(data.get("underline")),
            strike=_opt_bool(data.get("strike")),
            color=sanitize_color(data.get("color")),
            highlight=sanitize_color(data.get("highlight")),
            font_family=_str(data.get("fontFamily"))[:128],
            font_size=size,
            link=_str(data.get("link")),
            vertical=data.get("vertical") if data.get("vertical") in VERTICAL_ALIGNS else "",
            small_caps=_opt_bool(data.get("smallCaps")),
        )


Runs = tuple  # tuple[TextRun, ...]


def normalize_runs(runs: Iterable[TextRun]) -> tuple:
    """Usuwa puste przebiegi i scala sąsiednie o identycznym formacie."""
    out: list[TextRun] = []
    for run in runs:
        if not run.text:
            continue
        if out and out[-1].same_format(run):
            out[-1] = replace(out[-1], text=out[-1].text + run.text)
        else:
            out.append(run)
    return tuple(out)


def runs_to_json(runs: Iterable[TextRun]) -> list:
    return [r.to_json() for r in runs]


def runs_from_json(data: Any) -> tuple:
    if not isinstance(data, list):
        return ()
    return normalize_runs(TextRun.from_json(item) for item in data)


def plain_text(runs: Iterable[TextRun]) -> str:
    return "".join(r.text for r in runs)


def plain_runs(text: str) -> tuple:
    return (TextRun(text=text),) if text else ()


# ---------------------------------------------------------------------------
# Akapit
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TabStop:
    position: float = 0.0       # mm od lewej krawędzi tekstu akapitu
    align: str = "left"         # left | center | right | decimal
    leader: str = "none"        # none | dot | dash | line

    def to_json(self) -> dict:
        return {"position": self.position, "align": self.align, "leader": self.leader}

    @staticmethod
    def from_json(data: Any) -> "TabStop | None":
        if not isinstance(data, dict):
            return None
        pos = clamp_number(data.get("position"), 0, 500, -1)
        if pos < 0:
            return None
        align, leader = data.get("align"), data.get("leader")
        return TabStop(position=round(pos, 2), align=align if align in TAB_ALIGNS else "left",
                       leader=leader if leader in TAB_LEADERS else "none")


@dataclass(frozen=True)
class ParagraphFormat:
    align: str = "left"
    indent: int = 0             # poziom listy / wcięcia, 1 poziom = 1,25 cm
    space_before: float = 0.0   # pt
    space_after: float = 6.0    # pt
    line_height: float = 1.15   # mnożnik
    list: str = "none"          # none | bullet | number
    list_style: str = ""        # punktory: disc|circle|square, numeracja: decimal|decimalParen|…|multilevel
    list_start: int = 0         # >0 – numeracja zaczyna się od tej liczby
    list_continue: bool = False  # kontynuuj numerację mimo przerwy w liście
    left_mm: float = 0.0        # dodatkowe wcięcie z lewej
    right_mm: float = 0.0       # wcięcie z prawej
    first_line_mm: float = 0.0  # >0 wcięcie pierwszego wiersza, <0 wysunięcie (hanging)
    tabs: tuple = ()            # tuple[TabStop, ...]
    border: str = "none"        # none | box | top | bottom | topBottom | left
    border_color: str = "#5b6570"
    border_width: float = 0.75  # pt
    shading: str = ""           # kolor tła akapitu

    def to_json(self) -> dict:
        out = {
            "align": self.align,
            "indent": self.indent,
            "spaceBefore": self.space_before,
            "spaceAfter": self.space_after,
            "lineHeight": self.line_height,
            "list": self.list,
        }
        # Pola rozszerzone zapisujemy tylko, gdy różnią się od domyślnych (czytelny plik).
        if self.list_style:
            out["listStyle"] = self.list_style
        if self.list_start:
            out["listStart"] = self.list_start
        if self.list_continue:
            out["listContinue"] = True
        if self.left_mm:
            out["leftMm"] = self.left_mm
        if self.right_mm:
            out["rightMm"] = self.right_mm
        if self.first_line_mm:
            out["firstLineMm"] = self.first_line_mm
        if self.tabs:
            out["tabs"] = [t.to_json() for t in self.tabs]
        if self.border != "none":
            out["border"] = {"kind": self.border, "color": self.border_color, "width": self.border_width}
        if self.shading:
            out["shading"] = self.shading
        return out

    @staticmethod
    def from_json(data: Any, defaults: "ParagraphFormat | None" = None) -> "ParagraphFormat":
        d = defaults or ParagraphFormat()
        if not isinstance(data, dict):
            return d
        align = data.get("align")
        lst = data.get("list")
        lst = lst if lst in LIST_TYPES else d.list
        style = data.get("listStyle")
        allowed = BULLET_STYLES if lst == "bullet" else NUMBER_STYLES if lst == "number" else ()
        border = data.get("border") if isinstance(data.get("border"), dict) else {}
        kind = border.get("kind")
        tabs = data.get("tabs")
        stops = sorted((t for t in (TabStop.from_json(x) for x in tabs) if t is not None),
                       key=lambda t: t.position) if isinstance(tabs, list) else list(d.tabs)
        return ParagraphFormat(
            align=align if align in ALIGNMENTS else d.align,
            indent=clamp_int(data.get("indent"), 0, MAX_INDENT, d.indent),
            space_before=clamp_number(data.get("spaceBefore"), 0, 144, d.space_before),
            space_after=clamp_number(data.get("spaceAfter"), 0, 144, d.space_after),
            line_height=clamp_number(data.get("lineHeight"), 0.8, 4.0, d.line_height),
            list=lst,
            list_style=style if style in allowed else "",
            list_start=clamp_int(data.get("listStart"), 0, 9999, 0),
            list_continue=data.get("listContinue") is True,
            left_mm=clamp_number(data.get("leftMm"), -50, 200, 0.0),
            right_mm=clamp_number(data.get("rightMm"), -50, 200, 0.0),
            first_line_mm=clamp_number(data.get("firstLineMm"), -100, 100, 0.0),
            tabs=tuple(stops[:32]),
            border=kind if kind in BORDER_KINDS else "none",
            border_color=sanitize_color(border.get("color")) or d.border_color,
            border_width=clamp_number(border.get("width"), 0.25, 6, d.border_width),
            shading=sanitize_color(data.get("shading")),
        )


def default_paragraph_format(block_type: str, style: str = "body") -> ParagraphFormat:
    if block_type == HEADING:
        return ParagraphFormat(space_before=14, space_after=4, line_height=1.1)
    if style == "title":
        return ParagraphFormat(space_before=0, space_after=14, line_height=1.0)
    return ParagraphFormat()


# ---------------------------------------------------------------------------
# Tabela
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TableCell:
    runs: tuple = ()
    align: str = "left"
    row_span: int = 1
    col_span: int = 1
    background: str = ""
    border_top: str = ""        # "" = wg stylu tabeli | none | thin | thick
    border_bottom: str = ""
    border_left: str = ""
    border_right: str = ""
    formula: str = ""           # np. "=SUMA(POWYŻEJ)"; wynik trafia do runs

    def to_json(self) -> dict:
        out: dict[str, Any] = {"runs": runs_to_json(self.runs)}
        borders = {k: v for k, v in (("top", self.border_top), ("bottom", self.border_bottom),
                                     ("left", self.border_left), ("right", self.border_right)) if v}
        if borders:
            out["borders"] = borders
        if self.formula:
            out["formula"] = self.formula
        if self.align != "left":
            out["align"] = self.align
        if self.row_span > 1:
            out["rowSpan"] = self.row_span
        if self.col_span > 1:
            out["colSpan"] = self.col_span
        if self.background:
            out["background"] = self.background
        return out

    @staticmethod
    def from_json(data: Any) -> "TableCell":
        if not isinstance(data, dict):
            return TableCell()
        align = data.get("align")
        borders = data.get("borders") if isinstance(data.get("borders"), dict) else {}
        return TableCell(
            runs=runs_from_json(data.get("runs")),
            align=align if align in ALIGNMENTS else "left",
            row_span=clamp_int(data.get("rowSpan"), 1, 1000, 1),
            col_span=clamp_int(data.get("colSpan"), 1, 1000, 1),
            background=sanitize_color(data.get("background")),
            border_top=_cell_border(borders.get("top")),
            border_bottom=_cell_border(borders.get("bottom")),
            border_left=_cell_border(borders.get("left")),
            border_right=_cell_border(borders.get("right")),
            formula=_str(data.get("formula"))[:500],
        )


@dataclass(frozen=True)
class TableData:
    cells: tuple = ()           # tuple[tuple[TableCell, ...], ...]
    col_widths: tuple = ()      # udziały szerokości, suma = 1
    row_heights: tuple = ()     # minimalna wysokość wiersza w px (0 = auto)
    header_row: bool = True
    repeat_header: bool = True
    style: str = "grid"         # grid | light | striped | accent | plain
    banded_rows: bool = False   # co drugi wiersz z tłem
    first_column: bool = False  # pogrubiona pierwsza kolumna

    @property
    def rows(self) -> int:
        return len(self.cells)

    @property
    def cols(self) -> int:
        return len(self.cells[0]) if self.cells else 0

    @staticmethod
    def create(rows: int, cols: int, header_row: bool = True) -> "TableData":
        rows = clamp_int(rows, 1, 500, 2)
        cols = clamp_int(cols, 1, 50, 2)
        cells = tuple(tuple(TableCell() for _ in range(cols)) for _ in range(rows))
        return TableData(cells=cells, header_row=header_row).normalized()

    def anchor_of(self, r: int, c: int) -> tuple[int, int]:
        """Zwraca kotwicę scalenia obejmującego (r, c) albo samo (r, c)."""
        for ar in range(r + 1):
            for ac in range(c + 1):
                cell = self.cells[ar][ac]
                if (ar, ac) != (r, c) and (cell.row_span > 1 or cell.col_span > 1) \
                        and ar + cell.row_span > r and ac + cell.col_span > c:
                    return ar, ac
        return r, c

    def coverage(self) -> list[list[tuple[int, int]]]:
        """Macierz kotwic: dla każdej komórki (r, c) współrzędne jej kotwicy."""
        cov = [[(r, c) for c in range(self.cols)] for r in range(self.rows)]
        for r in range(self.rows):
            for c in range(self.cols):
                if cov[r][c] != (r, c):
                    continue
                cell = self.cells[r][c]
                for rr in range(r, min(self.rows, r + cell.row_span)):
                    for cc in range(c, min(self.cols, c + cell.col_span)):
                        if (rr, cc) != (r, c):
                            cov[rr][cc] = (r, c)
        return cov

    def is_covered(self, r: int, c: int) -> bool:
        return self.coverage()[r][c] != (r, c)

    def normalized(self) -> "TableData":
        rows = [list(row) for row in self.cells] or [[TableCell()]]
        ncols = max(1, max(len(row) for row in rows))
        for row in rows:
            while len(row) < ncols:
                row.append(TableCell())
        nrows = len(rows)

        # Rozwiązywanie nakładających się scaleń w kolejności czytania.
        taken = [[False] * ncols for _ in range(nrows)]
        for r in range(nrows):
            for c in range(ncols):
                cell = rows[r][c]
                if taken[r][c]:
                    if cell.row_span != 1 or cell.col_span != 1:
                        rows[r][c] = replace(cell, row_span=1, col_span=1)
                    continue
                rs = max(1, min(cell.row_span, nrows - r))
                cs = max(1, min(cell.col_span, ncols - c))
                clash = any(taken[rr][cc] for rr in range(r, r + rs) for cc in range(c, c + cs))
                if clash:
                    rs = cs = 1
                if (rs, cs) != (cell.row_span, cell.col_span):
                    rows[r][c] = replace(cell, row_span=rs, col_span=cs)
                for rr in range(r, r + rs):
                    for cc in range(c, c + cs):
                        taken[rr][cc] = True

        widths = list(self.col_widths)
        if len(widths) != ncols:
            widths = [1.0 / ncols] * ncols
        else:
            # Najpierw proporcje, potem minimalna szerokość – zachowuje stosunek kolumn.
            widths = [clamp_number(w, 1e-6, 1e6, 1.0 / ncols) for w in widths]
            total = sum(widths)
            widths = [max(0.02, w / total) for w in widths]
            total = sum(widths)
            widths = [w / total for w in widths]
        heights = list(self.row_heights)[:nrows]
        heights += [0.0] * (nrows - len(heights))
        heights = [clamp_number(h, 0, 2000, 0.0) for h in heights]
        return replace(self,
                       cells=tuple(tuple(row) for row in rows),
                       col_widths=tuple(round(w, 6) for w in widths),
                       row_heights=tuple(heights))

    def to_json(self) -> dict:
        return {
            "rows": self.rows,
            "cols": self.cols,
            "colWidths": list(self.col_widths),
            "rowHeights": list(self.row_heights),
            "headerRow": self.header_row,
            "repeatHeader": self.repeat_header,
            "style": self.style,
            "bandedRows": self.banded_rows,
            "firstColumn": self.first_column,
            "cells": [[cell.to_json() for cell in row] for row in self.cells],
        }

    @staticmethod
    def from_json(data: Any, warnings: list | None = None) -> "TableData":
        if not isinstance(data, dict):
            data = {}
        raw_rows = data.get("cells")
        cells = []
        if isinstance(raw_rows, list):
            for raw_row in raw_rows:
                if isinstance(raw_row, list):
                    cells.append(tuple(TableCell.from_json(c) for c in raw_row))
        cells = [row for row in cells if row]
        if not cells:
            if warnings is not None:
                warnings.append("Tabela bez komórek została zastąpiona pustą tabelą 2×2.")
            return TableData.create(2, 2)
        widths = data.get("colWidths")
        heights = data.get("rowHeights")
        return TableData(
            cells=tuple(cells),
            col_widths=tuple(w for w in widths if isinstance(w, (int, float))) if isinstance(widths, list) else (),
            row_heights=tuple(h for h in heights if isinstance(h, (int, float))) if isinstance(heights, list) else (),
            header_row=data.get("headerRow", True) is not False,
            repeat_header=data.get("repeatHeader", True) is not False,
            style=data.get("style") if data.get("style") in TABLE_STYLES else "grid",
            banded_rows=data.get("bandedRows") is True,
            first_column=data.get("firstColumn") is True,
        ).normalized()


# ---------------------------------------------------------------------------
# Obraz i podpis
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ImageData:
    path: str = ""          # względna do katalogu dokumentu lub bezwzględna
    width: float = 0.6      # ułamek szerokości obszaru tekstu
    align: str = "center"   # left | center | right
    alt: str = ""
    wrap: str = "inline"    # inline | left | right (opływanie tekstem)
    rotation: int = 0       # 0 | 90 | 180 | 270
    crop_left: float = 0.0  # ułamki szerokości/wysokości oryginału
    crop_top: float = 0.0
    crop_right: float = 0.0
    crop_bottom: float = 0.0
    border_width: float = 0.0  # pt, 0 = bez ramki
    border_color: str = "#5b6570"

    @property
    def cropped(self) -> bool:
        return any((self.crop_left, self.crop_top, self.crop_right, self.crop_bottom))

    def to_json(self) -> dict:
        out = {"path": self.path, "width": self.width, "align": self.align, "alt": self.alt}
        if self.wrap != "inline":
            out["wrap"] = self.wrap
        if self.rotation:
            out["rotation"] = self.rotation
        if self.cropped:
            out["crop"] = {"left": self.crop_left, "top": self.crop_top,
                           "right": self.crop_right, "bottom": self.crop_bottom}
        if self.border_width > 0:
            out["border"] = {"width": self.border_width, "color": self.border_color}
        return out

    @staticmethod
    def from_json(data: Any) -> "ImageData":
        if not isinstance(data, dict):
            return ImageData()
        align = data.get("align")
        crop = data.get("crop") if isinstance(data.get("crop"), dict) else {}
        border = data.get("border") if isinstance(data.get("border"), dict) else {}
        rotation = clamp_int(data.get("rotation"), 0, 270, 0)
        left, right = clamp_number(crop.get("left"), 0, 0.9, 0.0), clamp_number(crop.get("right"), 0, 0.9, 0.0)
        top, bottom = clamp_number(crop.get("top"), 0, 0.9, 0.0), clamp_number(crop.get("bottom"), 0, 0.9, 0.0)
        if left + right > 0.9:
            left = right = 0.0
        if top + bottom > 0.9:
            top = bottom = 0.0
        return ImageData(
            path=_str(data.get("path")),
            width=clamp_number(data.get("width"), 0.05, 1.0, 0.6),
            align=align if align in ("left", "center", "right") else "center",
            alt=_str(data.get("alt")),
            wrap=data.get("wrap") if data.get("wrap") in IMAGE_WRAPS else "inline",
            rotation=rotation if rotation in (0, 90, 180, 270) else 0,
            crop_left=left, crop_top=top, crop_right=right, crop_bottom=bottom,
            border_width=clamp_number(border.get("width"), 0, 12, 0.0),
            border_color=sanitize_color(border.get("color")) or "#5b6570",
        )


@dataclass(frozen=True)
class CaptionData:
    target_id: str = ""   # identyfikator tabeli lub obrazu
    text: str = ""

    def to_json(self) -> dict:
        return {"targetId": self.target_id, "text": self.text}

    @staticmethod
    def from_json(data: Any) -> "CaptionData":
        if not isinstance(data, dict):
            return CaptionData()
        return CaptionData(target_id=_str(data.get("targetId")), text=_str(data.get("text")))


# ---------------------------------------------------------------------------
# Blok
# ---------------------------------------------------------------------------

@dataclass(frozen=True, eq=True)
class Block:
    id: str
    type: str = PARAGRAPH
    style: str = "body"                 # akapit: body | title
    level: int = 1                      # nagłówek: 1..MAX_HEADING_LEVEL
    runs: tuple = ()
    description: str = ""               # krótki opis pod nagłówkiem sekcji
    para: ParagraphFormat = ParagraphFormat()
    table: TableData = TableData()
    image: ImageData = ImageData()
    caption: CaptionData = CaptionData()
    raw: Any = field(default=None, compare=True)  # nieznany typ: oryginalny JSON

    __hash__ = None  # bloki porównujemy, ale nie haszujemy

    @property
    def is_text(self) -> bool:
        return self.type in TEXT_TYPES

    @property
    def is_captionable(self) -> bool:
        return self.type in CAPTIONABLE_TYPES

    @property
    def style_key(self) -> str:
        if self.type == HEADING:
            return f"h{self.level}"
        return self.style

    def plain_text(self) -> str:
        if self.type in TEXT_TYPES:
            return plain_text(self.runs)
        if self.type == CAPTION:
            return self.caption.text
        if self.type == TABLE:
            parts = [plain_text(c.runs) for row in self.table.cells for c in row if c.runs]
            return " ".join(parts)
        return ""

    def to_json(self) -> dict:
        if self.type == UNKNOWN:
            out = dict(self.raw or {})
            out["id"] = self.id
            return out
        out: dict[str, Any] = {"id": self.id, "type": self.type}
        if self.type == PARAGRAPH:
            out["style"] = self.style
            out["runs"] = runs_to_json(self.runs)
            out["para"] = self.para.to_json()
        elif self.type == HEADING:
            out["level"] = self.level
            out["runs"] = runs_to_json(self.runs)
            if self.description:
                out["description"] = self.description
            out["para"] = self.para.to_json()
        elif self.type == TABLE:
            out["table"] = self.table.to_json()
        elif self.type == IMAGE:
            out["image"] = self.image.to_json()
        elif self.type == CAPTION:
            out["caption"] = self.caption.to_json()
        return out

    @staticmethod
    def from_json(data: Any, warnings: list | None = None) -> "Block | None":
        if not isinstance(data, dict):
            if warnings is not None:
                warnings.append("Pominięto element listy bloków, który nie jest obiektem.")
            return None
        block_id = _str(data.get("id"))
        btype = data.get("type")
        if not isinstance(btype, str) or not btype:
            if warnings is not None:
                warnings.append("Pominięto blok bez typu.")
            return None
        if btype not in KNOWN_TYPES:
            if warnings is not None:
                warnings.append(f"Nieznany typ bloku „{btype}” – zachowano go bez zmian.")
            return Block(id=block_id, type=UNKNOWN, raw=dict(data))
        if btype == PARAGRAPH:
            style = data.get("style")
            style = style if style in PARAGRAPH_STYLES else "body"
            return Block(id=block_id, type=PARAGRAPH, style=style,
                         runs=runs_from_json(data.get("runs")),
                         para=ParagraphFormat.from_json(data.get("para"), default_paragraph_format(PARAGRAPH, style)))
        if btype == HEADING:
            para = ParagraphFormat.from_json(data.get("para"), default_paragraph_format(HEADING))
            return Block(id=block_id, type=HEADING,
                         level=clamp_int(data.get("level"), 1, MAX_HEADING_LEVEL, 1),
                         runs=runs_from_json(data.get("runs")),
                         description=_str(data.get("description")),
                         para=replace(para, list="none"))
        if btype == TABLE:
            return Block(id=block_id, type=TABLE, table=TableData.from_json(data.get("table"), warnings))
        if btype == IMAGE:
            return Block(id=block_id, type=IMAGE, image=ImageData.from_json(data.get("image")))
        if btype == CAPTION:
            return Block(id=block_id, type=CAPTION, caption=CaptionData.from_json(data.get("caption")))
        return Block(id=block_id, type=btype)

    # --- fabryki ---

    @staticmethod
    def paragraph(text: str = "", style: str = "body", runs: tuple | None = None,
                  para: ParagraphFormat | None = None) -> "Block":
        return Block(id=generate_id(), type=PARAGRAPH, style=style,
                     runs=runs if runs is not None else plain_runs(text),
                     para=para or default_paragraph_format(PARAGRAPH, style))

    @staticmethod
    def heading(level: int, text: str = "", runs: tuple | None = None) -> "Block":
        return Block(id=generate_id(), type=HEADING, level=clamp_int(level, 1, MAX_HEADING_LEVEL, 1),
                     runs=runs if runs is not None else plain_runs(text),
                     para=default_paragraph_format(HEADING))

    @staticmethod
    def new_table(rows: int, cols: int, header_row: bool = True) -> "Block":
        return Block(id=generate_id(), type=TABLE, table=TableData.create(rows, cols, header_row))

    @staticmethod
    def new_image(path: str) -> "Block":
        return Block(id=generate_id(), type=IMAGE, image=ImageData(path=path))

    @staticmethod
    def new_caption(target_id: str, text: str = "") -> "Block":
        return Block(id=generate_id(), type=CAPTION, caption=CaptionData(target_id=target_id, text=text))

    @staticmethod
    def page_break() -> "Block":
        return Block(id=generate_id(), type=PAGE_BREAK)

    @staticmethod
    def placeholder() -> "Block":
        return Block(id=generate_id(), type=PLACEHOLDER)


def deep_merge(base: dict, patch: dict) -> dict:
    out = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out
