"""Czyste operacje na krotce bloków.

Sekcja = blok nagłówka + wszystkie kolejne bloki aż do następnego nagłówka
o poziomie mniejszym lub równym. Relacje rodzic–dziecko wynikają z poziomów
(``outline`` buduje z nich jawne drzewo). Wszystkie funkcje zwracają nową
krotkę bloków albo ``None``, gdy operacja niczego nie zmienia; niedozwolone
operacje zgłaszają ``OperationError`` z komunikatem dla użytkownika.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from .blocks import (CAPTION, HEADING, IMAGE, MAX_HEADING_LEVEL, PARAGRAPH, TABLE, Block,
                     plain_runs)

DROP_BEFORE = "before"
DROP_AFTER = "after"
DROP_INTO = "into"

CAPTION_LABELS = {TABLE: "Tabela", IMAGE: "Rysunek"}


class OperationError(Exception):
    """Operacja niedozwolona; komunikat jest przeznaczony dla użytkownika."""


@dataclass(frozen=True)
class OutlineEntry:
    id: str
    title: str
    level: int
    depth: int
    parent_id: str
    index: int          # indeks bloku nagłówka
    end: int            # indeks za ostatnim blokiem sekcji
    has_children: bool
    number: str         # numeracja w drzewie, np. "2.1.3"


# ---------------------------------------------------------------------------
# Pomocnicze
# ---------------------------------------------------------------------------

def index_of(blocks: tuple, block_id: str) -> int:
    for i, block in enumerate(blocks):
        if block.id == block_id:
            return i
    return -1


def require_index(blocks: tuple, block_id: str) -> int:
    i = index_of(blocks, block_id)
    if i < 0:
        raise OperationError("Element nie istnieje w dokumencie.")
    return i


def section_end(blocks: tuple, heading_index: int) -> int:
    level = blocks[heading_index].level
    j = heading_index + 1
    while j < len(blocks):
        b = blocks[j]
        if b.type == HEADING and b.level <= level:
            break
        j += 1
    return j


def caption_index_for(blocks: tuple, target_index: int) -> int:
    nxt = target_index + 1
    if nxt < len(blocks) and blocks[nxt].type == CAPTION \
            and blocks[nxt].caption.target_id == blocks[target_index].id:
        return nxt
    return -1


def movable_unit(blocks: tuple, index: int, whole_section: bool = True) -> tuple[int, int]:
    """Zakres (start, liczba) przenoszony razem z blokiem.

    Nagłówek przenosi całą sekcję, tabela/obraz – razem z podpisem, a podpis –
    razem ze swoim elementem.
    """
    block = blocks[index]
    if block.type == HEADING and whole_section:
        return index, section_end(blocks, index) - index
    if block.type == CAPTION:
        target = index_of(blocks, block.caption.target_id)
        if target == index - 1:
            return target, 2
        return index, 1
    if block.is_captionable and caption_index_for(blocks, index) >= 0:
        return index, 2
    return index, 1


def adjust_drop_index(blocks: tuple, dest: int) -> int:
    """Nie pozwala wstawić niczego między element a jego podpis."""
    dest = max(0, min(len(blocks), dest))
    if 0 < dest < len(blocks):
        b = blocks[dest]
        if b.type == CAPTION and b.caption.target_id == blocks[dest - 1].id:
            dest += 1
    return dest


def move_range(blocks: tuple, start: int, count: int, dest: int) -> tuple | None:
    if start <= dest <= start + count:
        return None
    segment = blocks[start:start + count]
    rest = blocks[:start] + blocks[start + count:]
    if dest > start:
        dest -= count
    return rest[:dest] + segment + rest[dest:]


def ensure_not_empty(blocks: tuple) -> tuple:
    return blocks if blocks else (Block.paragraph(),)


# ---------------------------------------------------------------------------
# Struktura: spis sekcji, numeracja
# ---------------------------------------------------------------------------

def outline(blocks: tuple) -> list[OutlineEntry]:
    raw: list[dict] = []
    stack: list[int] = []
    child_counter: dict[str, int] = {}
    for i, block in enumerate(blocks):
        if block.type != HEADING:
            continue
        while stack and raw[stack[-1]]["level"] >= block.level:
            stack.pop()
        parent = raw[stack[-1]] if stack else None
        parent_id = parent["id"] if parent else ""
        k = child_counter.get(parent_id, 0) + 1
        child_counter[parent_id] = k
        if parent:
            parent["has_children"] = True
        raw.append({
            "id": block.id,
            "title": block.plain_text().replace("\n", " "),
            "level": block.level,
            "depth": parent["depth"] + 1 if parent else 0,
            "parent_id": parent_id,
            "index": i,
            "end": section_end(blocks, i),
            "has_children": False,
            "number": f"{parent['number']}.{k}" if parent else str(k),
        })
        stack.append(len(raw) - 1)
    return [OutlineEntry(**e) for e in raw]


def section_of_block(blocks: tuple, index: int) -> str:
    """Identyfikator najbliższego nagłówka obejmującego blok (lub sam nagłówek)."""
    for i in range(min(index, len(blocks) - 1), -1, -1):
        if blocks[i].type == HEADING:
            return blocks[i].id
    return ""


def list_numbers(blocks: tuple) -> list[int]:
    numbers: list[int] = []
    counters: dict[int, int] = {}
    for block in blocks:
        if block.type == PARAGRAPH and block.para.list != "none":
            indent = block.para.indent
            for deeper in [k for k in counters if k > indent]:
                del counters[deeper]
            if block.para.list == "number":
                counters[indent] = counters.get(indent, 0) + 1
                numbers.append(counters[indent])
            else:
                counters.pop(indent, None)
                numbers.append(0)
        else:
            counters.clear()
            numbers.append(0)
    return numbers


def caption_info(blocks: tuple) -> dict[str, tuple[str, int]]:
    """Mapuje identyfikatory podpisów i ich elementów na (etykieta, numer)."""
    captions: dict[str, str] = {}
    for block in blocks:
        if block.type == CAPTION and block.caption.target_id not in captions:
            captions[block.caption.target_id] = block.id
    counters: dict[str, int] = {}
    info: dict[str, tuple[str, int]] = {}
    for block in blocks:
        if block.is_captionable and block.id in captions:
            label = CAPTION_LABELS[block.type]
            counters[label] = counters.get(label, 0) + 1
            info[block.id] = (label, counters[label])
            info[captions[block.id]] = (label, counters[label])
    return info


def caption_of(blocks: tuple, target_id: str) -> str:
    for block in blocks:
        if block.type == CAPTION and block.caption.target_id == target_id:
            return block.id
    return ""


# ---------------------------------------------------------------------------
# Przenoszenie bloków i sekcji
# ---------------------------------------------------------------------------

def plan_block_move(blocks: tuple, block_id: str, dest: int,
                    whole_section: bool = True) -> tuple[int, int, int] | None:
    """Zwraca (start, liczba, cel) albo None dla operacji pustej."""
    i = require_index(blocks, block_id)
    start, count = movable_unit(blocks, i, whole_section)
    dest = adjust_drop_index(blocks, dest)
    if start < dest < start + count:
        if blocks[start].type == HEADING and count > 1:
            raise OperationError("Nie można upuścić sekcji wewnątrz niej samej.")
        return None
    if dest in (start, start + count):
        return None
    return start, count, dest


def move_block(blocks: tuple, block_id: str, dest: int, whole_section: bool = True) -> tuple | None:
    plan = plan_block_move(blocks, block_id, dest, whole_section)
    if plan is None:
        return None
    return move_range(blocks, *plan)


def move_section(blocks: tuple, section_id: str, target_id: str, mode: str) -> tuple | None:
    s = require_index(blocks, section_id)
    t = require_index(blocks, target_id)
    if blocks[s].type != HEADING or blocks[t].type != HEADING:
        raise OperationError("Przenosić można tylko sekcje (nagłówki).")
    if s == t:
        return None
    e = section_end(blocks, s)
    if s <= t < e:
        raise OperationError("Nie można przenieść sekcji do jej własnej podsekcji.")
    target_level = blocks[t].level
    if mode == DROP_BEFORE:
        new_level, dest = target_level, t
    elif mode == DROP_AFTER:
        new_level, dest = target_level, section_end(blocks, t)
    elif mode == DROP_INTO:
        new_level, dest = target_level + 1, section_end(blocks, t)
    else:
        raise OperationError(f"Nieznany tryb upuszczenia: {mode}")
    delta = new_level - blocks[s].level
    segment = list(blocks[s:e])
    for b in segment:
        if b.type == HEADING and not 1 <= b.level + delta <= MAX_HEADING_LEVEL:
            raise OperationError(
                f"Przekroczono maksymalny poziom zagnieżdżenia ({MAX_HEADING_LEVEL}).")
    if delta:
        segment = [replace(b, level=b.level + delta) if b.type == HEADING else b for b in segment]
    rest = blocks[:s] + blocks[e:]
    if dest > s:
        dest -= e - s
    result = rest[:dest] + tuple(segment) + rest[dest:]
    if [(b.id, b.level) for b in result] == [(b.id, b.level) for b in blocks]:
        return None
    return result


def change_section_level(blocks: tuple, section_id: str, delta: int) -> tuple | None:
    s = require_index(blocks, section_id)
    if blocks[s].type != HEADING:
        raise OperationError("Poziom można zmienić tylko dla sekcji.")
    if delta == 0:
        return None
    e = section_end(blocks, s)
    for b in blocks[s:e]:
        if b.type == HEADING and not 1 <= b.level + delta <= MAX_HEADING_LEVEL:
            if delta < 0:
                raise OperationError("Sekcja ma już najwyższy poziom.")
            raise OperationError(
                f"Przekroczono maksymalny poziom zagnieżdżenia ({MAX_HEADING_LEVEL}).")
    changed = tuple(replace(b, level=b.level + delta) if b.type == HEADING else b
                    for b in blocks[s:e])
    return blocks[:s] + changed + blocks[e:]


def move_section_sibling(blocks: tuple, section_id: str, direction: int) -> tuple | None:
    """Zamienia sekcję miejscami z poprzednim (-1) lub następnym (+1) rodzeństwem."""
    entries = outline(blocks)
    pos = next((k for k, e in enumerate(entries) if e.id == section_id), -1)
    if pos < 0:
        raise OperationError("Sekcja nie istnieje.")
    me = entries[pos]
    siblings = [e for e in entries if e.parent_id == me.parent_id]
    k = siblings.index(me)
    if direction < 0:
        if k == 0:
            return None
        return move_section_to(blocks, me, siblings[k - 1].index)
    if k == len(siblings) - 1:
        return None
    return move_section_to(blocks, me, siblings[k + 1].end)


def move_section_to(blocks: tuple, entry: OutlineEntry, dest: int) -> tuple | None:
    return move_range(blocks, entry.index, entry.end - entry.index, dest)


# ---------------------------------------------------------------------------
# Wstawianie i usuwanie
# ---------------------------------------------------------------------------

def insert_blocks(blocks: tuple, index: int, new_blocks: tuple | list) -> tuple:
    index = adjust_drop_index(blocks, index)
    return blocks[:index] + tuple(new_blocks) + blocks[index:]


def remove_block(blocks: tuple, block_id: str) -> tuple:
    """Usuwa blok; tabela/obraz znikają razem ze swoimi podpisami."""
    i = require_index(blocks, block_id)
    block = blocks[i]
    doomed = {block.id}
    if block.is_captionable:
        doomed |= {b.id for b in blocks if b.type == CAPTION and b.caption.target_id == block.id}
    return ensure_not_empty(tuple(b for b in blocks if b.id not in doomed))


def remove_section(blocks: tuple, section_id: str) -> tuple:
    s = require_index(blocks, section_id)
    if blocks[s].type != HEADING:
        raise OperationError("To nie jest sekcja.")
    e = section_end(blocks, s)
    return ensure_not_empty(blocks[:s] + blocks[e:])


def add_section(blocks: tuple, ref_id: str, as_child: bool,
                title: str = "") -> tuple[tuple, str]:
    """Dodaje sekcję (nagłówek + pusty akapit) za sekcją ref_id lub jako jej ostatnią podsekcję."""
    if ref_id:
        r = require_index(blocks, ref_id)
        ref = blocks[r]
        if ref.type != HEADING:
            raise OperationError("Sekcję można dodać tylko względem innej sekcji.")
        level = ref.level + 1 if as_child else ref.level
        if level > MAX_HEADING_LEVEL:
            raise OperationError(
                f"Przekroczono maksymalny poziom zagnieżdżenia ({MAX_HEADING_LEVEL}).")
        dest = section_end(blocks, r)
    else:
        level = 1
        dest = len(blocks)
    if not title:
        title = "Nowa podsekcja" if as_child else "Nowa sekcja"
    heading = Block.heading(level, title)
    body = Block.paragraph()
    # Nowy, pusty dokument: zastępujemy jedyny pusty akapit.
    if len(blocks) == 1 and blocks[0].type == PARAGRAPH and not blocks[0].runs and not ref_id:
        return (heading, body), heading.id
    return blocks[:dest] + (heading, body) + blocks[dest:], heading.id


def normalize_document(blocks: tuple, warnings: list | None = None) -> tuple:
    """Naprawa danych po wczytaniu: unikalne id, poprawne powiązania podpisów."""
    seen: set[str] = set()
    fixed: list[Block] = []
    for block in blocks:
        if not block.id or block.id in seen:
            from .blocks import generate_id
            block = replace(block, id=generate_id())
            if warnings is not None:
                warnings.append("Uzupełniono brakujący lub powtórzony identyfikator bloku.")
        seen.add(block.id)
        fixed.append(block)

    by_id = {b.id: b for b in fixed}
    used_targets: set[str] = set()
    captions: dict[str, Block] = {}
    result: list[Block] = []
    for block in fixed:
        if block.type == CAPTION:
            target = by_id.get(block.caption.target_id)
            if target is None or not target.is_captionable or block.caption.target_id in used_targets:
                if warnings is not None:
                    warnings.append("Podpis bez poprawnego elementu zamieniono na zwykły akapit.")
                result.append(Block.paragraph(runs=plain_runs(block.caption.text)) if block.caption.text
                              else replace(Block.paragraph(), id=block.id))
                continue
            used_targets.add(block.caption.target_id)
            captions[block.caption.target_id] = block
            continue
        result.append(block)
    # Podpis ląduje zawsze bezpośrednio pod swoim elementem.
    out: list[Block] = []
    for block in result:
        out.append(block)
        if block.id in captions:
            out.append(captions[block.id])
    return ensure_not_empty(tuple(out))
