"""Konwersja formatów znaków Qt (QTextCharFormat) ↔ przebiegi modelu (słowniki jak w JSON).

Wspólne dla edytora (``qt/rich_text.py``) i importu HTML ze schowka (``html_import.py``).
Zapisywane są tylko właściwości ustawione jawnie – reszta dziedziczy się ze stylu akapitu.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont, QTextCharFormat, QTextDocument, QTextFormat

from ..model.styles import LINK_COLOR

P = QTextFormat.Property
LINE_SEPARATOR = " "
OBJECT_REPLACEMENT = "￼"
VERTICAL_TO_QT = {
    "super": QTextCharFormat.VerticalAlignment.AlignSuperScript,
    "sub": QTextCharFormat.VerticalAlignment.AlignSubScript,
}


def char_format_for_run(run: dict) -> QTextCharFormat:
    fmt = QTextCharFormat()
    if run.get("bold") is not None:
        fmt.setFontWeight(QFont.Weight.Bold if run["bold"] else QFont.Weight.Normal)
    if run.get("italic") is not None:
        fmt.setFontItalic(bool(run["italic"]))
    if run.get("underline") is not None:
        fmt.setFontUnderline(bool(run["underline"]))
    if run.get("strike") is not None:
        fmt.setFontStrikeOut(bool(run["strike"]))
    if run.get("color"):
        fmt.setForeground(QBrush(QColor(run["color"])))
    if run.get("highlight"):
        fmt.setBackground(QBrush(QColor(run["highlight"])))
    if run.get("fontFamily"):
        fmt.setFontFamilies([run["fontFamily"]])
    if run.get("fontSize"):
        fmt.setFontPointSize(float(run["fontSize"]))
    if run.get("vertical") in VERTICAL_TO_QT:
        fmt.setVerticalAlignment(VERTICAL_TO_QT[run["vertical"]])
    if run.get("smallCaps") is not None:
        fmt.setFontCapitalization(QFont.Capitalization.SmallCaps if run["smallCaps"]
                                  else QFont.Capitalization.MixedCase)
    if run.get("link"):
        fmt.setAnchor(True)
        fmt.setAnchorHref(run["link"])
        # Wygląd linku jest tylko prezentacją – nie trafia do modelu.
        fmt.setForeground(QBrush(QColor(run.get("color") or LINK_COLOR)))
        fmt.setFontUnderline(True)
    return fmt


def run_from_format(text: str, fmt: QTextCharFormat) -> dict:
    run: dict = {"text": text}
    is_link = fmt.isAnchor() and bool(fmt.anchorHref())
    if fmt.hasProperty(P.FontWeight):
        run["bold"] = fmt.fontWeight() >= QFont.Weight.DemiBold.value
    if fmt.hasProperty(P.FontItalic):
        run["italic"] = fmt.fontItalic()
    if not is_link:
        if fmt.hasProperty(P.TextUnderlineStyle) or fmt.hasProperty(P.FontUnderline):
            run["underline"] = fmt.fontUnderline()
    if fmt.hasProperty(P.FontStrikeOut):
        run["strike"] = fmt.fontStrikeOut()
    if fmt.hasProperty(P.ForegroundBrush) and fmt.foreground().style() != Qt.BrushStyle.NoBrush:
        color = fmt.foreground().color().name()
        if not (is_link and color == LINK_COLOR):
            run["color"] = color
    if fmt.hasProperty(P.BackgroundBrush) and fmt.background().style() != Qt.BrushStyle.NoBrush:
        run["highlight"] = fmt.background().color().name()
    if fmt.hasProperty(P.FontFamilies):
        families = fmt.fontFamilies()
        if families:
            run["fontFamily"] = str(families[0])
    if fmt.hasProperty(P.FontPointSize) and fmt.fontPointSize() > 0:
        run["fontSize"] = round(fmt.fontPointSize() * 2) / 2
    if fmt.hasProperty(P.TextVerticalAlignment):
        va = fmt.verticalAlignment()
        if va == QTextCharFormat.VerticalAlignment.AlignSuperScript:
            run["vertical"] = "super"
        elif va == QTextCharFormat.VerticalAlignment.AlignSubScript:
            run["vertical"] = "sub"
    if fmt.hasProperty(P.FontCapitalization):
        caps = fmt.fontCapitalization()
        if caps == QFont.Capitalization.SmallCaps:
            run["smallCaps"] = True
        elif caps == QFont.Capitalization.MixedCase:
            run["smallCaps"] = False
    if is_link:
        run["link"] = fmt.anchorHref()
    return run


def same_format(a: dict, b: dict) -> bool:
    return {k: v for k, v in a.items() if k != "text"} == {k: v for k, v in b.items() if k != "text"}


def append_run(runs: list, run: dict) -> None:
    if not run["text"]:
        return
    if runs and same_format(runs[-1], run):
        runs[-1]["text"] += run["text"]
    else:
        runs.append(run)


def block_runs(block, start: int = 0, end: int = 1 << 30) -> list[dict]:
    runs: list[dict] = []
    it = block.begin()
    while not it.atEnd():
        frag = it.fragment()
        if frag.isValid():
            f_start = frag.position()
            f_end = f_start + frag.length()
            s, e = max(f_start, start), min(f_end, end)
            if s < e:
                text = frag.text()[s - f_start:e - f_start]
                text = text.replace(LINE_SEPARATOR, "\n").replace(OBJECT_REPLACEMENT, "")
                append_run(runs, run_from_format(text, frag.charFormat()))
        it += 1
    return runs


def extract_paragraphs(doc: QTextDocument, start: int = 0, end: int = -1) -> list[list[dict]]:
    """Przebiegi z zakresu [start, end) – osobna lista dla każdego akapitu ``QTextDocument``."""
    if end < 0:
        end = doc.characterCount() - 1
    paragraphs: list[list[dict]] = []
    block = doc.findBlock(start)
    while block.isValid() and block.position() <= end:
        paragraphs.append(block_runs(block, start, end))
        block = block.next()
    return paragraphs or [[]]
