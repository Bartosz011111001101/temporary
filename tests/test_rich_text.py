"""Most edytor ↔ model: wczytanie przebiegów do QTextDocument i odczyt z powrotem."""
from PySide6.QtGui import QFont, QTextDocument

from qmlword.qt.rich_text import RichTextBridge, extract_paragraphs


def make_doc(qapp, runs, bold_base=False):
    doc = QTextDocument()
    font = QFont("Calibri")
    font.setPointSizeF(11)
    font.setBold(bold_base)
    doc.setDefaultFont(font)
    RichTextBridge.load(doc, runs, {"align": "center", "lineHeight": 1.5})
    return doc


def test_load_and_extract_roundtrip(qapp):
    runs = [{"text": "Ala ", "bold": True}, {"text": "ma\nkota", "italic": True, "color": "#b3261e"},
            {"text": " link", "link": "https://example.com"}, {"text": "!", "highlight": "#fff3a3", "fontSize": 14}]
    doc = make_doc(qapp, runs)
    assert extract_paragraphs(doc) == [runs]


def test_merge_format_sets_and_clears_properties(qapp):
    doc = make_doc(qapp, [{"text": "abcdef"}])
    RichTextBridge.merge_format(doc, 1, 3, {"bold": True, "color": "#2a5d9f"})
    assert extract_paragraphs(doc)[0] == [{"text": "a"}, {"text": "bc", "bold": True, "color": "#2a5d9f"},
                                          {"text": "def"}]
    RichTextBridge.merge_format(doc, 0, 6, {"bold": None, "color": ""})
    assert extract_paragraphs(doc)[0] == [{"text": "abcdef"}]


def test_empty_selection_formats_word_under_cursor(qapp):
    doc = make_doc(qapp, [{"text": "jeden dwa"}])
    start, end = RichTextBridge.merge_format(doc, 7, 7, {"italic": True})
    assert (start, end) == (6, 9)
    assert extract_paragraphs(doc)[0][-1] == {"text": "dwa", "italic": True}


def test_format_at_resolves_style_defaults(qapp):
    doc = make_doc(qapp, [{"text": "Nagłówek"}, {"text": " zwykły", "bold": False}], bold_base=True)
    assert RichTextBridge.format_at(doc, 2, 2)["bold"] is True       # z czcionki stylu
    assert RichTextBridge.format_at(doc, 10, 12)["bold"] is False    # jawnie wyłączone


def test_extract_range_for_split(qapp):
    doc = make_doc(qapp, [{"text": "Przed", "bold": True}, {"text": "Po"}])
    assert extract_paragraphs(doc, 0, 3) == [[{"text": "Prz", "bold": True}]]
    assert extract_paragraphs(doc, 3, 7) == [[{"text": "ed", "bold": True}, {"text": "Po"}]]
