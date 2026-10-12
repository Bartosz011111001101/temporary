"""Tworzy przykładowy dokument examples/przyklad.qwd.json (z obrazem i tabelą).

Uruchom: python tools/make_example.py
"""
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter, QPen  # noqa: E402

from qmlword.io.formats import default_registry  # noqa: E402
from qmlword.model import table_ops  # noqa: E402
from qmlword.model.blocks import Block, ParagraphFormat, TextRun, plain_runs  # noqa: E402
from qmlword.model.document import DocumentData, DocumentMeta  # noqa: E402

OUT = ROOT / "examples"


def make_chart(path: Path) -> None:
    img = QImage(900, 420, QImage.Format.Format_ARGB32)
    img.fill(QColor("#ffffff"))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor("#c9ced6"), 1))
    for i in range(5):
        y = 60 + i * 75
        p.drawLine(70, y, 870, y)
    values = [42, 55, 61, 58, 73, 81]
    labels = ["2020", "2021", "2022", "2023", "2024", "2025"]
    font = QFont("Segoe UI", 14)
    p.setFont(font)
    for i, v in enumerate(values):
        x = 110 + i * 125
        h = v * 3.6
        p.fillRect(QRectF(x, 360 - h, 70, h), QColor("#2a5d9f" if i < 5 else "#d97706"))
        p.setPen(QColor("#1d2329"))
        p.drawText(QRectF(x - 10, 370, 90, 30), Qt.AlignmentFlag.AlignCenter, labels[i])
        p.drawText(QRectF(x - 10, 330 - h, 90, 26), Qt.AlignmentFlag.AlignCenter, str(v))
    p.end()
    img.save(str(path))


def main() -> None:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)  # noqa: F841
    OUT.mkdir(exist_ok=True)
    make_chart(OUT / "wykres.png")

    table = Block.new_table(4, 3)
    t = table.table
    rows = [["Kwartał", "Przychód (tys. zł)", "Zmiana"], ["I", "1 240", "+4%"], ["II", "1 315", "+6%"], ["III", "1 402", "+7%"]]
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            t = table_ops.set_cell_runs(t, r, c, plain_runs(value))
    t = table_ops.set_cells_align(t, 0, 1, 3, 2, "right")
    table = replace(table, table=t)
    image = replace(Block.new_image("wykres.png"), image=replace(Block.new_image("").image, path="wykres.png", width=0.8))
    bullet = ParagraphFormat(list="bullet")

    blocks = (
        Block.paragraph("Raport kwartalny", style="title"),
        Block.paragraph(runs=(TextRun("Dokument przykładowy – pokazuje sekcje, listy, tabelę z podpisem, "),
                              TextRun("obraz", bold=True), TextRun(" i "),
                              TextRun("link", link="https://doc.qt.io"), TextRun("."))),
        replace(Block.heading(1, "Podsumowanie"), description="Najważniejsze wnioski w skrócie"),
        Block.paragraph("Przychody rosły w każdym kwartale. Najważniejsze czynniki:"),
        Block.paragraph("nowi klienci w segmencie B2B,", para=bullet),
        Block.paragraph("niższe koszty logistyki,", para=bullet),
        Block.paragraph("sezonowość sprzedaży w III kwartale.", para=bullet),
        Block.heading(2, "Wyniki finansowe"),
        table,
        Block.new_caption(table.id, "Przychody w kolejnych kwartałach"),
        Block.heading(2, "Trend wieloletni"),
        image,
        Block.new_caption(image.id, "Przychód roczny (mln zł)"),
        Block.page_break(),
        Block.heading(1, "Plan na kolejny rok"),
        Block.paragraph(runs=(TextRun("Priorytety: "), TextRun("automatyzacja", italic=True),
                              TextRun(", ekspansja zagraniczna i "), TextRun("nowe produkty", highlight="#fff3a3"),
                              TextRun("."))),
        Block.heading(2, "Ryzyka"),
        Block.paragraph("Kursy walut oraz dostępność specjalistów."),
    )
    doc = replace(DocumentData.create_default(), blocks=blocks,
                  meta=replace(DocumentMeta(), title="Raport kwartalny", author="QmlWord"))
    path = OUT / "przyklad.qwd.json"
    default_registry().exporter("json").write(doc, str(path))
    print(f"Zapisano {path}")


if __name__ == "__main__":
    main()
