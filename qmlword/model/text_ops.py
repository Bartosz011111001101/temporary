"""Operacje na przebiegach tekstu (runs): cięcie, formatowanie zakresu, zamiana, wielkość liter.

Pozycje są liczone w znakach tekstu jawnego (``plain_text(runs)``), tak samo jak
w edytorze (``\\n`` = miękki podział wiersza = jeden znak).
"""
from __future__ import annotations

from dataclasses import fields, replace
from typing import Any, Iterable

from .blocks import TextRun, normalize_runs, sanitize_color

# Nazwy właściwości w JSON/QML → pola TextRun
PROP_FIELDS = {
    "bold": "bold", "italic": "italic", "underline": "underline", "strike": "strike",
    "color": "color", "highlight": "highlight", "fontFamily": "font_family", "fontSize": "font_size",
    "link": "link", "vertical": "vertical", "smallCaps": "small_caps",
}
BOOL_PROPS = {"bold", "italic", "underline", "strike", "smallCaps"}


def runs_length(runs: Iterable[TextRun]) -> int:
    return sum(len(r.text) for r in runs)


def split_runs(runs: tuple, pos: int) -> tuple[tuple, tuple]:
    left: list[TextRun] = []
    right: list[TextRun] = []
    offset = 0
    for run in runs:
        end = offset + len(run.text)
        if end <= pos:
            left.append(run)
        elif offset >= pos:
            right.append(run)
        else:
            cut = pos - offset
            left.append(replace(run, text=run.text[:cut]))
            right.append(replace(run, text=run.text[cut:]))
        offset = end
    return tuple(left), tuple(right)


def slice_runs(runs: tuple, start: int, end: int) -> tuple:
    _, rest = split_runs(runs, start)
    middle, _ = split_runs(rest, max(0, end - start))
    return middle


def format_at(runs: tuple, pos: int) -> TextRun:
    """Format znaku przed pozycją (jak przy pisaniu); na początku – pierwszego znaku."""
    target = pos - 1 if pos > 0 else 0
    offset = 0
    last = None
    for run in runs:
        if offset <= target < offset + len(run.text):
            return replace(run, text="")
        offset += len(run.text)
        last = run
    return replace(last, text="") if last is not None else TextRun()


def apply_props_to_run(run: TextRun, props: dict) -> TextRun:
    changes: dict[str, Any] = {}
    for key, value in props.items():
        name = PROP_FIELDS.get(key)
        if name is None:
            continue
        clear = value is None or value == "" or (key == "fontSize" and not value)
        if key in BOOL_PROPS:
            changes[name] = None if clear else bool(value)
        elif key in ("color", "highlight"):
            changes[name] = "" if clear else sanitize_color(value)
        elif key == "fontSize":
            changes[name] = 0.0 if clear else max(4.0, min(144.0, float(value)))
        elif key == "vertical":
            changes[name] = value if value in ("super", "sub") else ""
        else:
            changes[name] = "" if clear else str(value)
    return replace(run, **changes) if changes else run


def apply_props(runs: tuple, start: int, end: int, props: dict) -> tuple:
    if start >= end:
        return runs
    left, rest = split_runs(runs, start)
    middle, right = split_runs(rest, end - start)
    middle = tuple(apply_props_to_run(r, props) for r in middle)
    return normalize_runs((*left, *middle, *right))


def insert_runs(runs: tuple, pos: int, new_runs: Iterable[TextRun]) -> tuple:
    left, right = split_runs(runs, pos)
    return normalize_runs((*left, *new_runs, *right))


def replace_in_runs(runs: tuple, start: int, end: int, text: str, props: dict | None = None) -> tuple:
    """Zastępuje zakres tekstem w formacie pierwszego zastępowanego znaku (+ opcjonalne props)."""
    base = format_at(runs, start + 1 if end > start else start)
    new_run = replace(base, text=text)
    if props:
        new_run = apply_props_to_run(new_run, props)
    left, rest = split_runs(runs, start)
    _, right = split_runs(rest, end - start)
    return normalize_runs((*left, new_run, *right))


def _title_case(text: str) -> str:
    out = []
    boundary = True
    for ch in text:
        out.append(ch.upper() if boundary else ch.lower())
        boundary = not ch.isalnum()
    return "".join(out)


def _sentence_case(text: str, at_start: bool) -> str:
    out = []
    capital = at_start
    for ch in text:
        if ch.isalpha():
            out.append(ch.upper() if capital else ch.lower())
            capital = False
        else:
            out.append(ch)
            if ch in ".!?\n":
                capital = True
    return "".join(out)


def change_case(runs: tuple, start: int, end: int, mode: str) -> tuple:
    """mode: lower | upper | title | sentence | toggle. Długość tekstu się nie zmienia."""
    full = "".join(r.text for r in runs)
    segment = full[start:end]
    if mode == "lower":
        new = segment.lower()
    elif mode == "upper":
        new = segment.upper()
    elif mode == "title":
        new = _title_case(segment)
    elif mode == "sentence":
        before = full[:start].rstrip(" ")
        new = _sentence_case(segment, at_start=not before or before[-1] in ".!?\n")
    elif mode == "toggle":
        new = segment.swapcase()
    else:
        return runs
    if len(new) != len(segment):  # np. „ß” → „SS” – zachowujemy pozycje kosztem tej litery
        new = "".join(n if len(n) == 1 else o for n, o in zip(new, segment))
    chars = list(full)
    chars[start:end] = list(new)
    out: list[TextRun] = []
    offset = 0
    for run in runs:
        out.append(replace(run, text="".join(chars[offset:offset + len(run.text)])))
        offset += len(run.text)
    return normalize_runs(out)


def explicit_props(run: TextRun) -> dict:
    """Jawne właściwości przebiegu w nazwach JSON (do malarza formatów, wyszukiwania)."""
    data = run.to_json()
    data.pop("text", None)
    return data


def run_field_names() -> list[str]:
    return [f.name for f in fields(TextRun) if f.name != "text"]
