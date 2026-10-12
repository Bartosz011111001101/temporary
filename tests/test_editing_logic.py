"""Logika nowych funkcji edycji: przebiegi, listy, zaznaczenie wielu bloków, wklejanie,
tabele (style, krawędzie, sortowanie, formuły, konwersja) oraz znajdź i zamień."""
from dataclasses import replace

import pytest

from qmlword.model import find, lists, range_ops, table_ops, table_style, text_ops
from qmlword.model.blocks import Block, ParagraphFormat, TableData, TextRun, plain_runs, plain_text
from qmlword.model.ops import OperationError


def text(block):
    return plain_text(block.runs)


# --- przebiegi ---------------------------------------------------------------------------

def test_apply_props_and_replace_keep_formatting():
    runs = (TextRun("Ala ", bold=True), TextRun("ma kota"))
    sup = text_ops.apply_props(runs, 4, 6, {"vertical": "super", "smallCaps": True})
    assert sup[1] == TextRun("ma", vertical="super", small_caps=True)
    replaced = text_ops.replace_in_runs(runs, 0, 3, "Ola")
    assert replaced[0] == TextRun("Ola ", bold=True)  # format pierwszego zastępowanego znaku
    assert text_ops.format_at(runs, 0).bold is True and text_ops.format_at(runs, 5).bold is None


@pytest.mark.parametrize("mode, expected", [
    ("upper", "ALA MA KOTA. ŻÓŁW"), ("lower", "ala ma kota. żółw"),
    ("title", "Ala Ma Kota. Żółw"), ("sentence", "Ala ma kota. Żółw"), ("toggle", "aLA MA kota. ŻÓŁw"),
])
def test_change_case(mode, expected):
    runs = (TextRun("Ala ma ", bold=True), TextRun("KOTA. żółW"))
    assert plain_text(text_ops.change_case(runs, 0, 17, mode)) == expected


# --- listy ---------------------------------------------------------------------------------

def item(kind, indent=0, style="", start=0, cont=False):
    return Block.paragraph("x", para=ParagraphFormat(list=kind, indent=indent, list_style=style,
                                                     list_start=start, list_continue=cont))


def test_list_markers_styles_levels_start_and_continue():
    blocks = (item("number"), item("number", 1), item("number", 1), item("number"),
              Block.paragraph("przerwa"), item("number", cont=True), item("number", start=10),
              item("number", style="upperRoman"), item("bullet"), item("bullet", 1),
              item("number", style="multilevel"), item("number", 1, style="multilevel"))
    markers = [i.marker for i in lists.list_infos(blocks)]
    assert markers[:4] == ["1.", "a)", "b)", "2."]
    assert markers[4] == ""
    assert markers[5:8] == ["3.", "10.", "I."]  # inny styl = nowa lista
    assert markers[8:10] == ["•", "◦"]
    assert markers[10:] == ["1.", "1.1."]


# --- zaznaczenie wielu bloków ------------------------------------------------------------------

@pytest.fixture
def three():
    a = Block.paragraph(runs=(TextRun("Pierwszy ", bold=True), TextRun("akapit")))
    t = Block.new_table(1, 1)
    c = Block.new_caption(t.id, "Podpis")
    b = Block.heading(2, "Drugi akapit")
    return (a, t, c, b)


def test_range_extract_and_text(three):
    span = range_ops.normalize_span(three, three[3].id, 5, three[0].id, 9)  # odwrotny kierunek
    assert (span.start_index, span.start_pos, span.end_index, span.end_pos) == (0, 9, 3, 5)
    frag = range_ops.extract_range(three, span)
    assert [b.type for b in frag] == ["paragraph", "table", "caption", "heading"]
    assert text(frag[0]) == "akapit" and text(frag[-1]) == "Drugi"
    assert frag[2].caption.target_id == frag[1].id  # podpis wskazuje na skopiowaną tabelę
    assert "akapit\n" in range_ops.range_plain_text(three, span)


def test_range_delete_merges_endpoints(three):
    span = range_ops.normalize_span(three, three[0].id, 9, three[3].id, 6)
    blocks, focus, pos = range_ops.delete_range(three, span)
    assert len(blocks) == 1 and focus == three[0].id and pos == 9
    assert blocks[0].runs == (TextRun("Pierwszy ", bold=True), TextRun("akapit"))


def test_range_format_and_case(three):
    span = range_ops.normalize_span(three, three[0].id, 0, three[3].id, 5)
    formatted = range_ops.format_range(three, span, {"italic": True})
    assert all(r.italic for r in formatted[0].runs)
    assert formatted[3].runs[0] == TextRun("Drugi", italic=True)
    upper = range_ops.case_range(three, span, "upper")
    assert text(upper[3]) == "DRUGI akapit"


def test_paste_fragment_merges_first_and_last_paragraph():
    target = Block.paragraph("Początek|koniec")
    frag = (Block.paragraph(runs=(TextRun("A", bold=True),)), Block.new_table(1, 1), Block.paragraph("Z"))
    blocks, focus, pos = range_ops.insert_fragment((target,), target.id, 9, 9, frag)
    assert [b.type for b in blocks] == ["paragraph", "table", "paragraph"]
    assert plain_text(blocks[0].runs) == "Początek|A" and plain_text(blocks[2].runs) == "Zkoniec"
    assert (focus, pos) == (blocks[2].id, 1)
    single, _, pos = range_ops.insert_fragment((target,), target.id, 0, 8, (Block.paragraph("Start"),))
    assert plain_text(single[0].runs) == "Start|koniec" and pos == 5


def test_text_table_conversion_roundtrip():
    rows = (Block.paragraph("Imię;Wiek"), Block.paragraph(runs=(TextRun("Ala", bold=True), TextRun(";7"))))
    blocks, table_id = range_ops.text_to_table(rows, 0, 1, ";")
    t = blocks[0].table
    assert (t.rows, t.cols) == (2, 2) and t.cells[1][0].runs == (TextRun("Ala", bold=True),)
    back, _ = range_ops.table_to_text(blocks, table_id, "\t")
    assert [plain_text(b.runs) for b in back] == ["Imię\tWiek", "Ala\t7"]
    with pytest.raises(OperationError):
        range_ops.text_to_table((Block.new_table(1, 1),), 0, 0, ";")


# --- tabele ---------------------------------------------------------------------------------------

def filled(rows):
    t = TableData.create(len(rows), len(rows[0]))
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            t = table_ops.set_cell_runs(t, r, c, plain_runs(value))
    return t


def test_table_style_appearance_and_borders():
    t = replace(filled([["A", "B"], ["1", "2"], ["3", "4"]]), style="light", banded_rows=True, first_column=True)
    app = table_style.appearance(t)
    assert app[0][0]["bold"] and app[1][0]["bold"] and not app[1][1]["bold"]
    assert app[1][0]["left"]["w"] == 0 and app[1][0]["top"]["w"] > 0  # tylko linie poziome
    assert app[2][1]["background"]  # pasy
    boxed = table_ops.set_cells_borders(t, 1, 0, 2, 1, "outside")
    app = table_style.appearance(boxed)
    assert app[1][0]["left"]["w"] > 0 and app[2][1]["right"]["w"] > 0 and app[1][1]["left"]["w"] == 0


def test_sort_rows_numeric_and_text():
    t = filled([["Nazwa", "Ilość"], ["gruszka", "10"], ["Ananas", "2"], ["banan", "1 240,5"]])
    by_qty = table_ops.sort_rows(t, 1)
    assert [plain_text(r[0].runs) for r in by_qty.cells[1:]] == ["Ananas", "gruszka", "banan"]
    by_name = table_ops.sort_rows(t, 0, descending=True)
    assert [plain_text(r[0].runs) for r in by_name.cells[1:]] == ["gruszka", "banan", "Ananas"]
    merged = table_ops.merge_cells(t, 1, 0, 2, 0)
    with pytest.raises(OperationError):
        table_ops.sort_rows(merged, 1)


def test_formulas_compute_and_update():
    t = filled([["Pozycja", "Kwota"], ["a", "1 000,50"], ["b", "2"], ["Razem", ""]])
    t = table_ops.set_cell_formula(t, 3, 1, "SUMA(POWYŻEJ)")
    assert plain_text(t.cells[3][1].runs) == "1 002,50"
    t = table_ops.set_cell_runs(t, 2, 1, plain_runs("3"))  # zmiana danych przelicza formułę
    assert plain_text(t.cells[3][1].runs) == "1 003,50"
    t = table_ops.set_cell_formula(t, 0, 0, "=ZAOKR(B2*2; 0) + MAX(B2:B3)")
    assert plain_text(t.cells[0][0].runs) == "3 001,50"
    t = table_ops.set_cell_formula(t, 0, 0, "=1/0")
    assert plain_text(t.cells[0][0].runs) == "#BŁĄD"
    assert table_ops.set_cell_runs(t, 0, 0, plain_runs("x")) is t  # komórka z formułą nie jest edytowalna


# --- znajdź i zamień ---------------------------------------------------------------------------------

def test_find_whole_words_case_and_format():
    p = Block.paragraph(runs=(TextRun("kot "), TextRun("Kot", bold=True), TextRun(" kotek kot")))
    h = Block.heading(1, "Kot w nagłówku")
    blocks = (p, h)
    assert len(find.find_matches(blocks, "kot")) == 5
    assert len(find.find_matches(blocks, "kot", whole_words=True)) == 4
    assert len(find.find_matches(blocks, "Kot", case_sensitive=True)) == 2
    bold = find.find_matches(blocks, "kot", fmt={"bold": True})
    assert [(m.block_id, m.start) for m in bold] == [(p.id, 4), (h.id, 0)]  # nagłówek jest pogrubiony stylem
    only_h1 = find.find_matches(blocks, "kot", fmt={"style": "h1"})
    assert [m.block_id for m in only_h1] == [h.id]
    spans = find.find_matches(blocks, "", fmt={"bold": True, "style": "body"})
    assert [(m.start, m.length) for m in spans] == [(4, 3)]


def test_replace_text_format_only_and_cells():
    p = Block.paragraph("kot i kot")
    t = replace(Block.new_table(1, 1), table=filled([["kot"]]))
    blocks = (p, t)
    matches = find.find_matches(blocks, "kot", whole_words=True)
    out, count = find.replace_matches(blocks, matches, "pies", {"bold": True})
    assert count == 3
    assert out[0].runs == (TextRun("pies", bold=True), TextRun(" i "), TextRun("pies", bold=True))
    assert plain_text(out[1].table.cells[0][0].runs) == "pies"
    fmt_only, _ = find.replace_matches(blocks, matches[:1], "", {"highlight": "#fff3a3"})
    assert fmt_only[0].runs[0] == TextRun("kot", highlight="#fff3a3")
