"""DocumentModel: cofanie/ponawianie, edycja tekstu, przenoszenie, zapis i ponowne otwarcie."""
import os
import time

import pytest
from PySide6.QtCore import QUrl

from qmlword.qt.document_model import DocumentModel


@pytest.fixture
def model(qapp):
    m = DocumentModel()
    yield m
    m.deleteLater()


def types(m):
    return [m.blockType(m.blockIdAt(i)) for i in range(m.rowCount())]


def text_of(m, block_id):
    return "".join(r["text"] for r in m.blockData(block_id).get("runs", []))


def test_typing_is_merged_into_one_undo_step(model):
    first = model.blockIdAt(0)
    for text in ("A", "Al", "Ala"):
        model.setBlockRuns(first, [{"text": text}])
    assert text_of(model, first) == "Ala" and model.modified
    model.undo()
    assert text_of(model, first) == "" and not model.modified
    model.redo()
    assert text_of(model, first) == "Ala"


def test_editor_commits_do_not_reset_own_editor_but_undo_does(model):
    resets = []
    model.blockReset.connect(resets.append)
    first = model.blockIdAt(0)
    model.setBlockRuns(first, [{"text": "x"}])
    assert resets == []
    model.undo()
    assert resets == [first]


def test_split_merge_and_paste_paragraphs(model):
    first = model.blockIdAt(0)
    new_id = model.splitBlock(first, [{"text": "Raz"}], [{"text": "Dwa"}])
    assert [text_of(model, model.blockIdAt(i)) for i in range(2)] == ["Raz", "Dwa"]
    assert model.mergeWithPrevious(new_id, [{"text": "Dwa"}])
    assert model.rowCount() == 1 and text_of(model, first) == "RazDwa"
    last = model.setBlockParagraphs(first, [[{"text": "a"}], [{"text": "b"}], [{"text": "c"}]])
    assert model.rowCount() == 3 and text_of(model, last) == "c"


def test_flow_sections_table_caption_move_save_reopen(model, tmp_path):
    title = model.blockIdAt(0)
    model.setStyle(title, "title")
    model.setBlockRuns(title, [{"text": "Raport"}])
    sec = model.addSection("", False)
    model.setHeadingTitle(sec, "Wstęp")
    sub = model.addSection(sec, True)
    model.setHeadingTitle(sub, "Szczegóły")
    para = model.blockIdAt(model.indexOf(sub) + 1)
    model.setBlockRuns(para, [{"text": "Treść podsekcji", "bold": True}])
    table = model.insertAfter(para, "table", {"rows": 2, "cols": 2, "caption": True, "captionText": "Dane"})
    model.setCellRuns(table, 0, 0, [{"text": "Kolumna"}])
    assert types(model)[-2:] == ["table", "caption"]

    # Przeniesienie tabeli (z podpisem) na początek sekcji „Wstęp”.
    assert model.moveBlock(table, model.indexOf(sec) + 1)
    i = model.indexOf(table)
    assert model.blockType(model.blockIdAt(i + 1)) == "caption"
    assert model.captionInfo(model.blockIdAt(i + 1)) == {"label": "Tabela", "number": 1}

    # Podsekcja do nowej sekcji głównej (drag and drop w nawigacji).
    other = model.addSection(sec, False)
    assert model.moveSection(sub, other, "into")
    assert model.sectionInfo(sub)["parentId"] == other
    assert model.moveSectionProblem(other, sub, "into").startswith("Nie można")

    path = tmp_path / "raport"
    assert model.saveAs(QUrl.fromLocalFile(str(path)))
    assert model.filePath.endswith(".qwd.json") and not model.modified
    snapshot = [model.blockData(model.blockIdAt(i)) for i in range(model.rowCount())]

    reopened = DocumentModel()
    assert reopened.openFile(QUrl.fromLocalFile(model.filePath))
    assert [reopened.blockData(reopened.blockIdAt(i)) for i in range(reopened.rowCount())] == snapshot
    reopened.deleteLater()


def test_save_errors_are_reported(model, tmp_path):
    errors = []
    model.errorOccurred.connect(lambda t, m: errors.append(t))
    assert not model.saveAs(str(tmp_path / "nie" / "istnieje" / "x.qwd.json"))
    assert errors and model.modified is False  # pusty dokument nie był zmieniony
    assert not model.openFile(str(tmp_path / "brak.qwd.json"))
    assert len(errors) == 2


def test_relative_image_paths_follow_save_as(model, tmp_path):
    img_dir = tmp_path / "a" / "img"
    img_dir.mkdir(parents=True)
    (img_dir / "x.png").write_bytes(b"\x89PNG")
    assert model.saveAs(str(tmp_path / "a" / "doc.qwd.json"))
    image = model.insertBlock(-1, "image", {"path": str(img_dir / "x.png")})
    assert model.blockData(image)["image"]["path"] == "img/x.png"
    (tmp_path / "b").mkdir()
    assert model.saveAs(str(tmp_path / "b" / "doc.qwd.json"))
    stored = model.blockData(image)["image"]["path"]
    assert os.path.normpath(os.path.join(tmp_path / "b", stored)) == os.path.normpath(img_dir / "x.png")


def test_move_rows_signal_keeps_rows_consistent(model):
    ids = [model.insertBlock(-1, "paragraph", {"text": str(i)}) for i in range(5)]
    moves = []
    model.rowsMoved.connect(lambda *a: moves.append(a))
    assert model.moveBlock(ids[4], 1)
    assert moves, "przeniesienie powinno być sygnalizowane jako ruch wierszy, nie reset"
    assert model.blockIdAt(1) == ids[4]
    model.undo()
    assert model.blockIdAt(model.rowCount() - 1) == ids[4]
