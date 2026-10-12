"""Style akapitów – jedno źródło prawdy dla edytora QML i eksportu PDF."""
from __future__ import annotations

from .document import DocumentMeta

HEADING_COLOR = "#1f3a5f"
TEXT_COLOR = "#1b1f24"
CAPTION_COLOR = "#4a5560"
DESCRIPTION_COLOR = "#5b6670"
LINK_COLOR = "#1f5fa8"

STYLE_LABELS = {
    "body": "Tekst podstawowy",
    "title": "Tytuł",
    "h1": "Nagłówek 1",
    "h2": "Nagłówek 2",
    "h3": "Nagłówek 3",
    "h4": "Nagłówek 4",
    "h5": "Nagłówek 5",
    "h6": "Nagłówek 6",
}

# rozmiar względem tekstu podstawowego (pt przy domyślnym 11 pt)
_SIZES = {"title": 26.0, "h1": 20.0, "h2": 16.0, "h3": 13.5, "h4": 12.0, "h5": 11.0, "h6": 11.0}


def text_style(key: str, meta: DocumentMeta) -> dict:
    base = meta.font_size
    scale = base / 11.0
    if key == "body":
        return {"key": key, "label": STYLE_LABELS[key], "family": meta.font_family, "pointSize": base,
                "bold": False, "italic": False, "color": TEXT_COLOR}
    if key == "title":
        return {"key": key, "label": STYLE_LABELS[key], "family": meta.font_family,
                "pointSize": round(_SIZES[key] * scale, 1), "bold": False, "italic": False,
                "color": HEADING_COLOR}
    size = round(_SIZES.get(key, base) * scale, 1)
    return {"key": key, "label": STYLE_LABELS.get(key, key), "family": meta.font_family,
            "pointSize": size, "bold": True, "italic": key == "h6",
            "color": HEADING_COLOR}


def all_text_styles(meta: DocumentMeta) -> dict:
    return {key: text_style(key, meta) for key in STYLE_LABELS}
