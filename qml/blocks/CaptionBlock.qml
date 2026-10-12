import QtQuick
import QmlWord.Backend
import ".."

// Podpis tabeli/obrazu: numerowana etykieta („Tabela 2.”) + edytowalna treść.
// Podpis jest powiązany z elementem przez targetId i przenosi się razem z nim.
Item {
    id: block

    property DocumentModel doc
    property EditorController editor
    property string blockId: ""
    property var blockData: ({})
    property string captionLabel: ""
    property int captionNumber: 0
    property real contentWidth: 600
    // Podpis osadzony w ramce pływającego obrazu (rysuje go ImageBlock).
    property bool embedded: false
    // Samodzielny blok podpisu chowa się, gdy jego obraz opływa tekst (podpis jest wtedy w ramce obrazu).
    readonly property bool hiddenByFloat: {
        if (embedded || !doc || doc.revision < 0)
            return false
        var target = blockData.caption ? doc.blockData(blockData.caption.targetId) : null
        return !!(target && target.image && (target.image.wrap === "left" || target.image.wrap === "right"))
    }
    readonly property real baseSize: doc ? doc.meta.fontSize * 0.9 : 10
    readonly property string family: doc ? doc.meta.fontFamily : "Calibri"

    signal navigateUp(real x)
    signal navigateDown(real x)

    implicitHeight: hiddenByFloat ? 0 : row.height + (embedded ? 4 : 14)
    visible: !hiddenByFloat

    function focusAt(start, end) { textEdit.focusAt(start, end) }
    function focusFromAbove(x) { textEdit.focusAt(0, 0) }
    function focusFromBelow(x) { textEdit.focusAt(textEdit.length, textEdit.length) }

    Component.onCompleted: textEdit.setTextSilently(blockData.caption ? blockData.caption.text : "")

    Connections {
        target: block.doc
        function onBlockReset(id) {
            if (id === block.blockId) {
                var d = block.doc.blockData(block.blockId)
                textEdit.setTextSilently(d.caption ? d.caption.text : "")
            }
        }
    }

    TextMetrics {
        id: metrics
        font: textEdit.font
        text: textEdit.text || textEdit.placeholderText
    }

    Row {
        id: row
        y: block.embedded ? 0 : 4
        spacing: 4
        x: Math.max(0, (block.contentWidth - width) / 2)

        Text {
            id: label
            text: (block.captionLabel || "Podpis") + (block.captionNumber > 0 ? " " + block.captionNumber : "") + "."
            font.family: block.family
            font.pointSize: block.baseSize
            font.bold: true
            color: "#4a5560"
            y: 0
        }

        PlainTextEditor {
            id: textEdit
            doc: block.doc
            width: Math.min(block.contentWidth - label.width - 4, Math.max(120, metrics.advanceWidth + 16))
            placeholderText: "Treść podpisu"
            font.family: block.family
            font.pointSize: block.baseSize
            font.italic: true
            color: "#4a5560"
            onCommitted: function(value) { block.doc.setCaptionText(block.blockId, value) }
            onNavigateUp: function(x) { block.navigateUp(x + row.x + textEdit.x) }
            onNavigateDown: function(x) { block.navigateDown(x + row.x + textEdit.x) }
            onEnterPressed: block.doc.insertAfter(block.blockId, "paragraph", {})
            onActiveFocusChanged: if (activeFocus) block.editor.select(block.blockId)

            TapHandler {
                acceptedButtons: Qt.RightButton
                onTapped: block.editor.contextMenuRequested("caption", { blockId: block.blockId })
            }
        }
    }
}
