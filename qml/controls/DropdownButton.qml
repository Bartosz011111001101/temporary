import QtQuick
import QtQuick.Controls
import ".."

// Przycisk paska narzędzi otwierający menu (np. style list, wielkość liter, wklejanie).
IconButton {
    id: btn

    property Menu menu
    property bool arrowOnly: false

    implicitWidth: arrowOnly ? 16 : Math.max(Theme.controlHeight + 10, implicitContentWidth + 22)
    rightPadding: arrowOnly ? 0 : 16
    leftPadding: arrowOnly ? 0 : 6

    onClicked: if (menu) menu.popup(btn, 0, btn.height)

    Text {
        anchors.right: parent.right
        anchors.rightMargin: btn.arrowOnly ? 4 : 4
        anchors.verticalCenter: parent.verticalCenter
        text: "▾"
        font.pointSize: 7
        color: btn.enabled ? Theme.textMuted : Theme.textFaint
    }
}
