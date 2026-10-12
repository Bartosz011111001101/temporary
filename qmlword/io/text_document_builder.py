"""Buduje QTextDocument z modelu – podstawa eksportu PDF, podglądu stron i HTML do schowka.

QTextDocument sam dzieli treść na strony (``pageSize``), powtarza wiersz nagłówka
tabeli na kolejnych stronach (``headerRowCount``), opływa tekstem pływające ramki
(obrazy z opływaniem) i respektuje wymuszone podziały stron. Wypełnienie tabulatorów
(kropki, kreski) rysujemy sami po ułożeniu tekstu, bo Qt go nie obsługuje.
"""
from __future__ import annotations

import os

from PySide6.QtCore import QPointF, QRectF, QSizeF, Qt, QUrl
from PySide6.QtGui import (QAbstractTextDocumentLayout, QBrush, QColor, QFont, QImage, QPainter,
                           QPalette, QPen, QTextBlockFormat, QTextCharFormat, QTextCursor,
                           QTextDocument, QTextFormat, QTextFrameFormat, QTextImageFormat, QTextLength,
                           QTextListFormat, QTextOption, QTextTableFormat, QTransform)

from ..model import styles, table_style
from ..model.blocks import (CAPTION, HEADING, IMAGE, PAGE_BREAK, PARAGRAPH, TABLE, Block, TextRun)
from ..model.document import DocumentData, MM_PER_INCH
from ..model.lists import ListInfo, list_infos
from ..model.ops import caption_info

ALIGN_FLAGS = {
    "left": Qt.AlignmentFlag.AlignLeft,
    "center": Qt.AlignmentFlag.AlignHCenter,
    "right": Qt.AlignmentFlag.AlignRight,
    "justify": Qt.AlignmentFlag.AlignJustify,
}
INDENT_MM = 12.5
PROPORTIONAL = QTextBlockFormat.LineHeightTypes.ProportionalHeight.value
SOLID = QTextFrameFormat.BorderStyle.BorderStyle_Solid
NO_BORDER = QTextFrameFormat.BorderStyle.BorderStyle_None

LIST_STYLES = {
    "disc": (QTextListFormat.Style.ListDisc, ""),
    "circle": (QTextListFormat.Style.ListCircle, ""),
    "square": (QTextListFormat.Style.ListSquare, ""),
    "decimal": (QTextListFormat.Style.ListDecimal, "."),
    "decimalParen": (QTextListFormat.Style.ListDecimal, ")"),
    "lowerAlpha": (QTextListFormat.Style.ListLowerAlpha, ")"),
    "upperAlpha": (QTextListFormat.Style.ListUpperAlpha, "."),
    "lowerRoman": (QTextListFormat.Style.ListLowerRoman, "."),
    "upperRoman": (QTextListFormat.Style.ListUpperRoman, "."),
    "multilevel": (QTextListFormat.Style.ListDecimal, "."),
}
TAB_TYPES = {
    "left": QTextOption.TabType.LeftTab,
    "center": QTextOption.TabType.CenterTab,
    "right": QTextOption.TabType.RightTab,
    "decimal": QTextOption.TabType.DelimiterTab,
}
VERTICAL = {
    "super": QTextCharFormat.VerticalAlignment.AlignSuperScript,
    "sub": QTextCharFormat.VerticalAlignment.AlignSubScript,
}


def resolve_image_path(path: str, base_dir: str) -> str:
    if not path:
        return ""
    if os.path.isabs(path) or not base_dir:
        return path
    return os.path.normpath(os.path.join(base_dir, path))


def char_format_for_style(style: dict) -> QTextCharFormat:
    cf = QTextCharFormat()
    cf.setFontFamilies([style["family"]])
    cf.setFontPointSize(style["pointSize"])
    cf.setFontWeight(QFont.Weight.Bold if style["bold"] else QFont.Weight.Normal)
    cf.setFontItalic(bool(style["italic"]))
    cf.setForeground(QBrush(QColor(style["color"])))
    return cf


def apply_run(base: QTextCharFormat, run: TextRun) -> QTextCharFormat:
    cf = QTextCharFormat(base)
    if run.bold is not None:
        cf.setFontWeight(QFont.Weight.Bold if run.bold else QFont.Weight.Normal)
    if run.italic is not None:
        cf.setFontItalic(run.italic)
    if run.underline is not None:
        cf.setFontUnderline(run.underline)
    if run.strike is not None:
        cf.setFontStrikeOut(run.strike)
    if run.color:
        cf.setForeground(QBrush(QColor(run.color)))
    if run.highlight:
        cf.setBackground(QBrush(QColor(run.highlight)))
    if run.font_family:
        cf.setFontFamilies([run.font_family])
    if run.font_size > 0:
        cf.setFontPointSize(run.font_size)
    if run.vertical in VERTICAL:
        cf.setVerticalAlignment(VERTICAL[run.vertical])
    if run.small_caps:
        cf.setFontCapitalization(QFont.Capitalization.SmallCaps)
    if run.link:
        cf.setAnchor(True)
        cf.setAnchorHref(run.link)
        cf.setFontUnderline(True)
        if not run.color:
            cf.setForeground(QBrush(QColor(styles.LINK_COLOR)))
    return cf


def transformed_image(image: QImage, img) -> QImage:
    """Kadrowanie i obrót obrazu (tak samo jak w edytorze)."""
    if img.cropped:
        w, h = image.width(), image.height()
        rect = QRectF(w * img.crop_left, h * img.crop_top,
                      w * (1 - img.crop_left - img.crop_right), h * (1 - img.crop_top - img.crop_bottom))
        image = image.copy(rect.toRect())
    if img.rotation:
        image = image.transformed(QTransform().rotate(img.rotation), Qt.TransformationMode.SmoothTransformation)
    return image


class _Writer:
    def __init__(self, state: DocumentData, base_dir: str, dpi: float, doc: QTextDocument,
                 content_width: float, content_height: float):
        self.state = state
        self.base_dir = base_dir
        self.dpi = dpi
        self.doc = doc
        self.cursor = QTextCursor(doc)
        self.reuse_current = True          # pierwszy (pusty) akapit dokumentu
        self.pending_page_break = False
        self.lists: dict[int, tuple] = {}  # poziom -> (klucz, QTextList, ostatni numer)
        self.styles = styles.all_text_styles(state.meta)
        self.content_width = content_width
        self.content_height = content_height
        self.captions = caption_info(state.blocks)
        self.list_info = list_infos(state.blocks)
        self.leaders: list[tuple[int, list[tuple[float, str]]]] = []  # (numer bloku, [(pozycja px, wypełnienie)])
        self.consumed: set[str] = set()

    def mm(self, value: float) -> float:
        return value / MM_PER_INCH * self.dpi

    def pt(self, value: float) -> float:
        return value / 72.0 * self.dpi

    # --- akapity ---

    def new_block(self, bf: QTextBlockFormat, cf: QTextCharFormat) -> None:
        if self.pending_page_break:
            bf.setPageBreakPolicy(QTextFormat.PageBreakFlag.PageBreak_AlwaysBefore)
            self.pending_page_break = False
        if self.reuse_current:
            self.cursor.setBlockFormat(bf)
            self.cursor.setBlockCharFormat(cf)
            self.reuse_current = False
        else:
            self.cursor.insertBlock(bf, cf)

    def block_format(self, block: Block) -> QTextBlockFormat:
        para = block.para
        bf = QTextBlockFormat()
        bf.setAlignment(ALIGN_FLAGS.get(para.align, Qt.AlignmentFlag.AlignLeft))
        bf.setTopMargin(self.pt(para.space_before))
        bf.setBottomMargin(self.pt(para.space_after))
        bf.setLineHeight(para.line_height * 100.0, PROPORTIONAL)
        left = self.mm(para.left_mm)
        if para.list == "none":
            left += self.mm(INDENT_MM) * para.indent
        first = self.mm(para.first_line_mm)
        if first < 0:  # wysunięcie: pozostałe wiersze przesunięte w prawo
            left += -first
        bf.setLeftMargin(max(0.0, left))
        bf.setRightMargin(max(0.0, self.mm(para.right_mm)))
        bf.setTextIndent(first)
        if para.tabs:
            bf.setTabPositions([QTextOption.Tab(self.mm(t.position), TAB_TYPES.get(t.align, QTextOption.TabType.LeftTab),
                                                ",") for t in para.tabs])
        return bf

    def insert_runs(self, runs, base: QTextCharFormat, cursor: QTextCursor | None = None) -> None:
        cursor = cursor or self.cursor
        for run in runs:
            # \n w przebiegu to miękki podział wiersza (Shift+Enter).
            cursor.insertText(run.text.replace("\n", " "), apply_run(base, run))

    def text_block(self, block: Block, info: ListInfo) -> None:
        style = self.styles[block.style_key]
        bf = self.block_format(block)
        if block.type == HEADING:
            bf.setHeadingLevel(block.level)
        cf = char_format_for_style(style)
        self.new_block(bf, cf)
        self.handle_list(block, info)
        if block.para.tabs and any(t.leader != "none" for t in block.para.tabs):
            self.leaders.append((self.cursor.block().blockNumber(),
                                 [(self.mm(t.position), t.leader) for t in block.para.tabs]))
        self.insert_runs(block.runs, cf)
        if block.type == HEADING and block.description:
            dbf = QTextBlockFormat()
            dbf.setAlignment(bf.alignment())
            dbf.setBottomMargin(self.pt(6))
            dcf = char_format_for_style(self.styles["body"])
            dcf.setFontItalic(True)
            dcf.setFontPointSize(self.state.meta.font_size * 0.92)
            dcf.setForeground(QBrush(QColor(styles.DESCRIPTION_COLOR)))
            self.new_block(dbf, dcf)
            self.cursor.insertText(block.description.replace("\n", " "), dcf)

    def handle_list(self, block: Block, info: ListInfo) -> None:
        if not info.kind:
            self.lists.clear()
            return
        level = block.para.indent
        for deeper in [k for k in self.lists if k > level]:
            del self.lists[deeper]
        key = (info.kind, info.style, info.prefix)
        current = self.lists.get(level)
        if current and current[0] == key and (info.kind == "bullet" or current[2] + 1 == info.number):
            current[1].add(self.cursor.block())
            self.lists[level] = (key, current[1], info.number)
            return
        style, suffix = LIST_STYLES.get(info.style, (QTextListFormat.Style.ListDisc, ""))
        fmt = QTextListFormat()
        fmt.setStyle(style)
        fmt.setIndent(level + 1)
        if info.kind == "number":
            fmt.setNumberSuffix(suffix)
            fmt.setNumberPrefix(info.prefix)
            fmt.setStart(info.number)
        self.lists[level] = (key, self.cursor.createList(fmt), info.number)

    # --- obramowanie i cieniowanie grup akapitów ---

    def bordered_group(self, group: list[tuple[Block, ListInfo]]) -> None:
        para = group[0][0].para
        self.lists.clear()
        tf = QTextTableFormat()
        tf.setBorder(0)
        tf.setBorderCollapse(True)
        tf.setCellSpacing(0)
        tf.setCellPadding(self.pt(4))
        tf.setWidth(QTextLength(QTextLength.Type.PercentageLength, 100))
        tf.setTopMargin(self.pt(2))
        tf.setBottomMargin(self.pt(2))
        if self.pending_page_break:
            tf.setPageBreakPolicy(QTextFormat.PageBreakFlag.PageBreak_AlwaysBefore)
            self.pending_page_break = False
        if not self.reuse_current:
            self.cursor.insertBlock()
        table = self.cursor.insertTable(1, 1, tf)
        cell = table.cellAt(0, 0)
        cfmt = cell.format().toTableCellFormat()
        width = max(0.5, self.pt(para.border_width))
        brush = QBrush(QColor(para.border_color))
        sides = {"box": ("top", "bottom", "left", "right"), "top": ("top",), "bottom": ("bottom",),
                 "topBottom": ("top", "bottom"), "left": ("left",)}.get(para.border, ())
        for side in ("top", "bottom", "left", "right"):
            on = side in sides
            w = (width * (2.5 if para.border == "left" else 1)) if on else 0
            name = side.capitalize()
            getattr(cfmt, f"set{name}Border")(w)
            getattr(cfmt, f"set{name}BorderStyle")(SOLID if on else NO_BORDER)
            getattr(cfmt, f"set{name}BorderBrush")(brush)
        if para.shading:
            cfmt.setBackground(QBrush(QColor(para.shading)))
        outer = self.cursor
        self.cursor = cell.firstCursorPosition()
        self.reuse_current = True
        for block, info in group:
            self.text_block(block, info)
        self.lists.clear()
        # Format komórki Qt trzyma w formacie znaków jej pierwszego bloku – ustawiamy go po treści.
        table.cellAt(0, 0).setFormat(cfmt)
        self.cursor = outer
        self.cursor.movePosition(QTextCursor.MoveOperation.End)
        self.reuse_current = True

    # --- tabele ---

    def table_block(self, block: Block) -> None:
        self.lists.clear()
        t = block.table
        fmt = QTextTableFormat()
        fmt.setCellPadding(self.pt(4))
        fmt.setCellSpacing(0)
        fmt.setBorder(0)
        fmt.setBorderCollapse(True)
        fmt.setTopMargin(self.pt(6))
        fmt.setBottomMargin(self.pt(4))
        fmt.setWidth(QTextLength(QTextLength.Type.PercentageLength, 100))
        fmt.setColumnWidthConstraints(
            [QTextLength(QTextLength.Type.PercentageLength, w * 100) for w in t.col_widths])
        if t.header_row and t.repeat_header:
            fmt.setHeaderRowCount(1)
        if self.pending_page_break:
            fmt.setPageBreakPolicy(QTextFormat.PageBreakFlag.PageBreak_AlwaysBefore)
            self.pending_page_break = False
        if not self.reuse_current:
            self.cursor.insertBlock()
        table = self.cursor.insertTable(t.rows, t.cols, fmt)
        cov = t.coverage()
        look = table_style.appearance(t)
        body = self.styles["body"]
        for r in range(t.rows):
            for c in range(t.cols):
                cell = t.cells[r][c]
                if cov[r][c] == (r, c) and (cell.row_span > 1 or cell.col_span > 1):
                    table.mergeCells(r, c, cell.row_span, cell.col_span)
        for r in range(t.rows):
            for c in range(t.cols):
                if cov[r][c] != (r, c):
                    continue
                cell = t.cells[r][c]
                a = look[r][c]
                qcell = table.cellAt(r, c)
                cell_fmt = qcell.format().toTableCellFormat()
                if a["background"]:
                    cell_fmt.setBackground(QBrush(QColor(a["background"])))
                for side in ("top", "bottom", "left", "right"):
                    edge = a[side]
                    name = side.capitalize()
                    getattr(cell_fmt, f"set{name}Border")(self.pt(edge["w"]) if edge["w"] else 0)
                    getattr(cell_fmt, f"set{name}BorderStyle")(SOLID if edge["w"] else NO_BORDER)
                    getattr(cell_fmt, f"set{name}BorderBrush")(QBrush(QColor(edge["c"])))
                qcell.setFormat(cell_fmt)
                cc = qcell.firstCursorPosition()
                cbf = QTextBlockFormat()
                cbf.setAlignment(ALIGN_FLAGS.get(cell.align, Qt.AlignmentFlag.AlignLeft))
                cc.setBlockFormat(cbf)
                base = char_format_for_style(body)
                if a["bold"]:
                    base.setFontWeight(QFont.Weight.Bold)
                if a["color"]:
                    base.setForeground(QBrush(QColor(a["color"])))
                self.insert_runs(cell.runs, base, cc)
        self.cursor.movePosition(QTextCursor.MoveOperation.End)
        self.reuse_current = True

    # --- obrazy ---

    def _load_image(self, block: Block) -> QImage:
        path = resolve_image_path(block.image.path, self.base_dir)
        image = QImage(path) if path else QImage()
        return transformed_image(image, block.image) if not image.isNull() else image

    def _image_format(self, block: Block, image: QImage) -> QTextImageFormat:
        name = f"qmlword-image://{block.id}"
        width = self.content_width * block.image.width
        height = width * image.height() / max(1, image.width())
        if height > self.content_height * 0.95:
            scale = self.content_height * 0.95 / height
            width, height = width * scale, height * scale
        if block.image.border_width > 0:
            # Ramkę rysujemy na kopii obrazu – grubość przeliczona na piksele obrazu.
            image = image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
            painter = QPainter(image)
            pen_px = max(1.0, self.pt(block.image.border_width) * image.width() / max(1.0, width))
            pen = QPen(QColor(block.image.border_color))
            pen.setWidthF(pen_px)
            pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
            painter.setPen(pen)
            painter.drawRect(QRectF(pen_px / 2, pen_px / 2, image.width() - pen_px, image.height() - pen_px))
            painter.end()
        self.doc.addResource(QTextDocument.ResourceType.ImageResource.value, QUrl(name), image)
        fmt = QTextImageFormat()
        fmt.setName(name)
        fmt.setWidth(width)
        fmt.setHeight(height)
        return fmt

    def _missing(self, block: Block, cf: QTextCharFormat) -> None:
        missing = QTextCharFormat(cf)
        missing.setFontItalic(True)
        missing.setForeground(QBrush(QColor("#a33")))
        self.cursor.insertText(f"[Nie można wczytać obrazu: {block.image.path or 'brak ścieżki'}]", missing)

    def image_block(self, block: Block, caption: Block | None) -> None:
        self.lists.clear()
        image = self._load_image(block)
        cf = char_format_for_style(self.styles["body"])
        if block.image.wrap in ("left", "right") and not image.isNull():
            self.floating_image(block, image, caption)
            return
        bf = QTextBlockFormat()
        bf.setAlignment(ALIGN_FLAGS.get(block.image.align, Qt.AlignmentFlag.AlignHCenter))
        bf.setTopMargin(self.pt(6))
        bf.setBottomMargin(self.pt(4))
        self.new_block(bf, cf)
        if image.isNull():
            self._missing(block, cf)
            return
        self.cursor.insertImage(self._image_format(block, image))

    def floating_image(self, block: Block, image: QImage, caption: Block | None) -> None:
        fmt = self._image_format(block, image)
        ff = QTextFrameFormat()
        ff.setPosition(QTextFrameFormat.Position.FloatLeft if block.image.wrap == "left"
                       else QTextFrameFormat.Position.FloatRight)
        ff.setWidth(QTextLength(QTextLength.Type.FixedLength, fmt.width() + 2))
        ff.setBorder(0)
        ff.setPadding(0)
        gap = self.pt(10)
        ff.setTopMargin(self.pt(4))
        ff.setBottomMargin(self.pt(6))
        ff.setLeftMargin(gap if block.image.wrap == "right" else 0)
        ff.setRightMargin(gap if block.image.wrap == "left" else 0)
        if self.pending_page_break:
            ff.setPageBreakPolicy(QTextFormat.PageBreakFlag.PageBreak_AlwaysBefore)
            self.pending_page_break = False
        if not self.reuse_current:
            self.cursor.insertBlock()
        frame = self.cursor.insertFrame(ff)
        inner = frame.firstCursorPosition()
        inner.insertImage(fmt)
        if caption is not None:
            self.consumed.add(caption.id)
            bf = QTextBlockFormat()
            bf.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            bf.setTopMargin(self.pt(2))
            inner.insertBlock(bf)
            self._caption_text(inner, caption)
        self.cursor.movePosition(QTextCursor.MoveOperation.End)
        # Pusty akapit za ramką zostaje użyty przez następny blok – tekst opływa obraz.
        self.reuse_current = True

    # --- podpisy ---

    def _caption_text(self, cursor: QTextCursor, block: Block) -> None:
        label, number = self.captions.get(block.id, ("Podpis", 0))
        cf = char_format_for_style(self.styles["body"])
        cf.setFontPointSize(self.state.meta.font_size * 0.9)
        cf.setForeground(QBrush(QColor(styles.CAPTION_COLOR)))
        label_fmt = QTextCharFormat(cf)
        label_fmt.setFontWeight(QFont.Weight.Bold)
        cursor.insertText(f"{label} {number}. " if number else f"{label}. ", label_fmt)
        text_fmt = QTextCharFormat(cf)
        text_fmt.setFontItalic(True)
        cursor.insertText(block.caption.text.replace("\n", " "), text_fmt)

    def caption_block(self, block: Block) -> None:
        self.lists.clear()
        bf = QTextBlockFormat()
        bf.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        bf.setBottomMargin(self.pt(10))
        self.new_block(bf, char_format_for_style(self.styles["body"]))
        self._caption_text(self.cursor, block)

    # --- całość ---

    def build(self) -> None:
        blocks = self.state.blocks
        i = 0
        while i < len(blocks):
            block = blocks[i]
            info = self.list_info[i]
            if block.id in self.consumed:
                i += 1
                continue
            if block.type in (PARAGRAPH, HEADING):
                para = block.para
                if para.border != "none" or para.shading:
                    group = [(block, info)]
                    key = (para.border, para.border_color, para.border_width, para.shading)
                    j = i + 1
                    while j < len(blocks) and blocks[j].type in (PARAGRAPH, HEADING):
                        p = blocks[j].para
                        if (p.border, p.border_color, p.border_width, p.shading) != key:
                            break
                        group.append((blocks[j], self.list_info[j]))
                        j += 1
                    self.bordered_group(group)
                    i = j
                    continue
                self.text_block(block, info)
            elif block.type == TABLE:
                self.table_block(block)
            elif block.type == IMAGE:
                nxt = blocks[i + 1] if i + 1 < len(blocks) else None
                caption = nxt if nxt is not None and nxt.type == CAPTION and nxt.caption.target_id == block.id else None
                self.image_block(block, caption)
            elif block.type == CAPTION:
                self.caption_block(block)
            elif block.type == PAGE_BREAK:
                self.pending_page_break = True
                self.lists.clear()
            # placeholder i nieznane bloki nie trafiają do wydruku
            i += 1


class PagedDocument:
    """Zbudowany i spaginowany dokument gotowy do malowania stron."""

    def __init__(self, state: DocumentData, base_dir: str, dpi: float, paint_device=None):
        self.dpi = dpi
        self.paint_device = paint_device  # trzymamy referencję tak długo jak dokument
        self.doc = QTextDocument()
        self.doc.setUndoRedoEnabled(False)
        if paint_device is not None:
            self.doc.documentLayout().setPaintDevice(paint_device)
        page = state.page
        w_mm, h_mm = page.size_mm()
        self.page_width = w_mm / MM_PER_INCH * dpi
        self.page_height = h_mm / MM_PER_INCH * dpi
        self.footer_height = page.margin_bottom / MM_PER_INCH * dpi
        font = QFont(state.meta.font_family)
        font.setPointSizeF(state.meta.font_size)
        self.doc.setDefaultFont(font)
        self.doc.setDocumentMargin(0)
        self.doc.setIndentWidth(INDENT_MM / MM_PER_INCH * dpi)
        self.doc.setPageSize(QSizeF(self.page_width, self.page_height))
        root = self.doc.rootFrame()
        ff = root.frameFormat()
        ff.setTopMargin(page.margin_top / MM_PER_INCH * dpi)
        ff.setBottomMargin(page.margin_bottom / MM_PER_INCH * dpi)
        ff.setLeftMargin(page.margin_left / MM_PER_INCH * dpi)
        ff.setRightMargin(page.margin_right / MM_PER_INCH * dpi)
        root.setFrameFormat(ff)
        content_w = page.content_width_mm() / MM_PER_INCH * dpi
        content_h = (h_mm - page.margin_top - page.margin_bottom) / MM_PER_INCH * dpi
        self.writer = _Writer(state, base_dir, dpi, self.doc, content_w, content_h)
        self.writer.build()

    def page_count(self) -> int:
        return max(1, self.doc.pageCount())

    def _paint_leaders(self, painter: QPainter, clip: QRectF) -> None:
        layout = self.doc.documentLayout()
        for number, stops in self.writer.leaders:
            block = self.doc.findBlockByNumber(number)
            if not block.isValid():
                continue
            rect = layout.blockBoundingRect(block)
            if not rect.intersects(clip):
                continue
            text_layout = block.layout()
            origin = text_layout.position()  # pozycja układu bloku jest już bezwzględna
            for k, ch in enumerate(block.text()):
                if ch != "\t":
                    continue
                line = text_layout.lineForTextPosition(k)
                if not line.isValid():
                    continue
                x1 = line.cursorToX(k)[0]
                x2 = line.cursorToX(k + 1)[0]
                leader = next((lead for pos, lead in stops if pos >= x2 - 1.0), "none")
                if leader == "none" or x2 - x1 < 6:
                    continue
                y = origin.y() + line.y() + line.ascent()
                pen = QPen(QColor(styles.TEXT_COLOR))
                pen.setWidthF(max(0.6, self.dpi / 110))
                if leader == "dot":
                    pen.setStyle(Qt.PenStyle.DotLine)
                    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                elif leader == "dash":
                    pen.setStyle(Qt.PenStyle.DashLine)
                painter.setPen(pen)
                gap = self.dpi / 40
                painter.drawLine(QPointF(origin.x() + x1 + gap, y), QPointF(origin.x() + x2 - gap, y))

    def paint_page(self, painter: QPainter, index: int, page_numbers: bool = True) -> None:
        painter.save()
        clip = QRectF(0, index * self.page_height, self.page_width, self.page_height)
        painter.translate(0, -index * self.page_height)
        painter.setClipRect(clip)
        ctx = QAbstractTextDocumentLayout.PaintContext()
        ctx.clip = clip
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Text, QColor(styles.TEXT_COLOR))
        ctx.palette = palette
        self.doc.documentLayout().draw(painter, ctx)
        self._paint_leaders(painter, clip)
        painter.restore()
        if page_numbers:
            painter.save()
            font = QFont(self.doc.defaultFont())
            font.setPointSizeF(9)
            painter.setFont(font)
            painter.setPen(QColor("#6b7580"))
            rect = QRectF(0, self.page_height - self.footer_height, self.page_width, self.footer_height)
            painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter),
                             f"{index + 1} / {self.page_count()}")
            painter.restore()


def fragment_html(state: DocumentData, base_dir: str) -> str:
    """HTML fragmentu dokumentu (do schowka – wklejanie do innych programów)."""
    doc = QTextDocument()
    font = QFont(state.meta.font_family)
    font.setPointSizeF(state.meta.font_size)
    doc.setDefaultFont(font)
    _Writer(state, base_dir, 96.0, doc, 600.0, 900.0).build()
    return doc.toHtml()
