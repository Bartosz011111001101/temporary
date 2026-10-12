"""Model bloków: serializacja, walidacja danych i operacje na tabelach."""
from dataclasses import replace

import pytest

from qmlword.model import table_ops
from qmlword.model.blocks import (Block, TableCell, TableData, TextRun, normalize_runs, plain_runs,
                                  runs_from_json)
from qmlword.model.ops import OperationError


def test_runs_normalize_merges_same_format_and_drops_empty():
    runs = normalize_runs([TextRun("Ala "), TextRun("ma"), TextRun(""), TextRun(" kota", bold=True)])
    assert [r.text for r in runs] == ["Ala ma", " kota"]
    assert runs[1].bold is True


def test_run_json_keeps_only_explicit_properties():
    run = TextRun("x", bold=True, color="#AABBCC", font_size=14)
    data = run.to_json()
    assert data == {"text": "x", "bold": True, "color": "#AABBCC", "fontSize": 14}
    assert TextRun.from_json(data) == replace(run, color="#aabbcc")


def test_invalid_run_values_are_sanitized():
    runs = runs_from_json([{"text": "a", "color": "red; drop table", "fontSize": "huge", "bold": "yes"}, 42, "b"])
    assert runs[0].color == "" and runs[0].font_size == 0 and runs[0].bold is None
    assert runs[-1].text.endswith("b")


@pytest.mark.parametrize("block", [
    Block.paragraph("Tekst", style="title"),
    Block.heading(3, "Sekcja"),
    Block.new_table(3, 4),
    Block.new_image("img/a.png"),
    Block.new_caption("b123", "Opis"),
    Block.page_break(),
    Block.placeholder(),
])
def test_block_json_roundtrip(block):
    assert Block.from_json(block.to_json()) == block


def test_unknown_block_is_preserved_verbatim():
    raw = {"id": "x1", "type": "chart", "series": [1, 2, 3]}
    warnings = []
    block = Block.from_json(raw, warnings)
    assert block.type == "unknown"
    assert block.to_json() == raw
    assert warnings


def test_block_without_type_is_skipped():
    warnings = []
    assert Block.from_json({"id": "a"}, warnings) is None
    assert Block.from_json("nonsense", warnings) is None
    assert len(warnings) == 2


def test_table_normalize_fixes_ragged_rows_and_overlapping_spans():
    table = TableData(cells=((TableCell(row_span=2, col_span=2), TableCell()),
                             (TableCell(col_span=5),)),
                      col_widths=(3, 1)).normalized()
    assert table.rows == 2 and table.cols == 2
    assert table.cells[0][0].row_span == 2 and table.cells[0][0].col_span == 2
    assert table.cells[1][0].col_span == 1  # przykryta komórka nie może być kotwicą
    assert abs(sum(table.col_widths) - 1) < 1e-6
    assert table.col_widths[0] == pytest.approx(0.75)


def test_table_insert_and_remove_rows_and_columns():
    t = TableData.create(2, 2)
    t = table_ops.set_cell_runs(t, 1, 1, plain_runs("D"))
    t = table_ops.insert_row(t, 1)
    assert t.rows == 3 and t.cells[2][1].runs[0].text == "D"
    t = table_ops.insert_column(t, 0)
    assert t.cols == 3 and t.cells[2][2].runs[0].text == "D"
    assert abs(sum(t.col_widths) - 1) < 1e-5
    t = table_ops.remove_column(t, 0)
    t = table_ops.remove_row(t, 1)
    assert (t.rows, t.cols) == (2, 2) and t.cells[1][1].runs[0].text == "D"


def test_merge_and_split_cells_keeps_text():
    t = TableData.create(3, 3)
    t = table_ops.set_cell_runs(t, 0, 0, plain_runs("A"))
    t = table_ops.set_cell_runs(t, 0, 1, plain_runs("B"))
    merged = table_ops.merge_cells(t, 0, 0, 1, 1)
    anchor = merged.cells[0][0]
    assert (anchor.row_span, anchor.col_span) == (2, 2)
    assert "".join(r.text for r in anchor.runs) == "A\nB"
    assert merged.anchor_of(1, 1) == (0, 0)
    split = table_ops.split_cell(merged, 1, 1)
    assert split.cells[0][0].row_span == 1 and not split.is_covered(1, 1)


def test_merge_expands_to_existing_spans_and_rows_adjust_spans():
    t = table_ops.merge_cells(TableData.create(4, 3), 1, 0, 2, 0)
    wider = table_ops.merge_cells(t, 2, 0, 2, 1)  # przecina istniejące scalenie -> rozszerzenie
    assert (wider.cells[1][0].row_span, wider.cells[1][0].col_span) == (2, 2)
    grown = table_ops.insert_row(t, 2)  # wiersz wewnątrz scalenia
    assert grown.cells[1][0].row_span == 3
    shrunk = table_ops.remove_row(t, 1)  # usunięcie wiersza kotwicy
    assert shrunk.cells[1][0].row_span == 1


def test_table_limits_raise_operation_error():
    with pytest.raises(OperationError):
        table_ops.remove_row(TableData.create(1, 2), 0)
    with pytest.raises(OperationError):
        table_ops.merge_cells(TableData.create(2, 2), 0, 0, 0, 0)
