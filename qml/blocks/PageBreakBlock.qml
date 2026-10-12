import QtQuick
import QmlWord.Backend
import ".."

// Podział strony: koniec bieżącej kartki, odstęp i początek następnej.
FocusScope {
    id: block

    property DocumentModel doc
    property EditorController editor
    property string blockId: ""
    property real contentWidth: 600
    property real pageWidth: 794
    property real marginLeft: 94
    property real marginTop: 94
    property real marginBottom: 94
    readonly property real gap: 28
    readonly property bool isCurrent: editor && editor.currentBlockId === blockId

    signal navigateUp(real x)
    signal navigateDown(real x)

    implicitHeight: marginBottom + gap + marginTop
    activeFocusOnTab: true
    Accessible.role: Accessible.Separator
    Accessible.name: "Podział strony"

    function focusAt(start, end) { forceActiveFocus() }
    function focusFromAbove(x) { forceActiveFocus() }
    function focusFromBelow(x) { forceActiveFocus() }

    onActiveFocusChanged: if (activeFocus && editor) editor.select(blockId)

    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Delete || event.key === Qt.Key_Backspace) {
            doc.removeBlock(blockId)
            event.accepted = true
        } else if (event.key === Qt.Key_Up) {
            navigateUp(0)
            event.accepted = true
        } else if (event.key === Qt.Key_Down) {
            navigateDown(0)
            event.accepted = true
        }
    }

    // Dół poprzedniej strony
    Rectangle {
        x: -block.marginLeft
        width: block.pageWidth
        height: block.marginBottom
        color: Theme.paper
        Rectangle { width: 1; height: parent.height; color: Theme.border }
        Rectangle { x: parent.width - 1; width: 1; height: parent.height; color: Theme.border }
        Rectangle { y: parent.height - 1; width: parent.width; height: 1; color: Theme.border }
    }

    // Odstęp między stronami
    Item {
        y: block.marginBottom
        x: -block.marginLeft
        width: block.pageWidth
        height: block.gap
        Rectangle {
            anchors.centerIn: parent
            width: tag.implicitWidth + 16
            height: 18
            radius: 9
            color: block.isCurrent || block.activeFocus ? Theme.accentSoft : "#d5d9de"
            border.width: block.activeFocus ? 2 : 0
            border.color: Theme.focusRing
            Text {
                id: tag
                anchors.centerIn: parent
                text: "Podział strony"
                font.family: Theme.uiFont
                font.pointSize: Theme.fontSmall
                color: block.isCurrent ? Theme.accent : Theme.textMuted
            }
        }
    }

    // Góra następnej strony
    Rectangle {
        y: block.marginBottom + block.gap
        x: -block.marginLeft
        width: block.pageWidth
        height: block.marginTop
        color: Theme.paper
        Rectangle { width: parent.width; height: 1; color: Theme.border }
        Rectangle { width: 1; height: parent.height; color: Theme.border }
        Rectangle { x: parent.width - 1; width: 1; height: parent.height; color: Theme.border }
    }

    TapHandler {
        onTapped: block.forceActiveFocus()
    }
    TapHandler {
        acceptedButtons: Qt.RightButton
        onTapped: {
            block.forceActiveFocus()
            block.editor.contextMenuRequested("block", { blockId: block.blockId })
        }
    }
}
