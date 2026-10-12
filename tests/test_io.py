"""Zapis/odczyt JSON, odporność na złe dane i eksport PDF."""
import json
from dataclasses import replace

import pytest

from qmlword.io import json_format
from qmlword.io.formats import default_registry
from qmlword.io.json_format import DocumentFormatError
from qmlword.model import table_ops
from qmlword.model.blocks import Block, TextRun
from qmlword.model.document import DocumentData, PageSettings


def sample_document() -> DocumentData:
    table = Block.new_table(3, 2)
    table = replace(table, table=table_ops.set_cell_runs(table.table, 0, 0, (TextRun("Nagłówek", bold=True),)))
    blocks = (
        Block.paragraph("Raport roczny", style="title"),
        replace(Block.heading(1, "Wstęp"), description="Krótki opis sekcji"),
        Block.paragraph(runs=(TextRun("Pogrubione ", bold=True), TextRun("link", link="https://example.com"))),
        table,
        Block.new_caption(table.id, "Zestawienie"),
        Block.page_break(),
        Block.heading(2, "Podsekcja"),
    )
    return replace(DocumentData.create_default(), blocks=blocks,
                   page=PageSettings(size="A5", landscape=True, margin_left=15))


def test_json_roundtrip_preserves_everything(tmp_path):
    doc = sample_document()
    path = tmp_path / "dok.qwd.json"
    registry = default_registry()
    registry.exporter("json").write(doc, str(path))
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["format"] == json_format.FORMAT_ID and data["schemaVersion"] == json_format.SCHEMA_VERSION
    warnings = []
    loaded = registry.importer_for(str(path)).read(str(path), warnings)
    assert loaded.blocks == doc.blocks
    assert loaded.page == doc.page
    assert warnings == []


@pytest.mark.parametrize("raw, message", [
    (b"{not json", "JSON"),
    (b"\xff\xfe\x00garbage", "UTF-8"),
    (b"[1,2,3]", "obiektu"),
    (b'{"format": "inny", "blocks": []}', "nie jest dokument"),
    (b'{"format": "qmlword-document", "schemaVersion": 1, "blocks": 5}', "bloków"),
])
def test_invalid_files_raise_readable_errors(raw, message):
    with pytest.raises(DocumentFormatError, match=message):
        json_format.parse(raw)


def test_damaged_content_is_repaired_with_warnings():
    raw = json.dumps({
        "format": "qmlword-document", "schemaVersion": 99,
        "page": {"size": "A0", "margins": {"left": 1e9}},
        "blocks": [{"type": "paragraph", "runs": "x"}, {"id": "t", "type": "table", "table": {}},
                   {"type": "hologram", "id": "h"}, "zły", {"id": "c", "type": "caption",
                                                             "caption": {"targetId": "nope"}}],
    }).encode()
    warnings = []
    doc = json_format.parse(raw, warnings)
    assert [b.type for b in doc.blocks] == ["paragraph", "table", "unknown", "paragraph"]
    assert doc.page.size == "A4" and doc.page.margin_left == 100 or doc.page.margin_left == 25
    assert any("nowszej wersji" in w for w in warnings)
    assert all(b.id for b in doc.blocks)


def test_pdf_export_paginates_and_reports_errors(qapp, tmp_path):
    from qmlword.io.text_document_builder import PagedDocument

    doc = sample_document()
    long_table = Block.new_table(120, 3)
    doc = replace(doc, blocks=doc.blocks + (long_table,))
    paged = PagedDocument(doc, str(tmp_path), 96)
    assert paged.page_count() >= 3  # podział strony + długa tabela na kilku stronach
    out = tmp_path / "out.pdf"
    default_registry().exporter("pdf").write(doc, str(out), str(tmp_path))
    assert out.read_bytes().startswith(b"%PDF")
    from qmlword.io.formats import ExportError
    with pytest.raises(ExportError):
        default_registry().exporter("pdf").write(doc, str(tmp_path / "brak" / "x.pdf"), "")
