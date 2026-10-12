import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QmlWord.Backend
import ".."
import "../controls"

// Lewy panel: drzewo sekcji (nawigacja, zwijanie, przeciąganie) i lista wstawiania.
Rectangle {
    id: panel

    property DocumentModel doc
    property EditorController editor
    property DragController dragCtl
    property OutlineModel outline
    property alias outlineList: outlineList
    property int tab: 0

    color: Theme.panel

    property int dropRow: -1
    property string dropMode: ""
    property bool dropVisible: false

    function focusOutline() {
        tab = 0
        outlineList.forceActiveFocus()
        if (outlineList.currentIndex < 0 && outlineList.count > 0)
            outlineList.currentIndex = 0
    }

    function revealCurrent() {
        var sid = editor.currentSectionId
        if (!sid)
            return
        outline.reveal(sid)
        var r = outline.rowOf(sid)
        if (r >= 0 && !outlineList.activeFocus) {
            outlineList.currentIndex = r
            outlineList.positionViewAtIndex(r, ListView.Contain)
        }
    }

    Connections {
        target: panel.editor
        function onCurrentSectionIdChanged() { Qt.callLater(panel.revealCurrent) }
    }

    // --- przeciąganie sekcji --------------------------------------------------------------
    function updateDrop() {
        if (!dragCtl.active || dragCtl.kind !== "section" || tab !== 0) {
            dropVisible = false
            return
        }
        var p = outlineList.mapFromItem(null, dragCtl.scenePos.x, dragCtl.scenePos.y)
        if (p.x < 0 || p.y < 0 || p.x > outlineList.width || p.y > outlineList.height) {
            if (dropVisible)
                dragCtl.overTarget = false
            dropVisible = false
            return
        }
        var cy = outlineList.contentY + p.y
        var idx = outlineList.indexAt(10, cy)
        if (idx < 0) {
            idx = cy < 0 ? 0 : outlineList.count - 1
        }
        var item = outlineList.itemAtIndex(idx)
        if (!item) {
            dropVisible = false
            return
        }
        var rel = (cy - item.y) / item.height
        var mode
        if (rel < 0.3)
            mode = "before"
        else if (item.hasChildren && item.expanded)
            mode = "into"
        else if (rel > 0.7)
            mode = "after"
        else
            mode = "into"
        var problem = doc.moveSectionProblem(dragCtl.sourceId, item.sectionId, mode)
        dropRow = idx
        dropMode = mode
        var depth = item.depth + (mode === "into" ? 1 : 0)
        sectionLine.x = 8 + depth * 16
        sectionLine.width = outlineList.width - sectionLine.x - 6
        sectionLine.y = outlineList.y + item.y - outlineList.contentY + (mode === "before" ? 0 : item.height) - sectionLine.height / 2
        intoBox.y = outlineList.y + item.y - outlineList.contentY
        intoBox.height = item.height
        sectionLine.allowed = problem === ""
        intoBox.allowed = problem === ""
        dropVisible = problem !== "noop"
        dragCtl.overTarget = problem !== "noop"
        dragCtl.dropAllowed = problem === ""
        dragCtl.problem = problem === "noop" ? "" : problem
    }

    Connections {
        target: panel.dragCtl
        function onScenePosChanged() { panel.updateDrop() }
        function onReleased(cancelled) {
            var ok = panel.dropVisible && !cancelled && panel.dragCtl.dropAllowed && panel.dragCtl.kind === "section"
            panel.dropVisible = false
            if (!ok)
                return
            var target = panel.outline.idAt(panel.dropRow)
            if (target)
                panel.doc.moveSection(panel.dragCtl.sourceId, target, panel.dropMode)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Zakładki
        RowLayout {
            Layout.fillWidth: true
            Layout.margins: 8
            Layout.bottomMargin: 4
            spacing: 4
            Repeater {
                model: ["Sekcje", "Wstaw"]
                delegate: Button {
                    required property string modelData
                    required property int index
                    Layout.fillWidth: true
                    text: modelData
                    checked: panel.tab === index
                    flat: !checked
                    font.pointSize: Theme.fontNormal
                    onClicked: panel.tab = index
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: panel.tab

            // --- Sekcje ---
            ColumnLayout {
                spacing: 0

                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 6
                    Layout.rightMargin: 6
                    spacing: 2
                    IconButton {
                        iconName: "plus"
                        text: "Sekcja"
                        showLabel: true
                        tip: "Dodaj sekcję za bieżącą sekcją"
                        shortcutText: "Ctrl+Shift+N"
                        onClicked: panel.doc.addSection(panel.editor.currentSectionId, false)
                    }
                    IconButton {
                        iconName: "subsection"
                        text: "Podsekcja"
                        showLabel: true
                        enabled: panel.editor.currentSectionId !== ""
                        tip: "Dodaj podsekcję do bieżącej sekcji"
                        onClicked: panel.doc.addSection(panel.editor.currentSectionId, true)
                    }
                    Item { Layout.fillWidth: true }
                    IconButton {
                        iconName: "expandAll"
                        tip: "Rozwiń wszystkie"
                        onClicked: panel.outline.expandAll()
                    }
                    IconButton {
                        iconName: "collapseAll"
                        tip: "Zwiń wszystkie"
                        onClicked: panel.outline.collapseAll()
                    }
                }

                Rectangle { Layout.fillWidth: true; Layout.topMargin: 4; implicitHeight: 1; color: Theme.divider }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ListView {
                        id: outlineList
                        anchors.fill: parent
                        anchors.margins: 4
                        model: panel.outline
                        clip: true
                        spacing: 1
                        keyNavigationEnabled: true
                        activeFocusOnTab: true
                        currentIndex: -1
                        boundsBehavior: Flickable.StopAtBounds
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                        Accessible.role: Accessible.Tree
                        Accessible.name: "Sekcje dokumentu"

                        delegate: OutlineDelegate {
                            doc: panel.doc
                            editor: panel.editor
                            dragCtl: panel.dragCtl
                            outline: panel.outline
                            list: outlineList
                        }

                        Keys.onPressed: function(event) {
                            var item = currentItem
                            if (!item)
                                return
                            var ctrl = (event.modifiers & Qt.ControlModifier) !== 0
                            if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
                                item.goTo()
                            } else if (event.key === Qt.Key_F2) {
                                item.startRename()
                            } else if (ctrl && event.key === Qt.Key_Up) {
                                panel.doc.moveSectionStep(item.sectionId, -1)
                            } else if (ctrl && event.key === Qt.Key_Down) {
                                panel.doc.moveSectionStep(item.sectionId, 1)
                            } else if (ctrl && event.key === Qt.Key_Left) {
                                panel.doc.changeSectionLevel(item.sectionId, -1)
                            } else if (ctrl && event.key === Qt.Key_Right) {
                                panel.doc.changeSectionLevel(item.sectionId, 1)
                            } else if (event.key === Qt.Key_Left) {
                                if (item.hasChildren && item.expanded)
                                    panel.outline.setExpanded(item.sectionId, false)
                                else if (panel.doc.sectionInfo(item.sectionId).parentId)
                                    currentIndex = panel.outline.rowOf(panel.doc.sectionInfo(item.sectionId).parentId)
                            } else if (event.key === Qt.Key_Right) {
                                if (item.hasChildren && !item.expanded)
                                    panel.outline.setExpanded(item.sectionId, true)
                            } else if (event.key === Qt.Key_Delete) {
                                panel.editor.removeSection(item.sectionId)
                            } else if (event.key === Qt.Key_Menu) {
                                panel.editor.contextMenuRequested("section", { sectionId: item.sectionId, delegate: item })
                            } else {
                                return
                            }
                            event.accepted = true
                        }
                        onActiveFocusChanged: if (activeFocus && currentIndex < 0 && count > 0) currentIndex = 0
                    }

                    Column {
                        visible: outlineList.count === 0
                        anchors.centerIn: parent
                        width: parent.width - 32
                        spacing: 10
                        Text {
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.Wrap
                            text: "Dokument nie ma jeszcze sekcji."
                            font.family: Theme.uiFont
                            font.pointSize: Theme.fontNormal
                            color: Theme.textMuted
                        }
                        Text {
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.Wrap
                            text: "Dodaj sekcję przyciskiem powyżej albo ustaw akapitowi styl „Nagłówek”."
                            font.family: Theme.uiFont
                            font.pointSize: Theme.fontSmall
                            color: Theme.textFaint
                        }
                    }

                    DropLine {
                        id: sectionLine
                        visible: panel.dropVisible && panel.dropMode !== "into"
                    }
                    Rectangle {
                        id: intoBox
                        property bool allowed: true
                        visible: panel.dropVisible && panel.dropMode === "into"
                        x: 4
                        width: outlineList.width
                        color: allowed ? Qt.rgba(0.16, 0.36, 0.62, 0.10) : Qt.rgba(0.7, 0.15, 0.12, 0.10)
                        border.width: 2
                        border.color: allowed ? Theme.accent : Theme.danger
                        radius: Theme.radius
                        z: 50
                    }
                }

                Text {
                    Layout.fillWidth: true
                    Layout.margins: 8
                    wrapMode: Text.Wrap
                    visible: outlineList.count > 0
                    text: "Przeciągnij sekcję: górna część wiersza – przed, środek – do środka, dół – za. "
                          + "Klawiatura: Ctrl+↑/↓ kolejność, Ctrl+←/→ poziom, F2 nazwa."
                    font.family: Theme.uiFont
                    font.pointSize: Theme.fontSmall - 0.5
                    color: Theme.textFaint
                }
            }

            // --- Wstaw ---
            InsertPanel {
                doc: panel.doc
                editor: panel.editor
                dragCtl: panel.dragCtl
            }
        }
    }

    Rectangle {
        anchors.right: parent.right
        width: 1
        height: parent.height
        color: Theme.border
    }
}
