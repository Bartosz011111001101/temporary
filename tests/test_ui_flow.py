"""Test przepływu na prawdziwym interfejsie QML (bez okna na ekranie – platforma offscreen).

Scenariusz: nowy dokument → tytuł → sekcja i podsekcja z klawiatury → tekst i pogrubienie →
tabela z podpisem (Tab między komórkami) → przeciągnięcie bloku myszą → zapis →
ponowne otwarcie → porównanie. Test kończy się błędem przy każdym ostrzeżeniu QML.
"""
import os
from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, Qt, QUrl, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication, QKeyEvent
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

ROOT = Path(__file__).resolve().parent.parent
SHOTS = os.environ.get("QMLWORD_SHOTS", "")


@pytest.fixture
def ui(qapp):
    from qmlword.qt import (app_utils, autosave, document_model, outline_model,  # noqa: F401
                            page_preview, rich_text, search)

    messages = []

    def handler(mode, context, message):
        messages.append(message)

    previous = qInstallMessageHandler(handler)
    engine = QQmlApplicationEngine()
    engine.setInitialProperties({"startupFile": "", "screenshotPath": ""})
    engine.load(QUrl.fromLocalFile(str(ROOT / "qml" / "Main.qml")))
    assert engine.rootObjects(), messages
    window = engine.rootObjects()[0]
    window.setProperty("width", 1400)
    window.setProperty("height", 900)
    QTest.qWaitForWindowExposed(window)
    QTest.qWait(400)
    yield window, messages
    window.setProperty("allowClose", True)
    window.close()
    QTest.qWait(50)
    qInstallMessageHandler(previous)
    del engine


def find_item(window, name):
    """Szuka po drzewie wizualnym (delegaty ListView nie są dziećmi QObject okna)."""
    pending = [window.contentItem()]
    while pending:
        item = pending.pop()
        if item.objectName() == name:
            return item
        pending.extend(item.childItems())
    return None


def shot(window, name):
    if SHOTS:
        window.grabWindow().save(os.path.join(SHOTS, f"{name}.png"))


def doc_state(doc):
    return [doc.blockData(doc.blockIdAt(i)) for i in range(doc.rowCount())]


def text(data):
    return "".join(r["text"] for r in data.get("runs", []))


def type_text(window, value, wait=60):
    for ch in value:
        code = ord(ch.upper()) if ch.isascii() and ch.isalnum() else (Qt.Key.Key_Space.value if ch == " " else 0)
        for kind in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            QGuiApplication.sendEvent(window, QKeyEvent(kind, code, Qt.KeyboardModifier.NoModifier, ch))
    QTest.qWait(wait)


def key(window, k, mods=Qt.KeyboardModifier.NoModifier, wait=80):
    QTest.keyClick(window, k, mods)
    QTest.qWait(wait)


def commit(window):
    QTest.qWait(600)  # edytory zatwierdzają tekst po 450 ms bezczynności


def test_full_editing_flow(ui, tmp_path):
    window, messages = ui
    doc = window.findChild(QObject, "documentModel")
    editor = window.findChild(QObject, "editorController")
    outline = window.findChild(QObject, "outlineModel")
    assert doc and editor and outline

    # 1. Tytuł dokumentu
    first = doc.blockIdAt(0)
    assert editor.property("currentBlockId") == first, "pierwszy blok powinien mieć fokus po starcie"
    type_text(window, "Raport roczny")
    doc.setStyle(first, "title")
    commit(window)
    assert text(doc.blockData(first)) == "Raport roczny"
    assert doc.blockData(first)["style"] == "title"

    # 2. Enter → nowy akapit, Ctrl+Alt+1 → sekcja (Nagłówek 1)
    key(window, Qt.Key.Key_End)
    key(window, Qt.Key.Key_Return)
    type_text(window, "Wstęp")
    key(window, Qt.Key.Key_1, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier)
    commit(window)
    section = doc.blockIdAt(1)
    assert doc.blockType(section) == "heading" and text(doc.blockData(section)) == "Wstęp"
    assert outline.rowCount() == 1

    # 3. Treść sekcji i pogrubienie zaznaczenia (Ctrl+A w akapicie, Ctrl+B)
    key(window, Qt.Key.Key_End)
    key(window, Qt.Key.Key_Return)
    type_text(window, "Treść pierwszej sekcji")
    commit(window)
    body = doc.blockIdAt(2)
    key(window, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    key(window, Qt.Key.Key_B, Qt.KeyboardModifier.ControlModifier)
    commit(window)
    runs = doc.blockData(body)["runs"]
    assert runs == [{"text": "Treść pierwszej sekcji", "bold": True}]

    # 4. Podsekcja (przycisk w panelu = addSection) – tytuł jest zaznaczony, więc wpisanie go zastępuje
    sub = doc.addSection(section, True)
    QTest.qWait(150)
    type_text(window, "Szczegóły")
    commit(window)
    assert text(doc.blockData(sub)) == "Szczegóły" and doc.blockData(sub)["level"] == 2
    assert outline.rowCount() == 2

    # 5. Tabela z podpisem pod podsekcją; Tab przechodzi między komórkami
    sub_para = doc.blockIdAt(doc.indexOf(sub) + 1)
    table = doc.insertAfter(sub_para, "table", {"rows": 2, "cols": 2, "caption": True, "captionText": "Wyniki"})
    QTest.qWait(200)
    type_text(window, "Kolumna 1")
    key(window, Qt.Key.Key_Tab)
    type_text(window, "Kolumna 2")
    key(window, Qt.Key.Key_Tab)
    type_text(window, "10")
    key(window, Qt.Key.Key_Tab)
    type_text(window, "20")
    key(window, Qt.Key.Key_Tab)  # Tab w ostatniej komórce dodaje wiersz
    type_text(window, "30")
    commit(window)
    cells = doc.blockData(table)["table"]["cells"]
    assert [[text(c) for c in row] for row in cells] == [["Kolumna 1", "Kolumna 2"], ["10", "20"], ["30", ""]]
    caption = doc.blockIdAt(doc.indexOf(table) + 1)
    assert doc.blockType(caption) == "caption" and doc.blockData(caption)["caption"]["text"] == "Wyniki"
    shot(window, "flow-1-edited")

    # 6. Przeciągnięcie tabeli myszą (uchwyt w marginesie) nad sekcję „Wstęp”
    handle = find_item(window, "handle:" + table)
    target_row = find_item(window, "handle:" + section)
    assert handle is not None and target_row is not None
    start = handle.mapToScene(QPointF(handle.width() / 2, handle.height() / 2)).toPoint()
    over = target_row.mapToScene(QPointF(target_row.width() / 2, 1)).toPoint()
    QTest.mouseMove(window, start)
    QTest.qWait(100)
    QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    for step in range(1, 13):
        p = QPoint(start.x() + (over.x() - start.x()) * step // 12, start.y() + (over.y() - start.y()) * step // 12)
        QTest.mouseMove(window, p)
        QTest.qWait(30)
    QTest.qWait(100)
    QTest.mouseRelease(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, over)
    QTest.qWait(200)
    order = [doc.blockType(doc.blockIdAt(i)) for i in range(doc.rowCount())]
    assert order[:4] == ["paragraph", "table", "caption", "heading"], order
    assert doc.indexOf(caption) == doc.indexOf(table) + 1  # podpis przeniósł się razem z tabelą
    shot(window, "flow-2-after-drag")

    # 7. Cofnij przeniesienie z klawiatury i ponów
    key(window, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier, wait=200)
    assert doc.indexOf(table) > doc.indexOf(sub)
    key(window, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier, wait=200)
    assert doc.indexOf(table) == 1

    # 8. Przeniesienie podsekcji do nowej sekcji (operacja panelu nawigacji) i blokada pętli
    second = doc.addSection(section, False)
    QTest.qWait(100)
    type_text(window, "Druga sekcja")
    commit(window)
    assert doc.moveSection(sub, second, "into")
    assert doc.sectionInfo(sub)["parentId"] == second
    assert not doc.moveSection(second, sub, "into")

    # 9. Zapis, nowy dokument, ponowne otwarcie
    expected = doc_state(doc)
    path = tmp_path / "raport.qwd.json"
    assert doc.saveAs(QUrl.fromLocalFile(str(path)))
    assert not doc.property("modified")
    doc.newDocument()
    QTest.qWait(100)
    assert doc.rowCount() == 1
    assert doc.openFile(QUrl.fromLocalFile(str(path)))
    QTest.qWait(300)
    assert doc_state(doc) == expected
    assert outline.rowCount() == 3
    shot(window, "flow-3-reopened")

    # 10. Podgląd stron (paginacja jak w PDF) i eksport PDF
    window.setProperty("previewMode", True)
    QTest.qWait(400)
    shot(window, "flow-4-preview")
    window.setProperty("previewMode", False)
    assert doc.exportPdf(QUrl.fromLocalFile(str(tmp_path / "raport.pdf")))
    assert (tmp_path / "raport.pdf").read_bytes().startswith(b"%PDF")

    problems = [m for m in messages if ("qml" in m.lower() or "TypeError" in m or "ReferenceError" in m)
                and "no longer ships fonts" not in m]
    assert problems == [], "\n".join(problems)


def editor_item(window, block_id):
    return find_item(window, "editor:" + block_id)


def click_text(window, item, x_frac, y=None):
    y = item.height() / 2 if y is None else y
    pos = item.mapToScene(QPointF(item.width() * x_frac, y)).toPoint()
    QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pos)
    QTest.qWait(80)


def drag_select(window, item, x1, x2):
    a = item.mapToScene(QPointF(x1, item.height() / 2)).toPoint()
    b = item.mapToScene(QPointF(x2, item.height() / 2)).toPoint()
    QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, a)
    for step in range(1, 7):
        QTest.mouseMove(window, QPoint(a.x() + (b.x() - a.x()) * step // 6, a.y()))
        QTest.qWait(15)
    QTest.mouseRelease(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, b)
    QTest.qWait(150)


def test_selection_clipboard_painter_and_replace(ui):
    from PySide6.QtCore import QMetaObject, QMimeData, Q_ARG
    from PySide6.QtGui import QGuiApplication

    window, messages = ui
    doc = window.findChild(QObject, "documentModel")
    editor = window.findChild(QObject, "editorController")
    search = window.findChild(QObject, "searchController")

    # Trzy akapity wpisane z klawiatury
    type_text(window, "Ala ma kota")
    key(window, Qt.Key.Key_Return)
    type_text(window, "Kot ma Ale")
    key(window, Qt.Key.Key_Return)
    type_text(window, "trzeci akapit")
    commit(window)
    ids = [doc.blockIdAt(i) for i in range(3)]

    # 1. Zaznaczenie przez dwa akapity: Shift+↑ z końca trzeciego, pogrubienie, potem pisanie nad zaznaczeniem
    key(window, Qt.Key.Key_Home)
    key(window, Qt.Key.Key_Up, Qt.KeyboardModifier.ShiftModifier, wait=150)
    assert editor.property("rangeActive"), "Shift+↑ na pierwszym wierszu powinno zaznaczyć poprzedni blok"
    key(window, Qt.Key.Key_B, Qt.KeyboardModifier.ControlModifier, wait=200)
    assert doc.blockData(ids[1])["runs"] == [{"text": "Kot ma Ale", "bold": True}]
    type_text(window, "X", wait=200)
    assert doc.rowCount() == 2 and text(doc.blockData(ids[1])) == "Xtrzeci akapit"

    # 2. Kopiowanie zakresu i wklejenie (własny format schowka – struktura i formatowanie)
    QMetaObject.invokeMethod(editor, "setRange", Q_ARG("QVariant", {"blockId": ids[0], "pos": 4}),
                             Q_ARG("QVariant", {"blockId": ids[1], "pos": 1}))
    QMetaObject.invokeMethod(editor, "copy")
    md = QGuiApplication.clipboard().mimeData()
    assert md.hasFormat("application/x-qmlword-blocks") and md.hasHtml() and md.text() == "ma kota\nX"
    QMetaObject.invokeMethod(editor, "clearRange")
    last = doc.blockIdAt(doc.rowCount() - 1)
    doc.requestFocus(last, doc.blockLength(last), doc.blockLength(last), -1, -1)
    QTest.qWait(100)
    key(window, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier, wait=200)
    texts = [text(doc.blockData(doc.blockIdAt(i))) for i in range(doc.rowCount())]
    assert texts[-2:] == ["Xtrzeci akapitma kota", "X"], texts

    # 3. Wklejanie HTML z edytora tekstu: nagłówek, lista i tabela zachowują strukturę
    mime = QMimeData()
    mime.setHtml("<h2>Wklejony rozdział</h2><ul><li>punkt</li></ul><table><tr><td>a</td><td>b</td></tr></table>")
    mime.setText("Wklejony rozdział")
    QGuiApplication.clipboard().setMimeData(mime)
    QTest.qWait(50)
    key(window, Qt.Key.Key_End)
    key(window, Qt.Key.Key_Return)
    key(window, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier, wait=250)
    types = [doc.blockType(doc.blockIdAt(i)) for i in range(doc.rowCount())]
    assert types[-4:-1] == ["heading", "paragraph", "table"], types
    heading = doc.blockData(doc.blockIdAt(len(types) - 4))
    assert heading["level"] == 2 and doc.blockData(doc.blockIdAt(len(types) - 3))["para"]["list"] == "bullet"

    # 4. Malarz formatów: format z pogrubionego tekstu na zaznaczenie myszą w pierwszym akapicie
    doc.requestFocus(ids[1], 0, 1, -1, -1)   # „X” jest pogrubione
    QTest.qWait(100)
    QMetaObject.invokeMethod(editor, "startPainter", Q_ARG("QVariant", False))
    assert editor.property("painterActive")
    first_editor = editor_item(window, ids[0])
    drag_select(window, first_editor, 2, first_editor.width() * 0.08)
    assert not editor.property("painterActive")
    assert any(r.get("bold") for r in doc.blockData(ids[0])["runs"]), doc.blockData(ids[0])["runs"]

    # 5. Indeks dolny skrótem Ctrl+= na zaznaczeniu
    doc.requestFocus(ids[0], 0, 3, -1, -1)
    QTest.qWait(100)
    key(window, Qt.Key.Key_Equal, Qt.KeyboardModifier.ControlModifier, wait=200)
    assert doc.blockData(ids[0])["runs"][0].get("vertical") == "sub"

    # 6. Znajdź i zamień: całe wyrazy + format zamiany, jeden krok cofania
    doc.setBlockRuns(ids[0], [{"text": "kot i kotek, kot."}])
    search.setProperty("wholeWords", True)
    search.setProperty("query", "kot")
    QTest.qWait(50)
    assert search.property("count") == 2
    search.setProperty("replacement", "pies")
    search.setProperty("replaceFormat", {"bold": True})
    QMetaObject.invokeMethod(search, "replaceAll")
    assert doc.blockData(ids[0])["runs"] == [{"text": "pies", "bold": True}, {"text": " i kotek, "},
                                              {"text": "pies", "bold": True}, {"text": "."}]
    doc.undo()
    assert text(doc.blockData(ids[0])) == "kot i kotek, kot."

    problems = [m for m in messages if ("qml" in m.lower() or "TypeError" in m or "ReferenceError" in m)
                and "no longer ships fonts" not in m]
    assert problems == [], "\n".join(problems)
