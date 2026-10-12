"""Operacje na tabelach. Każda funkcja zwraca nową, znormalizowaną TableData."""
from __future__ import annotations

from dataclasses import replace

from .blocks import ALIGNMENTS, TableCell, TableData, TextRun, normalize_runs, sanitize_color
from .ops import OperationError

MAX_ROWS = 500
MAX_COLS = 50


def _grid(table: TableData) -> list[list[TableCell]]:
    return [list(row) for row in table.cells]


def _build(table: TableData, grid: list[list[TableCell]], **changes) -> TableData:
    return replace(table, cells=tuple(tuple(r) for r in grid), **changes).normalized()


def insert_row(table: TableData, at: int) -> TableData:
    if table.rows >= MAX_ROWS:
        raise OperationError(f"Tabela może mieć najwyżej {MAX_ROWS} wierszy.")
    at = max(0, min(table.rows, at))
    grid = _grid(table)
    # Scalenia przecinające nowy wiersz zostają rozciągnięte.
    for r in range(table.rows):
        for c in range(table.cols):
            cell = grid[r][c]
            if cell.row_span > 1 and r < at < r + cell.row_span:
                grid[r][c] = replace(cell, row_span=cell.row_span + 1)
    new_row = [TableCell(align=grid[min(at, table.rows - 1)][c].align) for c in range(table.cols)]
    grid.insert(at, new_row)
    heights = list(table.row_heights)
    heights.insert(at, 0.0)
    return _build(table, grid, row_heights=tuple(heights))


def remove_row(table: TableData, row: int) -> TableData:
    if table.rows <= 1:
        raise OperationError("Tabela musi mieć co najmniej jeden wiersz. Usuń całą tabelę.")
    if not 0 <= row < table.rows:
        raise OperationError("Nieprawidłowy wiersz.")
    grid = _grid(table)
    for r in range(table.rows):
        for c in range(table.cols):
            cell = grid[r][c]
            if cell.row_span <= 1:
                continue
            if r < row < r + cell.row_span:
                grid[r][c] = replace(cell, row_span=cell.row_span - 1)
            elif r == row:
                # Kotwica przechodzi do następnego wiersza razem z treścią.
                grid[r + 1][c] = replace(cell, row_span=cell.row_span - 1)
    del grid[row]
    heights = list(table.row_heights)
    del heights[row]
    return _build(table, grid, row_heights=tuple(heights))


def insert_column(table: TableData, at: int) -> TableData:
    if table.cols >= MAX_COLS:
        raise OperationError(f"Tabela może mieć najwyżej {MAX_COLS} kolumn.")
    at = max(0, min(table.cols, at))
    grid = _grid(table)
    for r in range(table.rows):
        for c in range(table.cols):
            cell = grid[r][c]
            if cell.col_span > 1 and c < at < c + cell.col_span:
                grid[r][c] = replace(cell, col_span=cell.col_span + 1)
    for row in grid:
        row.insert(at, TableCell())
    widths = list(table.col_widths)
    new_width = 1.0 / (table.cols + 1)
    widths = [w * (1 - new_width) for w in widths]
    widths.insert(at, new_width)
    return _build(table, grid, col_widths=tuple(widths))


def remove_column(table: TableData, col: int) -> TableData:
    if table.cols <= 1:
        raise OperationError("Tabela musi mieć co najmniej jedną kolumnę. Usuń całą tabelę.")
    if not 0 <= col < table.cols:
        raise OperationError("Nieprawidłowa kolumna.")
    grid = _grid(table)
    for r in range(table.rows):
        for c in range(table.cols):
            cell = grid[r][c]
            if cell.col_span <= 1:
                continue
            if c < col < c + cell.col_span:
                grid[r][c] = replace(cell, col_span=cell.col_span - 1)
            elif c == col:
                grid[r][c + 1] = replace(cell, col_span=cell.col_span - 1)
    for row in grid:
        del row[col]
    widths = list(table.col_widths)
    del widths[col]
    return _build(table, grid, col_widths=tuple(widths))


def _expand_rect(table: TableData, r1: int, c1: int, r2: int, c2: int) -> tuple[int, int, int, int]:
    """Rozszerza prostokąt tak, by nie przecinał częściowo istniejących scaleń."""
    cov = table.coverage()
    changed = True
    while changed:
        changed = False
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                ar, ac = cov[r][c]
                anchor = table.cells[ar][ac]
                er, ec = ar + anchor.row_span - 1, ac + anchor.col_span - 1
                if ar < r1 or ac < c1 or er > r2 or ec > c2:
                    r1, c1, r2, c2 = min(r1, ar), min(c1, ac), max(r2, er), max(c2, ec)
                    changed = True
    return r1, c1, r2, c2


def merge_cells(table: TableData, r1: int, c1: int, r2: int, c2: int) -> TableData:
    r1, r2 = sorted((r1, r2))
    c1, c2 = sorted((c1, c2))
    if not (0 <= r1 and r2 < table.rows and 0 <= c1 and c2 < table.cols):
        raise OperationError("Zaznaczenie wykracza poza tabelę.")
    r1, c1, r2, c2 = _expand_rect(table, r1, c1, r2, c2)
    if r1 == r2 and c1 == c2:
        raise OperationError("Zaznacz co najmniej dwie komórki (Shift+klik), aby je scalić.")
    grid = _grid(table)
    cov = table.coverage()
    texts: list[tuple] = []
    for r in range(r1, r2 + 1):
        for c in range(c1, c2 + 1):
            if cov[r][c] == (r, c) and grid[r][c].runs:
                texts.append(grid[r][c].runs)
    merged_runs: list[TextRun] = []
    for k, runs in enumerate(texts):
        if k:
            merged_runs.append(TextRun(text="\n"))
        merged_runs.extend(runs)
    anchor = grid[r1][c1]
    for r in range(r1, r2 + 1):
        for c in range(c1, c2 + 1):
            grid[r][c] = TableCell(align=anchor.align)
    grid[r1][c1] = replace(anchor, runs=normalize_runs(merged_runs),
                           row_span=r2 - r1 + 1, col_span=c2 - c1 + 1)
    return _build(table, grid)


def split_cell(table: TableData, row: int, col: int) -> TableData:
    ar, ac = table.anchor_of(row, col)
    cell = table.cells[ar][ac]
    if cell.row_span == 1 and cell.col_span == 1:
        raise OperationError("Ta komórka nie jest scalona.")
    grid = _grid(table)
    grid[ar][ac] = replace(cell, row_span=1, col_span=1)
    return _build(table, grid)


def set_cell_runs(table: TableData, row: int, col: int, runs: tuple) -> TableData:
    ar, ac = table.anchor_of(row, col)
    grid = _grid(table)
    if grid[ar][ac].formula:
        return table  # komórka z formułą pokazuje wynik – treść zmienia się przez formułę
    grid[ar][ac] = replace(grid[ar][ac], runs=normalize_runs(runs))
    return recompute_formulas(_build(table, grid))


def _cells_in_rect(table: TableData, r1: int, c1: int, r2: int, c2: int):
    r1, r2 = sorted((max(0, r1), min(table.rows - 1, r2)))
    c1, c2 = sorted((max(0, c1), min(table.cols - 1, c2)))
    seen = set()
    for r in range(r1, r2 + 1):
        for c in range(c1, c2 + 1):
            anchor = table.anchor_of(r, c)
            if anchor not in seen:
                seen.add(anchor)
                yield anchor


def set_cells_align(table: TableData, r1: int, c1: int, r2: int, c2: int, align: str) -> TableData:
    if align not in ALIGNMENTS:
        raise OperationError("Nieznane wyrównanie.")
    grid = _grid(table)
    for r, c in _cells_in_rect(table, r1, c1, r2, c2):
        grid[r][c] = replace(grid[r][c], align=align)
    return _build(table, grid)


def set_cells_background(table: TableData, r1: int, c1: int, r2: int, c2: int, color: str) -> TableData:
    color = sanitize_color(color) if color else ""
    grid = _grid(table)
    for r, c in _cells_in_rect(table, r1, c1, r2, c2):
        grid[r][c] = replace(grid[r][c], background=color)
    return _build(table, grid)


def set_column_widths(table: TableData, widths: list[float]) -> TableData:
    if len(widths) != table.cols:
        raise OperationError("Liczba szerokości nie zgadza się z liczbą kolumn.")
    return replace(table, col_widths=tuple(float(w) for w in widths)).normalized()


def set_row_height(table: TableData, row: int, height: float) -> TableData:
    if not 0 <= row < table.rows:
        raise OperationError("Nieprawidłowy wiersz.")
    heights = list(table.row_heights)
    heights[row] = max(0.0, float(height))
    return replace(table, row_heights=tuple(heights)).normalized()


# ---------------------------------------------------------------------------
# Krawędzie wybranych komórek
# ---------------------------------------------------------------------------

BORDER_PRESETS = ("all", "none", "outside", "inside", "top", "bottom", "left", "right", "thickOutside", "reset")


def set_cells_borders(table: TableData, r1: int, c1: int, r2: int, c2: int, preset: str) -> TableData:
    """Krawędzie zakresu komórek, np. „all”, „outside”, „bottom”; „reset” wraca do stylu tabeli."""
    if preset not in BORDER_PRESETS:
        raise OperationError("Nieznany rodzaj obramowania.")
    r1, r2 = sorted((max(0, r1), min(table.rows - 1, r2)))
    c1, c2 = sorted((max(0, c1), min(table.cols - 1, c2)))
    grid = _grid(table)
    cov = table.coverage()
    done = set()
    for r in range(r1, r2 + 1):
        for c in range(c1, c2 + 1):
            ar, ac = cov[r][c]
            if (ar, ac) in done:
                continue
            done.add((ar, ac))
            cell = grid[ar][ac]
            last_r, last_c = ar + cell.row_span - 1, ac + cell.col_span - 1
            on_top, on_bottom = ar <= r1, last_r >= r2
            on_left, on_right = ac <= c1, last_c >= c2
            sides = {"top": cell.border_top, "bottom": cell.border_bottom,
                     "left": cell.border_left, "right": cell.border_right}
            outer = {"top": on_top, "bottom": on_bottom, "left": on_left, "right": on_right}
            for side in sides:
                if preset == "all":
                    sides[side] = "thin"
                elif preset == "none":
                    sides[side] = "none"
                elif preset == "reset":
                    sides[side] = ""
                elif preset in ("outside", "thickOutside") and outer[side]:
                    sides[side] = "thin" if preset == "outside" else "thick"
                elif preset == "inside" and not outer[side]:
                    sides[side] = "thin"
                elif preset == side and outer[side]:
                    sides[side] = "thin"
            grid[ar][ac] = replace(cell, border_top=sides["top"], border_bottom=sides["bottom"],
                                   border_left=sides["left"], border_right=sides["right"])
    return _build(table, grid)


# ---------------------------------------------------------------------------
# Sortowanie wierszy
# ---------------------------------------------------------------------------

def sort_rows(table: TableData, col: int, descending: bool = False) -> TableData:
    from .formulas import parse_number
    from .blocks import plain_text

    if not 0 <= col < table.cols:
        raise OperationError("Nieprawidłowa kolumna.")
    first = 1 if table.header_row else 0
    if any(cell.row_span > 1 for row in table.cells[first:] for cell in row):
        raise OperationError("Nie można sortować tabeli z komórkami scalonymi w pionie.")
    cov = table.coverage()
    body = list(range(first, table.rows))
    texts = {r: plain_text(table.cells[cov[r][col][0]][cov[r][col][1]].runs).strip() for r in body}
    numbers = {r: parse_number(texts[r]) for r in body}
    numeric = all(numbers[r] is not None for r in body if texts[r])

    def key(r: int):
        empty = texts[r] == ""
        value = numbers[r] if numeric else texts[r].casefold()
        return (empty, value if not empty else 0)

    non_empty = [r for r in body if texts[r]]
    empty = [r for r in body if not texts[r]]
    order = sorted(non_empty, key=key, reverse=descending) + empty
    grid = _grid(table)
    heights = list(table.row_heights)
    new_grid = grid[:first] + [grid[r] for r in order]
    new_heights = heights[:first] + [heights[r] for r in order]
    return recompute_formulas(_build(table, new_grid, row_heights=tuple(new_heights)))


# ---------------------------------------------------------------------------
# Formuły
# ---------------------------------------------------------------------------

def set_cell_formula(table: TableData, row: int, col: int, formula: str) -> TableData:
    ar, ac = table.anchor_of(row, col)
    formula = formula.strip()
    if formula and not formula.startswith("="):
        formula = "=" + formula
    grid = _grid(table)
    cell = grid[ar][ac]
    runs = cell.runs if formula else ()
    grid[ar][ac] = replace(cell, formula=formula, runs=runs)
    return recompute_formulas(_build(table, grid))


def recompute_formulas(table: TableData) -> TableData:
    """Przelicza komórki z formułami (dwa przebiegi – formuły mogą zależeć od innych formuł)."""
    from .formulas import evaluate, parse_number

    cells = [(r, c) for r, row in enumerate(table.cells) for c, cell in enumerate(row) if cell.formula]
    if not cells:
        return table
    values: dict[tuple[int, int], float | None] = {}
    results: dict[tuple[int, int], str] = {}
    for _ in range(2):
        for r, c in cells:
            text = evaluate(table, r, c, table.cells[r][c].formula, values)
            results[(r, c)] = text
            values[(r, c)] = parse_number(text)
    grid = _grid(table)
    changed = False
    for (r, c), text in results.items():
        cell = grid[r][c]
        base = cell.runs[0] if cell.runs else TextRun()
        new_runs = (replace(base, text=text),) if text else ()
        if new_runs != cell.runs:
            grid[r][c] = replace(cell, runs=new_runs)
            changed = True
    return _build(table, grid) if changed else table
