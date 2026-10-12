import QtQuick
import QtQuick.Controls
import QtQuick.Controls.impl
import QtQuick.Layouts
import ".."

// Przypomnienie o niezapisanych zmianach (pojawia się po dłuższej pracy bez zapisu).
Rectangle {
    id: banner

    property int minutes: 0
    signal saveRequested()
    signal dismissed()

    implicitHeight: 36
    color: Theme.warningSoft
    Accessible.role: Accessible.AlertMessage
    Accessible.name: label.text

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: "#ecd9a0"
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 8
        spacing: 8
        IconImage {
            source: Qt.resolvedUrl("../icons/warning.svg")
            sourceSize: Qt.size(16, 16)
            color: Theme.warning
        }
        Text {
            id: label
            Layout.fillWidth: true
            elide: Text.ElideRight
            text: "Masz niezapisane zmiany od " + banner.minutes + " min. Kopia robocza chroni przed awarią, ale nie zastępuje zapisu."
            font.family: Theme.uiFont
            font.pointSize: Theme.fontNormal
            color: Theme.text
        }
        Button {
            text: "Zapisz teraz"
            highlighted: true
            onClicked: banner.saveRequested()
        }
        Button {
            text: "Przypomnij później"
            flat: true
            onClicked: banner.dismissed()
        }
    }
}
