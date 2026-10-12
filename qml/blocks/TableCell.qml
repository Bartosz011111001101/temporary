import QtQuick
import QtQuick.Controls
import QmlWord.Backend
import ".."

// Pojedyncza komórka tabeli (kotwica scalenia) z własnym edytorem tekstu.
// Wygląd (tło, krawędzie, pogrubienie) pochodzi ze stylu tabeli wyliczonego w modelu.
Item {
    id: cell

    property DocumentModel doc
    property EditorController editor
    property string blockId: ""
    property int row: 0
    property int col: 0
    property int rowSpan: 1
    property int colSpan: 1
    property var cellData: ({})
    property var look: null
    property bool selectedCell: false
    property real padding: 5
    readonly property bool hasFormula: !!cellData.formula
    readonly property real naturalHeight: edit.implicitHeight + 2 * padding
    property alias textEditor: edit

    signal tabPressed(bool backwards)
    signal navigateUp(real x)
    signal navigateDown(real x)
    signal shiftClicked()

    function load(data) {
        cellData = data || {}
        edit.load(cellData.runs || [], { align: cellData.align || "left", lineHeight: 1.0 })
    }
    function reload(data) {
        cellData = data || {}
        edit.reload(cellData.runs || [], { align: cellData.align || "left", lineHeight: 1.0 })
    }
    function focusAt(start, end) { edit.focusAt(start, end) }

    function edgeWidth(side) {
        return cell.look && cell.look[side] ? cell.look[side].w * Theme.pxPerPt : 0
    }
    function edgeColor(side) {
        return cell.look && cell.look[side] ? cell.look[side].c : "#9aa3ad"
    }

    Rectangle {
        anchors.fill: parent
        color: cell.look && cell.look.background ? cell.look.background : "transparent"
    }

    Rectangle {
        anchors.fill: parent
        visible: cell.selectedCell
        color: Qt.rgba(0.16, 0.36, 0.62, 0.14)
        border.width: 1
        border.color: Theme.accent
        z: 2
    }

    // Krawędzie: lewa/górna rysowane o piksel na zewnątrz, by pokrywać się z krawędzią sąsiada.
    Rectangle { visible: cell.edgeWidth("top") > 0; x: -1; y: -1; width: parent.width + 1; height: Math.max(1, cell.edgeWidth("top")); color: cell.edgeColor("top"); z: 3 }
    Rectangle { visible: cell.edgeWidth("left") > 0; x: -1; y: -1; width: Math.max(1, cell.edgeWidth("left")); height: parent.height + 1; color: cell.edgeColor("left"); z: 3 }
    Rectangle { visible: cell.edgeWidth("right") > 0; x: parent.width - width; y: -1; width: Math.max(1, cell.edgeWidth("right")); height: parent.height + 1; color: cell.edgeColor("right"); z: 3 }
    Rectangle { visible: cell.edgeWidth("bottom") > 0; x: -1; y: parent.height - height; width: parent.width + 1; height: Math.max(1, cell.edgeWidth("bottom")); color: cell.edgeColor("bottom"); z: 3 }

    RichTextEditor {
        id: edit
        x: cell.padding
        y: cell.padding
        width: Math.max(10, cell.width - 2 * cell.padding)
        doc: cell.doc
        editor: cell.editor
        blockId: cell.blockId
        cellRow: cell.row
        cellCol: cell.col
        formulaCell: cell.hasFormula
        styleFont: {
            var base = cell.doc ? cell.doc.textStyles["body"] : {}
            return { family: base.family, pointSize: base.pointSize, bold: cell.look ? cell.look.bold : false,
                     italic: false, color: cell.look && cell.look.color ? cell.look.color : base.color }
        }
        onTabPressed: function(backwards) { cell.tabPressed(backwards) }
        onNavigateUp: function(x) { cell.navigateUp(x) }
        onNavigateDown: function(x) { cell.navigateDown(x) }
    }

    // Znacznik formuły
    Rectangle {
        visible: cell.hasFormula
        x: 2
        y: 2
        width: fx.implicitWidth + 6
        height: fx.implicitHeight + 2
        radius: 2
        color: Theme.accentSoft
        z: 4
        Text {
            id: fx
            anchors.centerIn: parent
            text: "fx"
            font.italic: true
            font.pointSize: 6.5
            color: Theme.accent
        }
        ToolTip.visible: fxHover.hovered
        ToolTip.text: cell.cellData.formula || ""
        HoverHandler { id: fxHover }
    }

    TapHandler {
        acceptedModifiers: Qt.ShiftModifier
        onTapped: cell.shiftClicked()
    }
}
