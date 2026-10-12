import QtQuick
import QtQuick.Controls
import ".."

// Pojedynczy przycisk symbolu w oknie symboli.
AbstractButton {
    id: cell

    property string symbol: ""
    signal picked()

    width: 34
    height: 34
    focusPolicy: Qt.TabFocus
    hoverEnabled: true
    Accessible.name: symbol
    ToolTip.visible: hovered
    ToolTip.delay: 600
    ToolTip.text: "U+" + symbol.charCodeAt(0).toString(16).toUpperCase()

    onClicked: picked()

    background: Rectangle {
        radius: 3
        color: cell.down ? Theme.pressed : cell.hovered ? Theme.accentSoft : Theme.paper
        border.width: cell.visualFocus ? 2 : 1
        border.color: cell.visualFocus ? Theme.focusRing : Theme.border
    }
    contentItem: Text {
        text: cell.symbol
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.pointSize: 13
        color: Theme.text
    }
}
