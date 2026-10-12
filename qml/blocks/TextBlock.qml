import QtQuick
import QmlWord.Backend
import ".."

// Akapit, tytuł lub nagłówek sekcji (z opcjonalnym opisem pod nagłówkiem), punkty list,
// wcięcia, obramowanie i cieniowanie akapitu oraz zaznaczenie obejmujące wiele bloków.
Item {
    id: block

    property DocumentModel doc
    property EditorController editor
    property string blockId: ""
    property var blockData: ({})
    property string listMarker: ""
    property int borderJoin: 0           // 1 = ta sama ramka co blok wyżej, 2 = co blok niżej
    property string rangeRole: ""        // "first" | "last" | "inner" | ""
    property real contentWidth: 600
    // Obraz opływany tekstem obok tego akapitu: strona i zajęta szerokość (px strony).
    property string floatSide: ""
    property real floatWidth: 0

    readonly property bool isHeading: blockData.type === "heading"
    readonly property string styleKey: isHeading ? "h" + blockData.level : (blockData.style || "body")
    readonly property var styleFont: doc ? doc.textStyles[styleKey] || ({}) : ({})
    readonly property var para: blockData.para || ({})
    readonly property string listType: isHeading ? "none" : (para.list || "none")
    readonly property real leftPx: (listType === "none" ? (para.indent || 0) * Theme.indentStep : (para.indent || 0) * Theme.indentStep)
                                   + (para.leftMm || 0) * Theme.pxPerMm
    readonly property real rightPx: (para.rightMm || 0) * Theme.pxPerMm
    readonly property real markerWidth: listType !== "none" ? Math.max(24, markerMetrics.advanceWidth + 10) : 0
    readonly property real topPad: (para.spaceBefore || 0) * Theme.pxPerPt
    readonly property real bottomPad: (para.spaceAfter || 0) * Theme.pxPerPt
    readonly property var border: para.border || null
    readonly property bool framed: (border !== null && border.kind !== "none") || !!para.shading
    readonly property real floatInsetLeft: floatSide === "left" ? floatWidth : 0
    readonly property real floatInsetRight: floatSide === "right" ? floatWidth : 0
    property bool showDescription: (blockData.description || "") !== ""
    property alias textEditor: edit

    signal navigateUp(real x)
    signal navigateDown(real x)

    implicitHeight: topPad + column.implicitHeight + bottomPad

    function focusAt(start, end) { edit.focusAt(start, end) }
    function focusFromAbove(x) { edit.focusAtX(x - column.x, false) }
    function focusFromBelow(x) {
        if (descriptionEditor.visible) descriptionEditor.focusAt(descriptionEditor.length, descriptionEditor.length)
        else edit.focusAtX(x - column.x, true)
    }
    function startDescription() {
        showDescription = true
        Qt.callLater(function() { descriptionEditor.forceActiveFocus() })
    }
    function positionAtItem(item, x, y) {
        var p = edit.mapFromItem(item, x, y)
        return edit.positionAt(p.x, p.y)
    }

    Component.onCompleted: {
        edit.load(blockData.runs, para)
        descriptionEditor.setTextSilently(blockData.description || "")
        applyRange()
    }

    Connections {
        target: block.doc
        function onBlockReset(id) {
            if (id !== block.blockId)
                return
            var d = block.doc.blockData(block.blockId)
            edit.reload(d.runs, d.para)
            descriptionEditor.setTextSilently(d.description || "")
            block.showDescription = (d.description || "") !== "" || descriptionEditor.activeFocus
            block.applyRange()
        }
    }

    // --- zaznaczenie obejmujące wiele bloków ----------------------------------------------
    function applyRange() {
        if (!editor)
            return
        var r = editor.range
        var len = edit.length
        if (rangeRole === "inner") {
            edit.select(0, len)
        } else if (rangeRole === "first" && r) {
            if (editor.rangeFocus.blockId === blockId) edit.select(len, r.firstPos)
            else edit.select(r.firstPos, len)
        } else if (rangeRole === "last" && r) {
            edit.select(0, r.lastPos)
        } else if (editor.activeEditor !== edit && edit.selectionStart !== edit.selectionEnd) {
            edit.deselect()
        }
    }
    onRangeRoleChanged: applyRange()
    Connections {
        target: block.editor
        function onRangeApplied() { block.applyRange() }
    }

    TextMetrics {
        id: markerMetrics
        font: edit.font
        text: block.listMarker
    }

    // --- obramowanie i cieniowanie ----------------------------------------------------------
    Item {
        id: frame
        visible: block.framed
        readonly property bool joinTop: (block.borderJoin & 1) !== 0
        readonly property bool joinBottom: (block.borderJoin & 2) !== 0
        readonly property string kind: block.border ? block.border.kind : "none"
        readonly property color lineColor: block.border ? block.border.color : "#5b6570"
        readonly property real lineWidth: Math.max(1, (block.border ? block.border.width : 0.75) * Theme.pxPerPt)
        x: block.leftPx + block.floatInsetLeft - 6
        y: joinTop ? 0 : Math.max(0, block.topPad - 4)
        width: block.contentWidth - block.leftPx - block.rightPx - block.floatInsetLeft - block.floatInsetRight + 12
        height: block.height - y - (joinBottom ? 0 : Math.max(0, block.bottomPad - 4))
        z: -1

        Rectangle {
            anchors.fill: parent
            color: block.para.shading || "transparent"
        }
        Rectangle {   // góra
            visible: !frame.joinTop && (frame.kind === "box" || frame.kind === "top" || frame.kind === "topBottom")
            width: parent.width; height: frame.lineWidth; color: frame.lineColor
        }
        Rectangle {   // dół
            visible: !frame.joinBottom && (frame.kind === "box" || frame.kind === "bottom" || frame.kind === "topBottom")
            y: parent.height - height; width: parent.width; height: frame.lineWidth; color: frame.lineColor
        }
        Rectangle {   // lewa
            visible: frame.kind === "box" || frame.kind === "left"
            width: frame.kind === "left" ? frame.lineWidth * 2.5 : frame.lineWidth; height: parent.height; color: frame.lineColor
        }
        Rectangle {   // prawa
            visible: frame.kind === "box"
            x: parent.width - width; width: frame.lineWidth; height: parent.height; color: frame.lineColor
        }
    }

    Text {
        visible: block.listType !== "none"
        x: block.leftPx + block.floatInsetLeft
        y: block.topPad
        width: block.markerWidth - 8
        horizontalAlignment: Text.AlignRight
        text: block.listMarker
        font.family: edit.font.family
        font.pointSize: edit.font.pointSize
        color: edit.color
    }

    Column {
        id: column
        x: block.leftPx + block.markerWidth + block.floatInsetLeft
        y: block.topPad
        width: Math.max(40, block.contentWidth - x - block.rightPx - block.floatInsetRight)
        spacing: 2

        RichTextEditor {
            id: edit
            width: parent.width
            doc: block.doc
            editor: block.editor
            blockId: block.blockId
            styleFont: block.styleFont
            listItem: block.listType !== "none"
            tabStops: block.para.tabs || []
            placeholderText: block.isHeading ? "Tytuł sekcji" : block.styleKey === "title" ? "Tytuł dokumentu" : "Zacznij pisać…"
            placeholderAlways: block.isHeading || block.styleKey === "title"
            onNavigateUp: function(x) { block.navigateUp(x + column.x) }
            onNavigateDown: function(x) {
                if (descriptionEditor.visible) descriptionEditor.focusAt(0, 0)
                else block.navigateDown(x + column.x)
            }
            onTabPressed: function(backwards) {
                if (block.listType !== "none")
                    block.doc.changeIndent(block.blockId, backwards ? -1 : 1)
                else if (!backwards)
                    insert(cursorPosition, "\t")
            }
        }

        PlainTextEditor {
            id: descriptionEditor
            visible: block.isHeading && (block.showDescription || activeFocus)
            width: parent.width
            doc: block.doc
            placeholderText: "Krótki opis sekcji (nie jest podpisem elementu)"
            font.family: block.styleFont.family || "Calibri"
            font.pointSize: (block.doc ? block.doc.meta.fontSize : 11) * 0.92
            font.italic: true
            color: "#5b6670"
            horizontalAlignment: block.para.align === "center" ? TextEdit.AlignHCenter
                               : block.para.align === "right" ? TextEdit.AlignRight : TextEdit.AlignLeft
            onCommitted: function(value) { block.doc.setDescription(block.blockId, value) }
            onNavigateUp: edit.focusAt(edit.length, edit.length)
            onNavigateDown: function(x) { block.navigateDown(x + column.x) }
            onEnterPressed: block.doc.insertAfter(block.blockId, "paragraph", {})
            onActiveFocusChanged: {
                if (activeFocus)
                    block.editor.select(block.blockId)
                else if (length === 0)
                    block.showDescription = false
            }
        }
    }
}
