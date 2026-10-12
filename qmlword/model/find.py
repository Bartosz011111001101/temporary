"""Znajdź i zamień: tekst, całe wyrazy, wielkość liter oraz formatowanie.

Filtr formatowania (``fmt``) to słownik z kluczami jak w JSON przebiegów:
bold/italic/underline/strike/smallCaps (True/False), color, highlight (kolor albo "" = brak),
vertical ("super"/"sub"/"" ), oraz ``style`` – styl akapitu (body, title, h1…h6).
Pusta fraza + filtr = szukanie fragmentów o danym formatowaniu.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace

from . import table_ops, text_ops
from .blocks import CAPTION, HEADING, PARAGRAPH, TABLE, Block, TextRun, plain_text

BOOL_KEYS = ("bold", "italic", "underline", "strike", "smallCaps")


@dataclass(frozen=True)
class Match:
    block_id: str
    start: int
    length: int
    row: int = -1
    col: int = -1

    @property
    def end(self) -> int:
        return self.start + self.length


def _style_key(block: Block) -> str:
    return f"h{block.level}" if block.type == HEADING else block.style


def _effective(run: TextRun, key: str, style: str):
    if key == "bold":
        return run.bold if run.bold is not None else (style.startswith("h") and style != "h6")
    if key == "italic":
        return run.italic if run.italic is not None else style == "h6"
    if key == "underline":
        return bool(run.underline) or bool(run.link)
    if key == "strike":
        return bool(run.strike)
    if key == "smallCaps":
        return bool(run.small_caps)
    return None


def run_matches(run: TextRun, fmt: dict, style: str) -> bool:
    for key in BOOL_KEYS:
        if key in fmt and fmt[key] is not None and bool(fmt[key]) != bool(_effective(run, key, style)):
            return False
    if "color" in fmt and fmt["color"] is not None and (run.color or "") != (fmt["color"] or ""):
        return False
    if "highlight" in fmt and fmt["highlight"] is not None and (run.highlight or "") != (fmt["highlight"] or ""):
        return False
    if "vertical" in fmt and fmt["vertical"] is not None and (run.vertical or "") != (fmt["vertical"] or ""):
        return False
    return True


def _char_runs(runs: tuple) -> list[TextRun]:
    out: list[TextRun] = []
    for run in runs:
        out.extend([run] * len(run.text))
    return out


def clean_format(fmt: dict | None) -> dict:
    """Usuwa klucze „dowolne” (None) – zostają tylko faktyczne warunki/zmiany."""
    return {k: v for k, v in (fmt or {}).items() if v is not None and k != ""}


def _pattern(query: str, case_sensitive: bool, whole_words: bool) -> re.Pattern:
    body = re.escape(query)
    if whole_words:
        body = rf"(?<!\w){body}(?!\w)"
    return re.compile(body, 0 if case_sensitive else re.IGNORECASE)


def _scan(text: str, runs: tuple | None, style: str, query: str, pattern, fmt: dict) -> list[tuple[int, int]]:
    char_runs = _char_runs(runs) if runs is not None else None
    para_fmt_ok = "style" not in fmt or fmt["style"] == style
    char_fmt = {k: v for k, v in fmt.items() if k != "style"}
    if not para_fmt_ok:
        return []
    if char_fmt and char_runs is None:
        return []  # podpisy nie mają formatowania znaków

    def ok(s: int, e: int) -> bool:
        if not char_fmt:
            return True
        return all(run_matches(char_runs[i], char_fmt, style) for i in range(s, e))

    if not query:
        if not fmt:
            return []
        if not char_fmt:
            return [(0, len(text))] if text else []
        spans, start = [], None
        for i in range(len(text) + 1):
            good = i < len(text) and run_matches(char_runs[i], char_fmt, style)
            if good and start is None:
                start = i
            elif not good and start is not None:
                spans.append((start, i))
                start = None
        return spans
    return [(m.start(), m.end()) for m in pattern.finditer(text) if m.end() > m.start() and ok(m.start(), m.end())]


def find_matches(blocks: tuple, query: str, case_sensitive: bool = False, whole_words: bool = False,
                 fmt: dict | None = None) -> list[Match]:
    fmt = clean_format(fmt)
    if not query and not fmt:
        return []
    pattern = _pattern(query, case_sensitive, whole_words) if query else None
    out: list[Match] = []
    for b in blocks:
        if b.type in (PARAGRAPH, HEADING):
            for s, e in _scan(plain_text(b.runs), b.runs, _style_key(b), query, pattern, fmt):
                out.append(Match(b.id, s, e - s))
        elif b.type == CAPTION:
            for s, e in _scan(b.caption.text, None, "caption", query, pattern, fmt):
                out.append(Match(b.id, s, e - s))
        elif b.type == TABLE:
            cov = b.table.coverage()
            for r, row in enumerate(b.table.cells):
                for c, cell in enumerate(row):
                    if cov[r][c] != (r, c) or not cell.runs:
                        continue
                    for s, e in _scan(plain_text(cell.runs), cell.runs, "body", query, pattern, fmt):
                        out.append(Match(b.id, s, e - s, r, c))
    return out


def _replace_runs(runs: tuple, items: list[Match], replacement: str, rfmt: dict, format_only: bool) -> tuple:
    for m in sorted(items, key=lambda x: x.start, reverse=True):
        if format_only:
            runs = text_ops.apply_props(runs, m.start, m.end, rfmt)
        else:
            runs = text_ops.replace_in_runs(runs, m.start, m.end, replacement, rfmt or None)
    return runs


def replace_matches(blocks: tuple, matches: list[Match], replacement: str,
                    replace_fmt: dict | None = None) -> tuple[tuple, int]:
    """Zamienia wskazane trafienia. Pusta zamiana + format = zmiana samego formatowania."""
    rfmt = clean_format(replace_fmt)
    rfmt.pop("style", None)
    format_only = replacement == "" and bool(rfmt)
    by_unit: dict[tuple, list[Match]] = {}
    for m in matches:
        by_unit.setdefault((m.block_id, m.row, m.col), []).append(m)
    out = list(blocks)
    index = {b.id: i for i, b in enumerate(blocks)}
    count = 0
    for (block_id, row, col), items in by_unit.items():
        i = index.get(block_id)
        if i is None:
            continue
        b = out[i]
        if b.type in (PARAGRAPH, HEADING):
            out[i] = replace(b, runs=_replace_runs(b.runs, items, replacement, rfmt, format_only))
        elif b.type == CAPTION:
            if format_only:
                continue
            text = b.caption.text
            for m in sorted(items, key=lambda x: x.start, reverse=True):
                text = text[:m.start] + replacement + text[m.end:]
            out[i] = replace(b, caption=replace(b.caption, text=text))
        elif b.type == TABLE and row >= 0:
            cell = b.table.cells[row][col]
            if cell.formula:
                continue
            new_runs = _replace_runs(cell.runs, items, replacement, rfmt, format_only)
            out[i] = replace(b, table=table_ops.set_cell_runs(b.table, row, col, new_runs))
        else:
            continue
        count += len(items)
    return tuple(out), count
