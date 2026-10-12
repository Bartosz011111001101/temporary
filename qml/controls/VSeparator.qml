import QtQuick
import ".."

// Pionowy separator grup na paskach narzędzi.
Rectangle {
    implicitWidth: 9
    implicitHeight: Theme.controlHeight - 6
    color: "transparent"
    Rectangle {
        anchors.centerIn: parent
        width: 1
        height: parent.height
        color: Theme.border
    }
}
