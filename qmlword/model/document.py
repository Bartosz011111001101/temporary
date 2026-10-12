"""Stan całego dokumentu: metadane, ustawienia strony i uporządkowana lista bloków."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any

from .blocks import Block, clamp_number

PAGE_SIZES_MM = {
    "A4": (210.0, 297.0),
    "A5": (148.0, 210.0),
    "Letter": (215.9, 279.4),
    "Legal": (215.9, 355.6),
}

MM_PER_INCH = 25.4
SCREEN_DPI = 96.0


def mm_to_px(mm: float, dpi: float = SCREEN_DPI) -> float:
    return mm / MM_PER_INCH * dpi


@dataclass(frozen=True)
class PageSettings:
    size: str = "A4"
    landscape: bool = False
    margin_top: float = 25.0     # mm
    margin_bottom: float = 25.0
    margin_left: float = 25.0
    margin_right: float = 25.0

    def size_mm(self) -> tuple[float, float]:
        w, h = PAGE_SIZES_MM.get(self.size, PAGE_SIZES_MM["A4"])
        return (h, w) if self.landscape else (w, h)

    def content_width_mm(self) -> float:
        return self.size_mm()[0] - self.margin_left - self.margin_right

    def to_json(self) -> dict:
        return {
            "size": self.size,
            "orientation": "landscape" if self.landscape else "portrait",
            "margins": {
                "top": self.margin_top,
                "bottom": self.margin_bottom,
                "left": self.margin_left,
                "right": self.margin_right,
            },
        }

    @staticmethod
    def from_json(data: Any) -> "PageSettings":
        if not isinstance(data, dict):
            return PageSettings()
        d = PageSettings()
        size = data.get("size")
        margins = data.get("margins") if isinstance(data.get("margins"), dict) else {}
        page = PageSettings(
            size=size if size in PAGE_SIZES_MM else d.size,
            landscape=data.get("orientation") == "landscape",
            margin_top=clamp_number(margins.get("top"), 0, 100, d.margin_top),
            margin_bottom=clamp_number(margins.get("bottom"), 0, 100, d.margin_bottom),
            margin_left=clamp_number(margins.get("left"), 0, 100, d.margin_left),
            margin_right=clamp_number(margins.get("right"), 0, 100, d.margin_right),
        )
        return page.validated()

    def validated(self) -> "PageSettings":
        """Marginesy nie mogą zjeść strony: zostawiamy co najmniej 30 mm obszaru tekstu."""
        w, h = self.size_mm()
        page = self
        if page.margin_left + page.margin_right > w - 30:
            page = replace(page, margin_left=25.0, margin_right=25.0)
        if page.margin_top + page.margin_bottom > h - 30:
            page = replace(page, margin_top=25.0, margin_bottom=25.0)
        return page


@dataclass(frozen=True)
class DocumentMeta:
    title: str = ""
    author: str = ""
    created: str = ""   # ISO 8601
    modified: str = ""
    font_family: str = "Calibri"
    font_size: float = 11.0  # pt, tekst podstawowy

    def to_json(self) -> dict:
        return {
            "title": self.title,
            "author": self.author,
            "created": self.created,
            "modified": self.modified,
            "fontFamily": self.font_family,
            "fontSize": self.font_size,
        }

    @staticmethod
    def from_json(data: Any) -> "DocumentMeta":
        if not isinstance(data, dict):
            return DocumentMeta()

        def s(key: str, default: str = "") -> str:
            v = data.get(key)
            return v if isinstance(v, str) else default

        family = s("fontFamily")[:128] or "Calibri"
        return DocumentMeta(
            title=s("title"),
            author=s("author"),
            created=s("created"),
            modified=s("modified"),
            font_family=family,
            font_size=clamp_number(data.get("fontSize"), 6, 72, 11.0),
        )


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class DocumentData:
    meta: DocumentMeta = DocumentMeta()
    page: PageSettings = PageSettings()
    blocks: tuple = field(default_factory=tuple)

    __hash__ = None

    @staticmethod
    def create_default() -> "DocumentData":
        stamp = now_iso()
        return DocumentData(
            meta=DocumentMeta(created=stamp, modified=stamp),
            blocks=(Block.paragraph(),),
        )
