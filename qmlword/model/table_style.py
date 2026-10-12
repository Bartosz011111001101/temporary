"""Wygląd komórek tabeli wynikający ze stylu tabeli i ustawień pojedynczych komórek.

Jedno źródło prawdy dla edytora (QML) i eksportu (PDF).
"""
from __future__ import annotations

from .blocks import TableData

STYLE_LABELS = {
    "grid": "Siatka",
    "light": "Jasna (linie poziome)",
    "striped": "Pasy",
    "accent": "Akcent",
    "plain": "Bez obramowania",
}

_STYLES = {
    #          krawędź          kolor krawędzi  tło nagłówka  tekst nagłówka  linia pod nagłówkiem  pasy
    "grid":    {"edge": "all", "border": "#9aa3ad", "head_bg": "#eef1f4", "head_fg": "", "head_line": "", "band": "#f4f6f8"},
    "light":   {"edge": "h",   "border": "#c4cad1", "head_bg": "", "head_fg": "", "head_line": "#2a5d9f", "band": "#f4f6f8"},
    "striped": {"edge": "all", "border": "#d3d9e0", "head_bg": "#2a5d9f", "head_fg": "#ffffff", "head_line": "", "band": "#eef3fa"},
    "accent":  {"edge": "all", "border": "#b9c4d1", "head_bg": "#1f3a5f", "head_fg": "#ffffff", "head_line": "", "band": "#f1f4f8"},
    "plain":   {"edge": "none", "border": "#b9c4d1", "head_bg": "", "head_fg": "", "head_line": "", "band": "#f4f6f8"},
}

THIN = 0.75   # pt
THICK = 2.0
EXPLICIT_COLOR = "#4b5560"


def _edge(width: float, color: str) -> dict:
    return {"w": width, "c": color}


def appearance(table: TableData) -> list[list[dict]]:
    """Dla każdej komórki: tło, kolor i pogrubienie tekstu oraz cztery krawędzie (szerokość w pt)."""
    st = _STYLES.get(table.style, _STYLES["grid"])
    rows, cols = table.rows, table.cols
    cov = table.coverage()
    banded = table.banded_rows or table.style == "striped"
    out: list[list[dict]] = []
    for r in range(rows):
        row_out = []
        for c in range(cols):
            cell = table.cells[r][c]
            ar, ac = cov[r][c]
            anchor = table.cells[ar][ac]
            header = table.header_row and ar == 0
            body_index = ar - (1 if table.header_row else 0)
            background = ""
            color = ""
            if header:
                background = st["head_bg"]
                color = st["head_fg"]
            elif banded and body_index % 2 == 1:
                background = st["band"]
            if anchor.background:
                background = anchor.background
            bold = header or (table.first_column and ac == 0)

            def default(side: str) -> dict:
                kind = st["edge"]
                if kind == "all" or (kind == "h" and side in ("top", "bottom")):
                    return _edge(THIN, st["border"])
                if kind == "none" and header and side == "bottom":
                    return _edge(THIN, st["border"])
                return _edge(0, st["border"])

            edges = {}
            for side, explicit in (("top", anchor.border_top), ("bottom", anchor.border_bottom),
                                   ("left", anchor.border_left), ("right", anchor.border_right)):
                if explicit == "none":
                    edges[side] = _edge(0, EXPLICIT_COLOR)
                elif explicit == "thin":
                    edges[side] = _edge(THIN, EXPLICIT_COLOR)
                elif explicit == "thick":
                    edges[side] = _edge(THICK, EXPLICIT_COLOR)
                else:
                    edges[side] = default(side)
            if header and st["head_line"] and not anchor.border_bottom:
                edges["bottom"] = _edge(1.5, st["head_line"])
            row_out.append({"background": background, "color": color, "bold": bold, **edges})
        out.append(row_out)
    return out
