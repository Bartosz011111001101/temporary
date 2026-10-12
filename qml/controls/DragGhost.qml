import QtQuick
import QtQuick.Controls.impl
import ".."

// Etykieta podążająca za kursorem podczas przeciągania.
Rectangle {
    id: ghost

    property DragController drag

    visible: drag && drag.active
    x: drag ? drag.scenePos.x + 14 : 0
    y: drag ? drag.scenePos.y + 10 : 0
    z: 1000
    radius: 5
    color: !drag || !drag.overTarget ? "#f0f2f5" : drag.dropAllowed ? Theme.accentSoft : Theme.dangerSoft
    border.color: !drag || !drag.overTarget ? Theme.borderStrong : drag.dropAllowed ? Theme.accent : Theme.danger
    implicitWidth: Math.min(row.implicitWidth + 20, 340)
    implicitHeight: row.implicitHeight + 12
    opacity: 0.95

    Column {
        id: row
        anchors.centerIn: parent
        width: Math.min(implicitWidth, 320)
        spacing: 2
        Row {
            spacing: 6
            IconImage {
                source: Qt.resolvedUrl("../icons/grip.svg")
                sourceSize: Qt.size(14, 14)
                color: Theme.textMuted
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: ghost.drag ? ghost.drag.label : ""
                elide: Text.ElideRight
                width: Math.min(implicitWidth, 290)
                font.family: Theme.uiFont
                font.pointSize: Theme.fontNormal
                color: Theme.text
            }
        }
        Text {
            visible: ghost.drag && ghost.drag.overTarget && !ghost.drag.dropAllowed && ghost.drag.problem !== ""
            text: ghost.drag ? ghost.drag.problem : ""
            width: 300
            wrapMode: Text.Wrap
            font.family: Theme.uiFont
            font.pointSize: Theme.fontSmall
            color: Theme.danger
        }
    }
}
