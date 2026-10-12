import QtQuick
import QtQuick.Controls
import QtQuick.Controls.impl
import QmlWord.Backend
import ".."

// Wiersz drzewa sekcji: wcięcie z liniami poziomów, zwijanie, numer, nazwa, akcje i przeciąganie.
Rectangle {
    id: row

    required property int index
    required property string sectionId
    required property string title
    required property int level
    required property int depth
    required property string number
    required property bool hasChildren
    required property bool expanded
    required property int blockCount

    property DocumentModel doc
    property EditorController editor
    property DragController dragCtl
    property OutlineModel outline
    property ListView list
    property bool renaming: false
    readonly property bool isCurrentSection: editor && editor.currentSectionId === sectionId
    readonly property bool keyboardCurrent: list && list.currentIndex === index && list.activeFocus
    readonly property real indent: 8 + depth * 16

    width: list ? list.width : 240
    height: 30
    color: dragHandler.active ? Theme.accentSofter
         : isCurrentSection ? Theme.selected
         : hover.hovered ? Theme.hover : "transparent"
    radius: Theme.radius
    border.width: keyboardCurrent ? 2 : 0
    border.color: Theme.focusRing
    Accessible.role: Accessible.TreeItem
    Accessible.name: number + " " + title

    function goTo() {
        list.currentIndex = index
        doc.requestFocus(sectionId, 0, 0, -1, -1)
    }

    function startRename() {
        renaming = true
        renameField.text = title === "(bez tytułu)" ? "" : title
        renameField.forceActiveFocus()
        renameField.selectAll()
    }

    // Linie poziomów zagnieżdżenia
    Repeater {
        model: row.depth
        delegate: Rectangle {
            required property int index
            x: 8 + index * 16 + 7
            width: 1
            height: row.height
            color: Theme.border
        }
    }

    HoverHandler {
        id: hover
    }

    Item {
        id: chevron
        x: row.indent
        width: 16
        height: parent.height
        visible: row.hasChildren
        IconImage {
            anchors.centerIn: parent
            source: Qt.resolvedUrl("../icons/" + (row.expanded ? "chevronDown" : "chevronRight") + ".svg")
            sourceSize: Qt.size(12, 12)
            color: Theme.textMuted
        }
        TapHandler {
            onTapped: row.outline.toggle(row.sectionId)
        }
    }

    Rectangle {
        id: badge
        x: chevron.x + 18
        anchors.verticalCenter: parent.verticalCenter
        width: 22
        height: 16
        radius: 3
        color: row.level === 1 ? Theme.accent : row.level === 2 ? "#6b8fc2" : "#c3cfde"
        Text {
            anchors.centerIn: parent
            text: "H" + row.level
            font.family: Theme.uiFont
            font.pointSize: 7
            font.bold: true
            color: row.level <= 2 ? "white" : Theme.text
        }
    }

    Text {
        id: label
        visible: !row.renaming
        anchors.verticalCenter: parent.verticalCenter
        x: badge.x + badge.width + 6
        width: actions.x - x - 4
        elide: Text.ElideRight
        textFormat: Text.PlainText
        text: row.number + "  " + row.title
        font.family: Theme.uiFont
        font.pointSize: Theme.fontNormal
        font.weight: row.depth === 0 ? Font.DemiBold : Font.Normal
        color: row.title === "(bez tytułu)" ? Theme.textFaint : Theme.text
    }

    TextField {
        id: renameField
        visible: row.renaming
        x: label.x
        width: row.width - x - 6
        anchors.verticalCenter: parent.verticalCenter
        height: 24
        font.pointSize: Theme.fontNormal
        placeholderText: "Nazwa sekcji"
        onAccepted: {
            row.doc.setHeadingTitle(row.sectionId, text)
            row.renaming = false
            row.list.forceActiveFocus()
        }
        Keys.onEscapePressed: {
            row.renaming = false
            row.list.forceActiveFocus()
        }
        onActiveFocusChanged: if (!activeFocus) row.renaming = false
    }

    Row {
        id: actions
        anchors.right: parent.right
        anchors.rightMargin: 4
        anchors.verticalCenter: parent.verticalCenter
        spacing: 0
        visible: (hover.hovered || row.isCurrentSection) && !row.renaming
        width: visible ? implicitWidth : 0

        Item {
            width: 22
            height: 22
            IconImage {
                anchors.centerIn: parent
                source: Qt.resolvedUrl("../icons/plus.svg")
                sourceSize: Qt.size(14, 14)
                color: addHover.hovered ? Theme.accent : Theme.textMuted
            }
            HoverHandler { id: addHover }
            ToolTip.visible: addHover.hovered
            ToolTip.delay: 500
            ToolTip.text: "Dodaj podsekcję"
            TapHandler { onTapped: row.doc.addSection(row.sectionId, true) }
        }
        Item {
            width: 22
            height: 22
            IconImage {
                anchors.centerIn: parent
                source: Qt.resolvedUrl("../icons/grip.svg")
                sourceSize: Qt.size(14, 14)
                color: gripHover.hovered ? Theme.accent : Theme.textFaint
            }
            HoverHandler { id: gripHover; cursorShape: Qt.OpenHandCursor }
            ToolTip.visible: gripHover.hovered
            ToolTip.delay: 500
            ToolTip.text: "Przeciągnij, aby przenieść sekcję"
        }
    }

    TapHandler {
        acceptedButtons: Qt.LeftButton
        onTapped: if (!row.renaming) row.goTo()
        onDoubleTapped: row.startRename()
    }
    TapHandler {
        acceptedButtons: Qt.RightButton
        onTapped: {
            row.list.currentIndex = row.index
            row.editor.contextMenuRequested("section", { sectionId: row.sectionId, delegate: row })
        }
    }

    DragHandler {
        id: dragHandler
        target: null
        dragThreshold: 6
        enabled: !row.renaming
        onActiveChanged: {
            if (active) {
                row.doc.flush()
                row.dragCtl.begin("section", row.sectionId,
                                  "Sekcja " + row.number + ": " + row.title + (row.blockCount > 1 ? " · " + row.blockCount + " el." : ""))
                row.dragCtl.move(centroid.scenePosition)
            } else {
                row.dragCtl.finish(false)
            }
        }
        onCentroidChanged: if (active) row.dragCtl.move(centroid.scenePosition)
    }
}
