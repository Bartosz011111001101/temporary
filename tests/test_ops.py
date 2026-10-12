"""Struktura dokumentu: sekcje, przenoszenie sekcji i bloków, podpisy, numeracja."""
import pytest

from qmlword.model import ops
from qmlword.model.blocks import Block
from qmlword.model.ops import OperationError


def doc_with_sections():
    """A(1) [a1, A1(2) [x], A2(2)] B(1) [b1, B1(2), B1a(3)]"""
    blocks = [
        Block.heading(1, "A"), Block.paragraph("a1"),
        Block.heading(2, "A1"), Block.paragraph("x"),
        Block.heading(2, "A2"),
        Block.heading(1, "B"), Block.paragraph("b1"),
        Block.heading(2, "B1"), Block.heading(3, "B1a"),
    ]
    return tuple(blocks), {b.plain_text(): b.id for b in blocks}


def titles(blocks):
    return [(b.plain_text(), b.level if b.type == "heading" else None) for b in blocks]


def test_outline_builds_tree_with_numbers_and_parents():
    blocks, ids = doc_with_sections()
    entries = {e.title: e for e in ops.outline(blocks)}
    assert entries["A1"].parent_id == ids["A"] and entries["A1"].number == "1.1"
    assert entries["B1a"].number == "2.1.1" and entries["B1a"].depth == 2
    assert entries["A"].has_children and not entries["A2"].has_children


def test_move_section_before_keeps_content_and_sets_level():
    blocks, ids = doc_with_sections()
    result = ops.move_section(blocks, ids["B"], ids["A"], ops.DROP_BEFORE)
    assert titles(result)[:5] == [("B", 1), ("b1", None), ("B1", 2), ("B1a", 3), ("A", 1)]
    assert sorted(b.id for b in result) == sorted(b.id for b in blocks)  # nic nie zginęło


def test_move_subsection_into_other_section_changes_levels_of_whole_subtree():
    blocks, ids = doc_with_sections()
    result = ops.move_section(blocks, ids["B1"], ids["A1"], ops.DROP_INTO)
    t = titles(result)
    # B1 ląduje jako ostatnie dziecko A1 (poziom 3), jego dziecko B1a schodzi na poziom 4.
    assert t[t.index(("x", None)) + 1] == ("B1", 3)
    assert ("B1a", 4) in t
    assert len(result) == len(blocks)


def test_move_section_after_target_goes_behind_its_subtree():
    blocks, ids = doc_with_sections()
    result = ops.move_section(blocks, ids["A2"], ids["B"], ops.DROP_AFTER)
    assert titles(result)[-1] == ("A2", 1)


def test_cannot_move_section_into_its_own_subsection():
    blocks, ids = doc_with_sections()
    with pytest.raises(OperationError, match="własnej podsekcji"):
        ops.move_section(blocks, ids["B"], ids["B1a"], ops.DROP_INTO)
    assert ops.move_section(blocks, ids["B"], ids["B"], ops.DROP_INTO) is None


def test_section_move_respects_max_depth():
    blocks = (Block.heading(1, "R"), Block.heading(6, "deep"), Block.heading(1, "S"), Block.heading(2, "S1"))
    with pytest.raises(OperationError, match="zagnieżdżenia"):
        ops.move_section(blocks, blocks[2].id, blocks[1].id, ops.DROP_INTO)


def test_move_block_carries_caption_and_section_content():
    table = Block.new_table(2, 2)
    caption = Block.new_caption(table.id, "Wyniki")
    blocks = (Block.paragraph("p0"), Block.heading(1, "H"), Block.paragraph("p1"), table, caption, Block.paragraph("end"))
    moved = ops.move_block(blocks, table.id, 0)
    assert [b.id for b in moved[:2]] == [table.id, caption.id]
    moved_by_caption = ops.move_block(blocks, caption.id, len(blocks))
    assert [b.id for b in moved_by_caption[-2:]] == [table.id, caption.id]
    section = ops.move_block(blocks, blocks[1].id, 0)  # nagłówek przenosi całą sekcję
    assert [b.plain_text() for b in section[:3]] == ["H", "p1", ""]


def test_cannot_drop_between_element_and_caption():
    table = Block.new_table(1, 1)
    caption = Block.new_caption(table.id)
    p = Block.paragraph("p")
    blocks = (p, table, caption)
    result = ops.move_block(blocks, p.id, 2)  # między tabelę i podpis
    assert [b.id for b in result] == [table.id, caption.id, p.id]


def test_cannot_drop_section_inside_itself():
    blocks, ids = doc_with_sections()
    with pytest.raises(OperationError):
        ops.move_block(blocks, ids["A"], 3)


def test_change_section_level_and_sibling_moves():
    blocks, ids = doc_with_sections()
    promoted = ops.change_section_level(blocks, ids["B1"], -1)
    assert ("B1", 1) in titles(promoted) and ("B1a", 2) in titles(promoted)
    with pytest.raises(OperationError):
        ops.change_section_level(blocks, ids["A"], -1)
    swapped = ops.move_section_sibling(blocks, ids["A2"], -1)
    assert titles(swapped)[:3] == [("A", 1), ("a1", None), ("A2", 2)]
    assert ops.move_section_sibling(blocks, ids["A"], -1) is None


def test_add_section_and_subsection():
    blocks, ids = doc_with_sections()
    with_child, new_id = ops.add_section(blocks, ids["A"], True, "Nowa")
    i = ops.index_of(with_child, new_id)
    assert with_child[i].level == 2 and with_child[i + 2].plain_text() == "B"
    sibling, sid = ops.add_section(blocks, ids["A"], False)
    assert sibling[ops.index_of(sibling, sid)].level == 1


def test_remove_table_removes_caption_and_section_removal():
    table = Block.new_table(1, 1)
    blocks = (Block.paragraph("p"), table, Block.new_caption(table.id))
    assert len(ops.remove_block(blocks, table.id)) == 1
    sections, ids = doc_with_sections()
    remaining = ops.remove_section(sections, ids["A"])
    assert titles(remaining)[0] == ("B", 1)


def test_list_and_caption_numbering():
    from dataclasses import replace
    numbered = [replace(Block.paragraph(str(i)), para=replace(Block.paragraph().para, list="number")) for i in range(3)]
    blocks = (numbered[0], numbered[1], Block.paragraph("break"), numbered[2])
    assert ops.list_numbers(blocks) == [1, 2, 0, 1]
    t1, t2, img = Block.new_table(1, 1), Block.new_table(1, 1), Block.new_image("a.png")
    c1, c2, c3 = Block.new_caption(t1.id), Block.new_caption(img.id), Block.new_caption(t2.id)
    info = ops.caption_info((t1, c1, img, c2, t2, c3))
    assert info[c1.id] == ("Tabela", 1) and info[c3.id] == ("Tabela", 2) and info[c2.id] == ("Rysunek", 1)


def test_normalize_document_repairs_ids_and_detached_captions():
    table = Block.new_table(1, 1)
    caption = Block.new_caption(table.id, "c")
    orphan = Block.new_caption("missing", "sierota")
    dup = Block.paragraph("dup")
    warnings = []
    fixed = ops.normalize_document((caption, dup, dup, table, orphan), warnings)
    ids = [b.id for b in fixed]
    assert len(set(ids)) == len(ids)
    assert fixed[ops.index_of(fixed, table.id) + 1].id == caption.id  # podpis wrócił pod tabelę
    assert any(b.type == "paragraph" and b.plain_text() == "sierota" for b in fixed)
    assert warnings
