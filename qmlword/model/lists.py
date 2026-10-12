"""Numeracja i znaczniki list (wspólne dla edytora i eksportu)."""
from __future__ import annotations

from dataclasses import dataclass

from .blocks import PARAGRAPH

BULLETS = {"disc": "•", "circle": "◦", "square": "▪"}
DEFAULT_BULLETS = ("disc", "circle", "square")
DEFAULT_NUMBERS = ("decimal", "lowerAlpha", "lowerRoman")

BULLET_LABELS = {"disc": "• Kropka", "circle": "◦ Kółko", "square": "▪ Kwadrat"}
NUMBER_LABELS = {"decimal": "1. 2. 3.", "decimalParen": "1) 2) 3)", "lowerAlpha": "a) b) c)",
                 "upperAlpha": "A. B. C.", "lowerRoman": "i. ii. iii.", "upperRoman": "I. II. III.",
                 "multilevel": "1. 1.1. 1.1.1."}


@dataclass(frozen=True)
class ListInfo:
    kind: str = ""        # "" | "bullet" | "number"
    style: str = ""       # efektywny styl
    number: int = 0
    marker: str = ""      # gotowy tekst znacznika, np. "b)" albo "2.1."
    prefix: str = ""      # numeracja wielopoziomowa: część rodzica, np. "2."


def to_roman(n: int) -> str:
    values = ((1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"),
              (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i"))
    out = []
    for value, sym in values:
        while n >= value:
            out.append(sym)
            n -= value
    return "".join(out) or "0"


def to_alpha(n: int) -> str:
    out = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        out = chr(ord("a") + rem) + out
    return out or "a"


def effective_style(kind: str, style: str, indent: int) -> str:
    if style:
        return style
    defaults = DEFAULT_BULLETS if kind == "bullet" else DEFAULT_NUMBERS
    return defaults[indent % len(defaults)]


def format_number(style: str, n: int) -> str:
    if style == "decimalParen":
        return f"{n})"
    if style == "lowerAlpha":
        return f"{to_alpha(n)})"
    if style == "upperAlpha":
        return f"{to_alpha(n).upper()}."
    if style == "lowerRoman":
        return f"{to_roman(n)}."
    if style == "upperRoman":
        return f"{to_roman(n).upper()}."
    return f"{n}."


def list_infos(blocks: tuple) -> list[ListInfo]:
    infos: list[ListInfo] = []
    counters: dict[int, int] = {}   # bieżąca lista: poziom -> numer
    kinds: dict[int, str] = {}      # bieżąca lista: poziom -> styl numeracji
    memory: dict[int, int] = {}     # ostatni numer na poziomie (dla „kontynuuj numerację”)
    for block in blocks:
        para = block.para
        if block.type != PARAGRAPH or para.list == "none":
            counters.clear()
            infos.append(ListInfo())
            continue
        level = para.indent
        for deeper in [k for k in counters if k > level]:
            del counters[deeper]
        style = effective_style(para.list, para.list_style, level)
        if para.list == "bullet":
            counters.pop(level, None)
            infos.append(ListInfo("bullet", style, 0, BULLETS.get(style, "•")))
            continue
        if level in counters and kinds.get(level) != style:
            del counters[level]  # inny styl numeracji = nowa lista
        if para.list_start > 0:
            n = para.list_start
        elif level in counters:
            n = counters[level] + 1
        elif para.list_continue and level in memory:
            n = memory[level] + 1
        else:
            n = 1
        counters[level] = n
        kinds[level] = style
        memory[level] = n
        if style == "multilevel":
            chain = [counters.get(k, 1) for k in range(level + 1)]
            prefix = "".join(f"{c}." for c in chain[:-1])
            infos.append(ListInfo("number", style, n, prefix + f"{n}.", prefix))
        else:
            infos.append(ListInfo("number", style, n, format_number(style, n)))
    return infos
