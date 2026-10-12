import QtQuick
import ".."

// Wskaźnik miejsca upuszczenia: linia z kropką; czerwona, gdy upuszczenie jest niedozwolone.
Item {
    id: line

    property bool allowed: true
    readonly property color tone: allowed ? Theme.accent : Theme.danger

    height: 10
    z: 500

    Rectangle {
        anchors.verticalCenter: parent.verticalCenter
        x: 0
        width: 10
        height: 10
        radius: 5
        color: "transparent"
        border.width: 2
        border.color: line.tone
    }
    Rectangle {
        anchors.verticalCenter: parent.verticalCenter
        x: 9
        width: parent.width - 9
        height: 2.5
        radius: 1
        color: line.tone
    }
}
