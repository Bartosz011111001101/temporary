import QtQuick
import QtQuick.Controls
import ".."

// Siatka próbek kolorów z opcją „bez koloru”.
Column {
    id: grid

    property var colors: []
    property string current: ""
    property string noneLabel: "Automatyczny"
    signal picked(string color)

    spacing: 6

    Button {
        width: parent.width
        text: grid.noneLabel
        flat: true
        focusPolicy: Qt.TabFocus
        onClicked: grid.picked("")
    }

    Grid {
        columns: 6
        spacing: 4
        Repeater {
            model: grid.colors
            delegate: AbstractButton {
                required property string modelData
                width: 24
                height: 24
                focusPolicy: Qt.TabFocus
                hoverEnabled: true
                Accessible.name: modelData
                ToolTip.visible: hovered
                ToolTip.text: modelData
                ToolTip.delay: 500
                background: Rectangle {
                    radius: 3
                    color: modelData
                    border.width: parent.visualFocus || grid.current === modelData ? 2 : 1
                    border.color: parent.visualFocus || grid.current === modelData ? Theme.focusRing
                                  : parent.hovered ? Theme.borderStrong : Qt.darker(modelData, 1.15)
                }
                onClicked: grid.picked(modelData)
            }
        }
    }
}
