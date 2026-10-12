"""Usługi wokół modelu: wyszukiwanie, drzewo sekcji, kopia robocza i odzyskiwanie."""
import os

from PySide6.QtCore import QStandardPaths
from PySide6.QtTest import QTest

from qmlword.qt.autosave import AutosaveManager
from qmlword.qt.document_model import DocumentModel
from qmlword.qt.outline_model import OutlineModel
from qmlword.qt.search import SearchController


def test_search_finds_text_in_paragraphs_cells_and_captions(qapp):
    doc = DocumentModel()
    first = doc.blockIdAt(0)
    doc.setBlockRuns(first, [{"text": "Koszty i KOSZTY"}])
    table = doc.insertBlock(-1, "table", {"rows": 1, "cols": 2, "caption": True, "captionText": "Koszty roczne"})
    doc.setCellRuns(table, 0, 1, [{"text": "koszty"}])
    focus = []
    doc.focusRequested.connect(lambda *a: focus.append(a))
    search = SearchController()
    search.document = doc
    search.query = "koszty"
    assert search.count == 4
    search.next()
    assert search.label == "1 z 4" and focus[-1] == (first, 0, 6, -1, -1)
    search.previous()
    assert search.current == 3  # zawinięcie od początku na koniec
    search.next()
    search.next()
    search.next()
    assert focus[-1][3:] == (0, 1)  # wynik w komórce (wiersz 0, kolumna 1)
    search.caseSensitive = True
    assert search.count == 1


def test_outline_collapse_and_reveal(qapp):
    doc = DocumentModel()
    a = doc.addSection("", False)
    a1 = doc.addSection(a, True)
    a1x = doc.addSection(a1, True)
    outline = OutlineModel()
    outline.document = doc
    assert outline.rowCount() == 3
    outline.collapseAll()
    assert outline.rowCount() == 1
    outline.reveal(a1x)
    assert outline.rowCount() == 3 and outline.rowOf(a1x) == 2
    outline.toggle(a1)
    assert outline.rowCount() == 2
    assert outline.isDescendant(a1x, a) and not outline.isDescendant(a, a1x)


def test_draft_is_saved_and_recovered_by_next_session(qapp, tmp_path):
    QStandardPaths.setTestModeEnabled(True)
    doc = DocumentModel()
    first = doc.blockIdAt(0)
    doc.setBlockRuns(first, [{"text": "Niezapisany tekst"}])
    crashed = AutosaveManager()
    crashed.document = doc
    crashed.saveDraft()
    # Symulacja awarii: blokada sesji zostaje zwolniona bez sprzątania kopii.
    crashed._lock.unlock()

    fresh_doc = DocumentModel()
    survivor = AutosaveManager()
    survivor.document = fresh_doc
    items = survivor.findRecoverable()
    mine = [i for i in items if i["session"] == crashed._session]
    assert mine, items
    assert survivor.recover(crashed._session)
    assert fresh_doc.modified
    assert fresh_doc.blockData(fresh_doc.blockIdAt(0))["runs"][0]["text"] == "Niezapisany tekst"
    assert not os.path.exists(mine[0]["draft"])
    survivor.shutdown()
    QTest.qWait(10)
