import QtQuick
import QtQuick.Controls
import QtQuick.Controls.impl
import ".."

// Przycisk paska narzędzi: ikona SVG albo znak (B, I, U…), podpowiedź ze skrótem.
ToolButton {
    id: btn

    property string iconName: ""
    property string glyph: ""
    property font glyphFont: Qt.font({ family: "Segoe UI", pointSize: 10.5 })
    property string tip: ""
    property string shortcutText: ""
    property bool showLabel: false
    property bool danger: false
    property color tint: !enabled ? Theme.textFaint
                        : danger && hovered ? Theme.danger
                        : checked ? Theme.accent : Theme.text

    implicitWidth: Math.max(Theme.controlHeight, contentRow.implicitWidth + leftPadding + rightPadding)
    implicitHeight: Theme.controlHeight
    leftPadding: showLabel ? 8 : 6
    rightPadding: showLabel ? 10 : 6
    topPadding: 0
    bottomPadding: 0
    focusPolicy: Qt.TabFocus
    hoverEnabled: true

    Accessible.name: tip || text || glyph
    ToolTip.visible: hovered && tip !== "" && !pressed
    ToolTip.delay: 600
    ToolTip.text: tip + (shortcutText ? "   " + shortcutText : "")

    contentItem: Item {
        implicitWidth: contentRow.implicitWidth
        implicitHeight: contentRow.implicitHeight
        Row {
            id: contentRow
            anchors.centerIn: parent
            spacing: 6
            IconImage {
                visible: btn.iconName !== ""
                anchors.verticalCenter: parent.verticalCenter
                source: btn.iconName ? Qt.resolvedUrl("../icons/" + btn.iconName + ".svg") : ""
                sourceSize: Qt.size(Theme.iconSize, Theme.iconSize)
                color: btn.tint
            }
            Text {
                visible: btn.glyph !== ""
                anchors.verticalCenter: parent.verticalCenter
                text: btn.glyph
                font: btn.glyphFont
                color: btn.tint
            }
            Text {
                visible: btn.showLabel && btn.text !== ""
                anchors.verticalCenter: parent.verticalCenter
                text: btn.text
                font.family: Theme.uiFont
                font.pointSize: Theme.fontNormal
                color: btn.tint
            }
        }
    }

    background: Rectangle {
        implicitWidth: Theme.controlHeight
        implicitHeight: Theme.controlHeight
        radius: Theme.radius
        color: btn.down ? Theme.pressed
             : btn.checked ? Theme.accentSoft
             : btn.hovered && btn.enabled ? Theme.hover : "transparent"
        border.width: btn.visualFocus ? 2 : 0
        border.color: Theme.focusRing
    }
}
