"""Most między edytorem ``TextEdit`` (QML) a przebiegami tekstu modelu.

Edytor nie trzyma HTML-a: treść wczytujemy kursorem z formatami znaków,
a przy zatwierdzaniu odczytujemy fragmenty ``QTextDocument`` z powrotem
do listy przebiegów. Zapisywane są tylko właściwości ustawione jawnie –
reszta dziedziczy się ze stylu akapitu (czcionka ``TextEdit``).
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Slot
from PySide6.QtGui import (QBrush, QColor, QFont, QTextBlockFormat, QTextCharFormat, QTextCursor,
                           QTextDocument, QTextOption)
from PySide6.QtQml import QmlElement, QmlSingleton
from PySide6.QtQuick import QQuickTextDocument

from ..io.qt_text import (LINE_SEPARATOR, VERTICAL_TO_QT, P, append_run, char_format_for_run,
                          extract_paragraphs)
from ..model.styles import LINK_COLOR

QML_IMPORT_NAME = "QmlWord.Backend"
QML_IMPORT_MAJOR_VERSION = 1

ALIGN = {
    "left": Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignAbsolute,
    "center": Qt.AlignmentFlag.AlignHCenter,
    "right": Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignAbsolute,
    "justify": Qt.AlignmentFlag.AlignJustify,
}
PROPORTIONAL = QTextBlockFormat.LineHeightTypes.ProportionalHeight.value
PX_PER_MM = 96 / 25.4
TAB_TYPES = {
    "left": QTextOption.TabType.LeftTab,
    "center": QTextOption.TabType.CenterTab,
    "right": QTextOption.TabType.RightTab,
    "decimal": QTextOption.TabType.DelimiterTab,
}

# Re-eksport dla testów i kodu, który importował z tego modułu.
__all__ = ["RichText", "RichTextBridge", "extract_paragraphs"]


def _doc(qdoc) -> QTextDocument | None:
    if isinstance(qdoc, QQuickTextDocument):
        return qdoc.textDocument()
    if isinstance(qdoc, QTextDocument):
        return qdoc
    return None


def block_format_for(para: dict) -> QTextBlockFormat:
    """Format akapitu w edytorze: wyrównanie, interlinia, pierwszy wiersz/wysunięcie, tabulatory.

    Wcięcia lewe/prawe w mm i poziomy listy realizuje QML (pozycja edytora), tu tylko to,
    co dotyczy wierszy wewnątrz akapitu.
    """
    bf = QTextBlockFormat()
    bf.setAlignment(ALIGN.get(para.get("align", "left"), ALIGN["left"]))
    bf.setLineHeight(float(para.get("lineHeight", 1.15)) * 100.0, PROPORTIONAL)
    first = float(para.get("firstLineMm", 0) or 0) * PX_PER_MM
    if first < 0:
        bf.setLeftMargin(-first)
    bf.setTextIndent(first)
    tabs = para.get("tabs") or []
    if tabs:
        bf.setTabPositions([QTextOption.Tab(float(t.get("position", 0)) * PX_PER_MM,
                                            TAB_TYPES.get(t.get("align"), QTextOption.TabType.LeftTab), ",")
                            for t in tabs])
    return bf


class RichTextBridge:
    """Logika niezależna od QML – testowalna na zwykłym ``QTextDocument``."""

    @staticmethod
    def load(doc: QTextDocument, runs: list, para: dict | None = None) -> None:
        doc.setUndoRedoEnabled(False)
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.removeSelectedText()
        cursor.setBlockCharFormat(QTextCharFormat())
        cursor.setCharFormat(QTextCharFormat())
        cursor.setBlockFormat(block_format_for(para or {}))
        for run in runs or []:
            text = str(run.get("text", "")).replace("\n", LINE_SEPARATOR)
            if text:
                cursor.insertText(text, char_format_for_run(run))
        if not runs:
            cursor.setBlockCharFormat(QTextCharFormat())
        cursor.endEditBlock()
        doc.setModified(False)

    @staticmethod
    def merge_format(doc: QTextDocument, start: int, end: int, props: dict) -> tuple[int, int]:
        """Ustawia (lub czyści – wartość None/"") właściwości znaków w zakresie.

        Pusty zakres oznacza słowo pod kursorem, a w pustym akapicie – format
        akapitu, który przejmie wpisywany tekst. Zwraca faktycznie użyty zakres.
        """
        if start > end:
            start, end = end, start
        if start == end:
            cursor = QTextCursor(doc)
            cursor.setPosition(start)
            if doc.characterCount() <= 1:
                fmt = cursor.blockCharFormat()
                RichTextBridge._apply_props(fmt, props)
                cursor.setBlockCharFormat(fmt)
                return start, end
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
            if not cursor.hasSelection() or not cursor.selectedText().strip():
                return start, end
            start, end = cursor.selectionStart(), cursor.selectionEnd()
        # Najpierw zbieramy fragmenty, potem je zmieniamy (zmiana formatu dzieli fragmenty).
        pieces: list[tuple[int, int, QTextCharFormat]] = []
        block = doc.findBlock(start)
        while block.isValid() and block.position() < end:
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                f_start, f_end = frag.position(), frag.position() + frag.length()
                s, e = max(f_start, start), min(f_end, end)
                if s < e:
                    pieces.append((s, e, QTextCharFormat(frag.charFormat())))
                it += 1
            block = block.next()
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()
        for s, e, fmt in pieces:
            RichTextBridge._apply_props(fmt, props)
            cursor.setPosition(s)
            cursor.setPosition(e, QTextCursor.MoveMode.KeepAnchor)
            cursor.setCharFormat(fmt)
        cursor.endEditBlock()
        return start, end

    @staticmethod
    def _apply_props(fmt: QTextCharFormat, props: dict) -> None:
        for key, value in props.items():
            clear = value is None or value == "" or (key == "fontSize" and not value)
            if key == "bold":
                if clear:
                    fmt.clearProperty(P.FontWeight)
                else:
                    fmt.setFontWeight(QFont.Weight.Bold if value else QFont.Weight.Normal)
            elif key == "italic":
                fmt.clearProperty(P.FontItalic) if clear else fmt.setFontItalic(bool(value))
            elif key == "underline":
                if clear:
                    fmt.clearProperty(P.TextUnderlineStyle)
                    fmt.clearProperty(P.FontUnderline)
                else:
                    fmt.setFontUnderline(bool(value))
            elif key == "strike":
                fmt.clearProperty(P.FontStrikeOut) if clear else fmt.setFontStrikeOut(bool(value))
            elif key == "color":
                fmt.clearProperty(P.ForegroundBrush) if clear else fmt.setForeground(QBrush(QColor(value)))
            elif key == "highlight":
                fmt.clearProperty(P.BackgroundBrush) if clear else fmt.setBackground(QBrush(QColor(value)))
            elif key == "fontFamily":
                fmt.clearProperty(P.FontFamilies) if clear else fmt.setFontFamilies([str(value)])
            elif key == "fontSize":
                fmt.clearProperty(P.FontPointSize) if clear else fmt.setFontPointSize(float(value))
            elif key == "vertical":
                if value in VERTICAL_TO_QT:
                    fmt.setVerticalAlignment(VERTICAL_TO_QT[value])
                else:
                    fmt.clearProperty(P.TextVerticalAlignment)
            elif key == "smallCaps":
                if clear:
                    fmt.clearProperty(P.FontCapitalization)
                else:
                    fmt.setFontCapitalization(QFont.Capitalization.SmallCaps if value
                                              else QFont.Capitalization.MixedCase)
            elif key == "link":
                if clear:
                    fmt.setAnchor(False)
                    fmt.clearProperty(P.AnchorHref)
                    fmt.clearProperty(P.IsAnchor)
                    fmt.clearProperty(P.ForegroundBrush)
                    fmt.clearProperty(P.TextUnderlineStyle)
                    fmt.clearProperty(P.FontUnderline)
                else:
                    fmt.setAnchor(True)
                    fmt.setAnchorHref(str(value))
                    fmt.setForeground(QBrush(QColor(LINK_COLOR)))
                    fmt.setFontUnderline(True)

    @staticmethod
    def format_at(doc: QTextDocument, start: int, end: int) -> dict:
        """Efektywny format (z uwzględnieniem domyślnej czcionki edytora)."""
        if start > end:
            start, end = end, start
        cursor = QTextCursor(doc)
        if start == end:
            cursor.setPosition(start)
        else:
            cursor.setPosition(start + 1)
        fmt = cursor.charFormat()
        font = fmt.font().resolve(doc.defaultFont())
        is_link = fmt.isAnchor() and bool(fmt.anchorHref())
        va = fmt.verticalAlignment() if fmt.hasProperty(P.TextVerticalAlignment) else None
        return {
            "bold": font.bold(),
            "italic": font.italic(),
            "underline": font.underline() and not is_link,
            "strike": font.strikeOut(),
            "color": fmt.foreground().color().name() if fmt.hasProperty(P.ForegroundBrush) and not is_link else "",
            "highlight": fmt.background().color().name()
            if fmt.hasProperty(P.BackgroundBrush) and fmt.background().style() != Qt.BrushStyle.NoBrush else "",
            "fontFamily": str(fmt.fontFamilies()[0]) if fmt.hasProperty(P.FontFamilies) and fmt.fontFamilies() else "",
            "fontSize": round(fmt.fontPointSize() * 2) / 2 if fmt.hasProperty(P.FontPointSize) else 0,
            "link": fmt.anchorHref() if is_link else "",
            "vertical": "super" if va == QTextCharFormat.VerticalAlignment.AlignSuperScript
            else "sub" if va == QTextCharFormat.VerticalAlignment.AlignSubScript else "",
            "smallCaps": font.capitalization() == QFont.Capitalization.SmallCaps,
        }

    @staticmethod
    def link_range(doc: QTextDocument, pos: int) -> tuple[int, int, str]:
        """Zakres linku obejmującego pozycję (start, end, adres) albo (-1, -1, "")."""
        block = doc.findBlock(pos)
        it = block.begin()
        while not it.atEnd():
            frag = it.fragment()
            if frag.position() <= pos <= frag.position() + frag.length():
                fmt = frag.charFormat()
                if fmt.isAnchor() and fmt.anchorHref():
                    return frag.position(), frag.position() + frag.length(), fmt.anchorHref()
            it += 1
        return -1, -1, ""


def _joined(paragraphs: list[list[dict]]) -> list[dict]:
    out: list[dict] = []
    for i, para in enumerate(paragraphs):
        if i:
            append_run(out, {"text": "\n"})
        for run in para:
            append_run(out, dict(run))
    return out


@QmlElement
@QmlSingleton
class RichText(QObject):
    """Funkcje dla edytorów tekstu w QML (``RichText.load(textEdit.textDocument, ...)``)."""

    @Slot(QQuickTextDocument, "QVariantList", "QVariantMap")
    def load(self, qdoc, runs, para) -> None:
        doc = _doc(qdoc)
        if doc is not None:
            RichTextBridge.load(doc, list(runs or []), dict(para or {}))

    @Slot(QQuickTextDocument, "QVariantMap")
    def setParagraphFormat(self, qdoc, para) -> None:
        """Zmiana formatu akapitu bez przeładowania treści (kursor zostaje na miejscu)."""
        doc = _doc(qdoc)
        if doc is None:
            return
        cursor = QTextCursor(doc)
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setBlockFormat(block_format_for(dict(para or {})))

    @Slot(QQuickTextDocument, result="QVariantList")
    def runs(self, qdoc) -> list:
        """Cała treść jako jedna lista przebiegów (akapity łączone znakiem nowej linii)."""
        doc = _doc(qdoc)
        return _joined(extract_paragraphs(doc)) if doc is not None else []

    @Slot(QQuickTextDocument, result="QVariantList")
    def paragraphs(self, qdoc) -> list:
        doc = _doc(qdoc)
        return extract_paragraphs(doc) if doc is not None else [[]]

    @Slot(QQuickTextDocument, int, int, result="QVariantList")
    def runsInRange(self, qdoc, start: int, end: int) -> list:
        doc = _doc(qdoc)
        return _joined(extract_paragraphs(doc, start, end)) if doc is not None else []

    @Slot(QQuickTextDocument, result=int)
    def blockCount(self, qdoc) -> int:
        doc = _doc(qdoc)
        return doc.blockCount() if doc is not None else 0

    @Slot(QQuickTextDocument, int, int, "QVariantMap", result="QVariantList")
    def mergeFormat(self, qdoc, start: int, end: int, props) -> list:
        doc = _doc(qdoc)
        if doc is None:
            return [start, end]
        s, e = RichTextBridge.merge_format(doc, start, end, dict(props))
        return [s, e]

    @Slot(QQuickTextDocument, int, int, result="QVariantMap")
    def formatAt(self, qdoc, start: int, end: int) -> dict:
        doc = _doc(qdoc)
        if doc is None:
            return {}
        return RichTextBridge.format_at(doc, start, end)

    @Slot(QQuickTextDocument, int, str, str, result=int)
    def insertLink(self, qdoc, pos: int, text: str, url: str) -> int:
        doc = _doc(qdoc)
        if doc is None or not text:
            return pos
        cursor = QTextCursor(doc)
        cursor.setPosition(pos)
        cursor.insertText(text, char_format_for_run({"text": text, "link": url}))
        # Kolejny wpisany znak nie powinien przejąć linku.
        cursor.insertText("​", QTextCharFormat())
        cursor.deletePreviousChar()
        return pos + len(text)

    @Slot(QQuickTextDocument, int, result="QVariantMap")
    def linkAt(self, qdoc, pos: int) -> dict:
        doc = _doc(qdoc)
        if doc is None:
            return {"start": -1, "end": -1, "url": ""}
        s, e, url = RichTextBridge.link_range(doc, pos)
        return {"start": s, "end": e, "url": url}

    @Slot(QQuickTextDocument, int, str)
    def insertPlainText(self, qdoc, pos: int, text: str) -> None:
        """Wstawia tekst w formacie znaku przed kursorem (symbole, twarda spacja…)."""
        doc = _doc(qdoc)
        if doc is None:
            return
        cursor = QTextCursor(doc)
        cursor.setPosition(pos)
        cursor.insertText(text.replace("\r\n", "\n").replace("\n", LINE_SEPARATOR))

    @Slot(QQuickTextDocument, bool)
    def setShowMarks(self, qdoc, show: bool) -> None:
        """Znaki niedrukowalne: kropki w miejscu spacji i strzałki tabulatorów."""
        doc = _doc(qdoc)
        if doc is None:
            return
        option = doc.defaultTextOption()
        flags = option.flags()
        if show:
            flags |= QTextOption.Flag.ShowTabsAndSpaces
        else:
            flags &= ~QTextOption.Flag.ShowTabsAndSpaces
        option.setFlags(flags)
        doc.setDefaultTextOption(option)

    @Slot(QQuickTextDocument, result="QVariantList")
    def tabPositions(self, qdoc) -> list:
        """Pozycje znaków tabulacji (do rysowania wypełnienia kropkami w edytorze)."""
        doc = _doc(qdoc)
        if doc is None:
            return []
        text = doc.toPlainText()
        return [i for i, ch in enumerate(text) if ch == "\t"]

    @Slot("QVariantList", result=str)
    def plainText(self, runs) -> str:
        return "".join(str(r.get("text", "")) for r in (runs or []))
