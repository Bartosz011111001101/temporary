"""Generuje zestaw ikon SVG do qml/icons (uruchom: python tools/make_icons.py).

Ikony są czarne; QML barwi je przez ``icon.color``, więc jeden plik
obsługuje stany normal / hover / disabled / selected.
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "qml" / "icons"

STROKE = ('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 20 20" '
          'fill="none" stroke="#000" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{}</svg>')


def p(d: str, extra: str = "") -> str:
    return f'<path d="{d}"{extra}/>'


def dot(x: float, y: float, r: float = 1.25) -> str:
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="#000" stroke="none"/>'


ICONS = {
    "new": p("M5 2.5h6l4 4v11H5z") + p("M11 2.5v4h4") + p("M10 9.5v5M7.5 12h5"),
    "open": p("M2.5 5h5l1.5 1.8h8.5v9.7h-15z") + p("M2.5 9h15"),
    "save": p("M3.5 3.5h10l3 3v10h-13z") + p("M6.5 3.5v4h6v-4") + p("M6.5 16.5v-5h7v5"),
    "saveAs": p("M3.5 3.5h9l3 3v3") + p("M3.5 3.5v13h6") + p("M6.5 3.5v4h5v-4")
              + p("M11.5 17l.6-2.6 4.6-4.6 2 2-4.6 4.6z"),
    "undo": p("M7.5 5.5L4 9l3.5 3.5") + p("M4 9h8.5a4 4 0 0 1 0 8H10"),
    "redo": p("M12.5 5.5L16 9l-3.5 3.5") + p("M16 9H7.5a4 4 0 0 0 0 8H10"),
    "export": p("M10 3v9") + p("M6.5 6.5L10 3l3.5 3.5") + p("M4 11v5.5h12V11"),
    "pageSetup": p("M4.5 2.5h11v15h-11z") + p("M7.5 5.5h5v9h-5z", ' stroke-dasharray="1.6 1.6"'),
    "preview": p("M3.5 3.5h7v10h-7z") + p("M9.5 6.5h7v10h-7z"),
    "edit": p("M4 16l.9-3.6 8.3-8.3 2.7 2.7-8.3 8.3z") + p("M11.6 5.7l2.7 2.7"),
    "search": '<circle cx="8.5" cy="8.5" r="5"/>' + p("M12.3 12.3L17 17"),
    "chevronUp": p("M5 12.5l5-5 5 5"),
    "chevronDown": p("M5 7.5l5 5 5-5"),
    "chevronRight": p("M7.5 5l5 5-5 5"),
    "chevronLeft": p("M12.5 5l-5 5 5 5"),
    "close": p("M5.5 5.5l9 9M14.5 5.5l-9 9"),
    "alignLeft": p("M3 4.5h14M3 8.5h9M3 12.5h14M3 16.5h9"),
    "alignCenter": p("M3 4.5h14M5.5 8.5h9M3 12.5h14M5.5 16.5h9"),
    "alignRight": p("M3 4.5h14M8 8.5h9M3 12.5h14M8 16.5h9"),
    "alignJustify": p("M3 4.5h14M3 8.5h14M3 12.5h14M3 16.5h14"),
    "listBullet": dot(4.5, 5) + dot(4.5, 10) + dot(4.5, 15) + p("M8 5h9M8 10h9M8 15h9"),
    "listNumber": p("M3.3 3.8l1-.6v4") + p("M3 9.4a1.1 1.1 0 1 1 1.9.8L3 12.4h2.1")
                  + p("M3.1 14.2h1.9l-1 1.3a1 1 0 1 1-.9 1.5") + p("M8 5.5h9M8 10.5h9M8 15.5h9"),
    "indentMore": p("M3 4h14M9 8h8M9 12h8M3 16h14") + p("M3 7.5l3 2.5-3 2.5"),
    "indentLess": p("M3 4h14M9 8h8M9 12h8M3 16h14") + p("M6 7.5L3 10l3 2.5"),
    "lineSpacing": p("M4.5 3.5v13") + p("M2.5 5.5l2-2 2 2M2.5 14.5l2 2 2-2") + p("M9 5h8M9 10h8M9 15h8"),
    "table": p("M3 4h14v12H3z") + p("M3 8.3h14M3 12.2h14M8.7 4v12M13.3 4v12"),
    "image": p("M3 4h14v12H3z") + p("M3 13.5l4-4 3.5 3.5 2.5-2.5 4 4") + '<circle cx="13" cy="7.5" r="1.3"/>',
    "link": p("M8.5 11.5a3 3 0 0 0 4.2 0l2.6-2.6a3 3 0 0 0-4.2-4.2l-.9.9")
            + p("M11.5 8.5a3 3 0 0 0-4.2 0l-2.6 2.6a3 3 0 0 0 4.2 4.2l.9-.9"),
    "caption": p("M4 3.5h12v8H4z") + p("M6 14.5h8M7.5 17h5"),
    "pageBreak": p("M3 6.5v-3h14v3M3 13.5v3h14v-3") + p("M2.5 10h2M6.5 10h2M10.5 10h2M14.5 10h2.5"),
    "grip": dot(7.5, 5, 1.2) + dot(12.5, 5, 1.2) + dot(7.5, 10, 1.2) + dot(12.5, 10, 1.2)
            + dot(7.5, 15, 1.2) + dot(12.5, 15, 1.2),
    "plus": p("M10 4.5v11M4.5 10h11"),
    "minus": p("M4.5 10h11"),
    "subsection": p("M5 4v6.5a2 2 0 0 0 2 2h8") + p("M12.5 10l2.5 2.5-2.5 2.5"),
    "panelLeft": p("M3 4h14v12H3z") + p("M8 4v12"),
    "panelRight": p("M3 4h14v12H3z") + p("M12 4v12"),
    "more": dot(5, 10) + dot(10, 10) + dot(15, 10),
    "trash": p("M4 6h12M8 6V4h4v2") + p("M5.5 6l.8 10.5h7.4L14.5 6"),
    "heading": p("M5 4v12M13 4v12M5 10h8"),
    "paragraph": p("M3.5 5h13M3.5 8.5h13M3.5 12h13M3.5 15.5h8"),
    "title": p("M4 5h12M10 5v11"),
    "textColor": p("M5.5 13.5L10 3l4.5 10.5M7.3 9.5h5.4"),
    "highlight": p("M5 14l7.5-7.5 3 3L8 17H5z") + p("M11 8l3 3"),
    "expandAll": p("M6 8l4 4 4-4") + p("M6 4l4 4 4-4", ' opacity=".55"'),
    "collapseAll": p("M6 12l4-4 4 4") + p("M6 16l4-4 4 4", ' opacity=".55"'),
    "arrowUp": p("M10 16V4M5.5 8.5L10 4l4.5 4.5"),
    "arrowDown": p("M10 4v12M5.5 11.5L10 16l4.5-4.5"),
    "arrowLeft": p("M16 10H4M8.5 5.5L4 10l4.5 4.5"),
    "arrowRight": p("M4 10h12M11.5 5.5L16 10l-4.5 4.5"),
    "warning": p("M10 3l8 14H2z") + p("M10 8v4M10 14.4v.2"),
    "info": '<circle cx="10" cy="10" r="7.5"/>' + p("M10 9v5M10 6.2v.2"),
    "check": p("M4 10.5l4 4 8-9"),
    "duplicate": p("M7 7h9v9H7z") + p("M4 13V4h9"),
    "placeholder": p("M3 5h14v10H3z", ' stroke-dasharray="2 2"') + p("M10 8v4M8 10h4"),
    "mergeCells": p("M3 4h14v12H3z") + p("M6 10h8M7.5 8l-1.5 2 1.5 2M12.5 8l1.5 2-1.5 2"),
    "splitCells": p("M3 4h14v12H3z") + p("M10 4v12") + p("M4.5 10h3M12.5 10h3"),
    "rowAbove": p("M3 9h14v7H3z") + p("M10 2.5v5M7.5 5h5"),
    "rowBelow": p("M3 4h14v7H3z") + p("M10 12.5v5M7.5 15h5"),
    "colLeft": p("M9 3h7v14H9z") + p("M2.5 10h5M5 7.5v5"),
    "colRight": p("M4 3h7v14H4z") + p("M12.5 10h5M15 7.5v5"),
    "zoomIn": '<circle cx="8.5" cy="8.5" r="5"/>' + p("M12.3 12.3L17 17M8.5 6.5v4M6.5 8.5h4"),
    "zoomOut": '<circle cx="8.5" cy="8.5" r="5"/>' + p("M12.3 12.3L17 17M6.5 8.5h4"),
    "description": p("M4 4.5h12") + p("M4 8.5h8M4 12h10M4 15.5h6", ' opacity=".6"'),
    "cut": '<circle cx="6" cy="15" r="2.4"/><circle cx="14" cy="15" r="2.4"/>' + p("M7.6 13.2L15 3.5M12.4 13.2L5 3.5"),
    "copy": p("M7 7h9v10H7z") + p("M4 13V3.5h9"),
    "paste": p("M7 4.5H5v13h10v-13h-2") + p("M7.5 3h5v3h-5z") + p("M8 10h4M8 13h4", ' opacity=".6"'),
    "brush": p("M11.5 3.5l5 5-4.5 1.5-2-2z") + p("M10 8.5l-6 6 1.5 1.5 6-6"),
    "rotateLeft": p("M5 9a6 6 0 1 1 1.8 4.2") + p("M5 4.5V9h4.5"),
    "rotateRight": p("M15 9a6 6 0 1 0-1.8 4.2") + p("M15 4.5V9h-4.5"),
    "sortAsc": p("M5 4v12M2.5 13.5L5 16l2.5-2.5") + p("M10 5h7M10 9.5h5M10 14h3"),
    "sortDesc": p("M5 4v12M2.5 13.5L5 16l2.5-2.5") + p("M10 5h3M10 9.5h5M10 14h7"),
    "borders": p("M3 3h14v14H3z") + p("M3 10h14M10 3v14", ' opacity=".45"'),
    "wrapLeft": p("M3 4h6v7H3z") + p("M11 4.5h6M11 8h6M11 11.5h6M3 15h14"),
    "wrapRight": p("M11 4h6v7h-6z") + p("M3 4.5h6M3 8h6M3 11.5h6M3 15h14"),
    "wrapInline": p("M6 4h8v7H6z") + p("M3 15h14"),
    "formula": p("M14 4.5c-2-1-3.5 0-4 2l-2 8c-.5 2-2 3-4 2") + p("M6 9h7"),
}

APP_ICON = ('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">'
            '<rect x="10" y="4" width="44" height="56" rx="5" fill="#2a5d9f"/>'
            '<path d="M20 18h24M20 27h24M20 36h16M20 45h20" stroke="#fff" stroke-width="4" stroke-linecap="round"/>'
            '</svg>')


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, body in ICONS.items():
        (OUT / f"{name}.svg").write_text(STROKE.format(body), encoding="utf-8")
    (OUT / "app.svg").write_text(APP_ICON, encoding="utf-8")
    print(f"Zapisano {len(ICONS) + 1} ikon w {OUT}")


if __name__ == "__main__":
    main()
