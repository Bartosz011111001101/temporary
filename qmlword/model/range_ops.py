"""Operacje na zaznaczeniu obejmującym wiele bloków i na wklejanych fragmentach.

Zaznaczenie to para punktów (blok, pozycja) – kotwica i fokus, w dowolnej kolejności.
Bloki tekstowe (akapit, nagłówek) mogą być zaznaczone częściowo; pozostałe bloki
(tabela, obraz, podział strony…) zawsze w całości. Podpis traktujemy jak tekst.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from . import text_ops
from .blocks import (CAPTION, PARAGRAPH, PLACEHOLDER, TABLE, Block, TableCell, TableData, TextRun,
                     generate_id, normalize_runs, plain_runs, plain_text)
from .ops import OperationError, caption_index_for, ensure_not_empty, index_of


@dataclass(frozen=True)
class Span:
    start_index: int
    start_pos: int
    end_index: int
    end_pos: int

    @property
    def single(self) -> bool:
        return self.start_index == self.end_index


def block_length(block: Block) -> int:
    if block.is_text:
        return text_ops.runs_length(block.runs)
    if block.type == CAPTION:
        return len(block.caption.text)
    return 0


def normalize_span(blocks: tuple, a_id: str, a_pos: int, f_id: str, f_pos: int) -> Span:
    a, f = index_of(blocks, a_id), index_of(blocks, f_id)
    if a < 0 or f < 0:
        raise OperationError("Zaznaczenie nie pasuje już do dokumentu.")
    a_pos = max(0, min(a_pos, block_length(blocks[a])))
    f_pos = max(0, min(f_pos, block_length(blocks[f])))
    if (a, a_pos) <= (f, f_pos):
        return Span(a, a_pos, f, f_pos)
    return Span(f, f_pos, a, a_pos)


def _bounds(span: Span, index: int, block: Block) -> tuple[int, int]:
    start = span.start_pos if index == span.start_index else 0
    end = span.end_pos if index == span.end_index else block_length(block)
    return start, end


def range_plain_text(blocks: tuple, span: Span) -> str:
    lines = []
    for i in range(span.start_index, span.end_index + 1):
        b = blocks[i]
        s, e = _bounds(span, i, b)
        if b.is_text:
            lines.append(plain_text(b.runs)[s:e])
        elif b.type == CAPTION:
            lines.append(b.caption.text[s:e])
        elif b.type == TABLE:
            for row in b.table.cells:
                lines.append("\t".join(plain_text(c.runs) for c in row))
    return "\n".join(lines)


def extract_range(blocks: tuple, span: Span) -> tuple:
    """Kopia zaznaczonego fragmentu jako nowe bloki (z nowymi identyfikatorami)."""
    out: list[Block] = []
    id_map: dict[str, str] = {}
    for i in range(span.start_index, span.end_index + 1):
        b = blocks[i]
        s, e = _bounds(span, i, b)
        new_id = generate_id()
        id_map[b.id] = new_id
        if b.is_text:
            out.append(replace(b, id=new_id, runs=text_ops.slice_runs(b.runs, s, e)))
        elif b.type == CAPTION:
            out.append(replace(b, id=new_id, caption=replace(b.caption, text=b.caption.text[s:e])))
        elif b.type == PLACEHOLDER:
            continue
        else:
            out.append(replace(b, id=new_id))
    fixed: list[Block] = []
    for b in out:
        if b.type == CAPTION:
            target = id_map.get(b.caption.target_id)
            if target and any(x.id == target for x in out):
                b = replace(b, caption=replace(b.caption, target_id=target))
            else:
                b = Block.paragraph(b.caption.text)
        fixed.append(b)
    return tuple(fixed)


def delete_range(blocks: tuple, span: Span) -> tuple[tuple, str, int]:
    """Usuwa zaznaczenie. Zwraca (bloki, id bloku z kursorem, pozycja kursora)."""
    si, ei = span.start_index, span.end_index
    first, last = blocks[si], blocks[ei]
    first_text = first.is_text or first.type == CAPTION and si > 0 and caption_index_for(blocks, si - 1) == si
    last_text = last.is_text

    def keep_left(b: Block) -> Block:
        if b.type == CAPTION:
            return replace(b, caption=replace(b.caption, text=b.caption.text[:span.start_pos]))
        return replace(b, runs=text_ops.split_runs(b.runs, span.start_pos)[0])

    if span.single:
        if first.is_text:
            left, rest = text_ops.split_runs(first.runs, span.start_pos)
            _, right = text_ops.split_runs(rest, span.end_pos - span.start_pos)
            merged = replace(first, runs=normalize_runs((*left, *right)))
            return blocks[:si] + (merged,) + blocks[si + 1:], first.id, span.start_pos
        if first.type == CAPTION:
            text = first.caption.text
            merged = replace(first, caption=replace(first.caption, text=text[:span.start_pos] + text[span.end_pos:]))
            return blocks[:si] + (merged,) + blocks[si + 1:], first.id, span.start_pos

    after = ei + 1
    # Podpis tuż za usuwanym elementem znika razem z nim.
    if not last_text and caption_index_for(blocks, ei) == after:
        after += 1
    head = blocks[:si]
    tail = blocks[after:]
    if first_text and last_text:
        left = keep_left(first)
        right = text_ops.split_runs(last.runs, span.end_pos)[1]
        if left.type == CAPTION:
            return ensure_not_empty(head + (left, replace(last, runs=right)) + tail), left.id, span.start_pos
        merged = replace(left, runs=normalize_runs((*left.runs, *right)))
        return ensure_not_empty(head + (merged,) + tail), merged.id, span.start_pos
    if first_text:
        left = keep_left(first)
        return ensure_not_empty(head + (left,) + tail), left.id, span.start_pos
    if last_text:
        right = replace(last, runs=text_ops.split_runs(last.runs, span.end_pos)[1])
        return ensure_not_empty(head + (right,) + tail), right.id, 0
    result = ensure_not_empty(head + tail)
    focus = result[min(si, len(result) - 1)]
    return result, focus.id, 0


def map_text_blocks(blocks: tuple, span: Span, fn: Callable[[Block, int, int], Block]) -> tuple:
    out = list(blocks)
    for i in range(span.start_index, span.end_index + 1):
        b = blocks[i]
        if b.is_text:
            s, e = _bounds(span, i, b)
            out[i] = fn(b, s, e)
    return tuple(out)


def format_range(blocks: tuple, span: Span, props: dict) -> tuple:
    return map_text_blocks(blocks, span, lambda b, s, e: replace(b, runs=text_ops.apply_props(b.runs, s, e, props)))


def case_range(blocks: tuple, span: Span, mode: str) -> tuple:
    return map_text_blocks(blocks, span, lambda b, s, e: replace(b, runs=text_ops.change_case(b.runs, s, e, mode)))


def text_blocks_in_span(blocks: tuple, span: Span) -> list[int]:
    return [i for i in range(span.start_index, span.end_index + 1) if blocks[i].is_text]


# ---------------------------------------------------------------------------
# Wklejanie fragmentu
# ---------------------------------------------------------------------------

def insert_fragment(blocks: tuple, block_id: str, start: int, end: int,
                    fragment: tuple) -> tuple[tuple, str, int]:
    """Wkleja bloki w miejsce zaznaczenia [start, end) w bloku tekstowym (jak w edytorach tekstu):
    pierwszy wklejony akapit łączy się z tekstem przed kursorem, ostatni – z tekstem za kursorem."""
    i = index_of(blocks, block_id)
    if i < 0:
        raise OperationError("Nie znaleziono miejsca wklejenia.")
    target = blocks[i]
    if target.type == PLACEHOLDER:
        target = replace(Block.paragraph(), id=target.id)
    if not target.is_text:
        raise OperationError("Wklejać można w tekście akapitu.")
    fragment = tuple(b for b in fragment if b.type != PLACEHOLDER)
    if not fragment:
        return blocks, target.id, start
    left, rest = text_ops.split_runs(target.runs, start)
    _, right = text_ops.split_runs(rest, max(0, end - start))

    if len(fragment) == 1 and fragment[0].is_text:
        pasted = fragment[0].runs
        merged = replace(target, runs=normalize_runs((*left, *pasted, *right)))
        return blocks[:i] + (merged,) + blocks[i + 1:], target.id, text_ops.runs_length(left) + text_ops.runs_length(pasted)

    new_blocks: list[Block] = []
    rest_fragment = list(fragment)
    head = rest_fragment[0]
    if head.is_text:
        if not left:
            # Wklejanie na początku akapitu – akapit przejmuje styl pierwszego wklejonego.
            new_blocks.append(replace(head, id=target.id))
        else:
            new_blocks.append(replace(target, runs=normalize_runs((*left, *head.runs))))
        rest_fragment.pop(0)
    elif left:
        new_blocks.append(replace(target, runs=left))
    tail = rest_fragment[-1] if rest_fragment else None
    if tail is not None and tail.is_text:
        rest_fragment.pop()
        new_blocks.extend(rest_fragment)
        last = replace(tail, runs=normalize_runs((*tail.runs, *right)))
        new_blocks.append(last)
        focus_id, focus_pos = last.id, text_ops.runs_length(tail.runs)
    else:
        new_blocks.extend(rest_fragment)
        # Tekst za kursorem trafia do akapitu pod wklejonymi elementami (tam też ląduje kursor).
        if target.type == PARAGRAPH:
            body = replace(target, id=generate_id(), runs=right)
        else:
            body = Block.paragraph(runs=right)
        new_blocks.append(body)
        focus_id, focus_pos = body.id, 0
    return blocks[:i] + tuple(new_blocks) + blocks[i + 1:], focus_id, focus_pos


def fresh_ids(fragment: tuple) -> tuple:
    """Nowe identyfikatory dla wklejanych bloków (z zachowaniem powiązań podpisów)."""
    id_map = {b.id: generate_id() for b in fragment}
    out = []
    for b in fragment:
        b = replace(b, id=id_map[b.id])
        if b.type == CAPTION:
            target = id_map.get(b.caption.target_id)
            b = replace(b, caption=replace(b.caption, target_id=target)) if target else Block.paragraph(b.caption.text)
        out.append(b)
    return tuple(out)


# ---------------------------------------------------------------------------
# Konwersja tekst ↔ tabela
# ---------------------------------------------------------------------------

def _split_runs_by(runs: tuple, separator: str) -> list[tuple]:
    text = plain_text(runs)
    parts: list[tuple] = []
    start = 0
    while True:
        pos = text.find(separator, start)
        if pos < 0:
            parts.append(text_ops.slice_runs(runs, start, len(text)))
            return parts
        parts.append(text_ops.slice_runs(runs, start, pos))
        start = pos + len(separator)


def text_to_table(blocks: tuple, first_index: int, last_index: int, separator: str) -> tuple[tuple, str]:
    if not separator:
        raise OperationError("Podaj separator kolumn.")
    rows: list[list[tuple]] = []
    for i in range(first_index, last_index + 1):
        b = blocks[i]
        if not b.is_text:
            raise OperationError("Na tabelę można zamienić tylko akapity tekstu.")
        rows.append(_split_runs_by(b.runs, separator))
    if not rows:
        raise OperationError("Zaznacz akapity do zamiany na tabelę.")
    cols = min(50, max(len(r) for r in rows))
    cells = tuple(tuple(TableCell(runs=normalize_runs(row[c])) if c < len(row) else TableCell()
                        for c in range(cols)) for row in rows[:500])
    table = Block(id=generate_id(), type=TABLE,
                  table=TableData(cells=cells, header_row=len(rows) > 1).normalized())
    return blocks[:first_index] + (table,) + blocks[last_index + 1:], table.id


def table_to_text(blocks: tuple, table_id: str, separator: str) -> tuple[tuple, str]:
    i = index_of(blocks, table_id)
    if i < 0 or blocks[i].type != TABLE:
        raise OperationError("To nie jest tabela.")
    table = blocks[i].table
    cov = table.coverage()
    paragraphs = []
    for r, row in enumerate(table.cells):
        runs: list[TextRun] = []
        for c, cell in enumerate(row):
            if c:
                runs.append(TextRun(text=separator))
            if cov[r][c] == (r, c):
                runs.extend(replace(t, text=t.text.replace("\n", " ")) for t in cell.runs)
        paragraphs.append(Block.paragraph(runs=normalize_runs(runs)))
    after = i + 1
    caption = caption_index_for(blocks, i)
    if caption >= 0:
        paragraphs.append(Block.paragraph(blocks[caption].caption.text))
        after = caption + 1
    return blocks[:i] + tuple(paragraphs) + blocks[after:], paragraphs[0].id
