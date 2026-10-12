import QtQuick
import QtQuick.Controls
import ".."

// Krótki komunikat u dołu okna (np. odrzucone przeniesienie, wykonany eksport).
Rectangle {
    id: toast

    property string message: ""

    function show(text) {
        message = text
        opacity = 1
        hideTimer.restart()
    }

    visible: opacity > 0
    opacity: 0
    radius: 6
    color: "#2b3138"
    implicitWidth: Math.min(label.implicitWidth + 32, 560)
    implicitHeight: label.implicitHeight + 18
    Behavior on opacity { NumberAnimation { duration: 160 } }
    Accessible.role: Accessible.AlertMessage
    Accessible.name: message

    Text {
        id: label
        anchors.centerIn: parent
        width: Math.min(implicitWidth, 528)
        text: toast.message
        color: "#ffffff"
        wrapMode: Text.Wrap
        font.family: Theme.uiFont
        font.pointSize: Theme.fontNormal
    }

    Timer {
        id: hideTimer
        interval: 3500
        onTriggered: toast.opacity = 0
    }

    MouseArea {
        anchors.fill: parent
        onClicked: toast.opacity = 0
    }
}
