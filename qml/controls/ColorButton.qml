import QtQuick
import QtQuick.Controls
import ".."

// Przycisk koloru (tekst/zakreślenie): ikona z paskiem bieżącego koloru i paleta w okienku.
IconButton {
    id: btn

    property var colors: Theme.textColors
    property string currentColor: ""
    property string lastColor: colors.length ? colors[0] : "#000000"
    property string noneLabel: "Automatyczny"
    signal colorPicked(string color)

    implicitWidth: 40
    rightPadding: 16
    focusPolicy: Qt.NoFocus

    onClicked: popup.opened ? popup.close() : popup.open()

    Rectangle {
        x: 8
        y: parent.height - 8
        width: 16
        height: 3
        radius: 1
        color: btn.currentColor || btn.lastColor
        border.width: btn.currentColor ? 0 : 1
        border.color: Theme.borderStrong
    }

    Text {
        anchors.right: parent.right
        anchors.rightMargin: 4
        anchors.verticalCenter: parent.verticalCenter
        text: "▾"
        font.pointSize: 7
        color: Theme.textMuted
    }

    Popup {
        id: popup
        y: btn.height + 2
        padding: 10
        focus: true
        background: Rectangle {
            color: Theme.paper
            border.color: Theme.border
            radius: Theme.radius
        }
        contentItem: ColorGrid {
            colors: btn.colors
            current: btn.currentColor
            noneLabel: btn.noneLabel
            onPicked: function(color) {
                if (color)
                    btn.lastColor = color
                popup.close()
                btn.colorPicked(color)
            }
        }
    }
}
