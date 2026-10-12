import QtQuick
import QtQuick.Controls
import QmlWord.Backend
import ".."
import "../blocks"
import "../controls"

// Centralny obszar: dokument jako ciąg bloków na stronie (tryb ciągłego przewijania
// z widocznymi marginesami i podziałami stron).
Item {
    id: docView

    property DocumentModel doc
    property EditorController editor
    property DragController dragCtl
    property real zoom: 1.0
    signal zoomRequested(real value)

    readonly property var page: doc ? doc.page : ({})
    readonly property real pageWidth: (page.widthMm || 210) * Theme.pxPerMm
    readonly property real marginLeft: (page.marginLeft || 25) * Theme.pxPerMm
    readonly property real marginRight: (page.marginRight || 25) * Theme.pxPerMm
    readonly property real marginTop: (page.marginTop || 25) * Theme.pxPerMm
    readonly property real marginBottom: (page.marginBottom || 25) * Theme.pxPerMm
    readonly property real paperX: Math.max(16, (list.contentWidth - pageWidth * zoom) / 2)

    property int dropIndex: -1
    property bool dropVisible: false

    // --- opływanie obrazów ------------------------------------------------------------------
    // Zwiększany po każdej zmianie układu – wymusza ponowne policzenie pozycji obok obrazów.
    property int floatTick: 0
    function bumpFloats() { floatTick++ }

    // Pływający obraz powyżej bloku `index` (o górnej krawędzi `y`), obok którego blok leży.
    function floatFor(index, y) {
        if (floatTick < 0)
            return null
        for (var k = index - 1; k >= 0 && k >= index - 12; --k) {
            var it = list.itemAtIndex(k)
            if (!it)
                return null
            if (it.floatBox) {
                var bottom = it.y + it.floatBox.height * zoom
                return y < bottom - 1 ? { side: it.floatBox.side, width: it.floatBox.width, bottom: bottom } : null
            }
            if (it.blockType !== "paragraph" && it.blockType !== "heading" && it.blockType !== "caption")
                return null
        }
        return null
    }

    // --- zaznaczanie myszą przez wiele bloków ------------------------------------------------
    property string pressBlockId: ""
    property var pressAnchor: null

    function delegateAtScene(sx, sy) {
        var p = list.mapFromItem(null, sx, sy)
        var idx = list.indexAt(10, list.contentY + p.y)
        if (idx < 0) {
            if (list.contentY + p.y < 0 || list.count === 0) idx = 0
            else idx = list.count - 1
        }
        return list.itemAtIndex(idx)
    }

    function updatePointerSelection(scenePos) {
        if (!pressBlockId || dragCtl.active)
            return
        var item = delegateAtScene(scenePos.x, scenePos.y)
        if (!item)
            return
        if (item.blockId === pressBlockId) {
            if (editor.rangeActive)
                editor.clearRange()
            return
        }
        if (!pressAnchor) {
            var ed = editor.activeEditor
            if (!ed || ed.blockId !== pressBlockId || ed.cellRow >= 0)
                return
            pressAnchor = { blockId: pressBlockId, pos: ed.cursorPosition === ed.selectionEnd ? ed.selectionStart : ed.selectionEnd }
        }
        var pos = item.isTextLike ? item.positionAtScene(scenePos.x, scenePos.y) : 0
        editor.setRange(pressAnchor, { blockId: item.blockId, pos: pos })
    }

    function focusBlock(blockId, start, end, row, col) {
        var i = doc.indexOf(blockId)
        if (i < 0)
            return
        list.positionViewAtIndex(i, ListView.Contain)
        var item = list.itemAtIndex(i)
        if (item) {
            item.focusBlock(start, end, row, col)
        } else {
            Qt.callLater(function() {
                var it = list.itemAtIndex(i)
                if (it) it.focusBlock(start, end, row, col)
            })
        }
    }

    function blockItem(blockId) {
        var i = doc.indexOf(blockId)
        if (i < 0)
            return null
        list.positionViewAtIndex(i, ListView.Contain)
        var d = list.itemAtIndex(i)
        return d ? d.blockItem : null
    }

    function startDescription(blockId) {
        var it = blockItem(blockId)
        if (it && it.startDescription)
            it.startDescription()
    }

    function focusFirstBlock() {
        if (list.count > 0)
            focusBlock(doc.blockIdAt(0), 0, 0, 0, 0)
        pendingVisible = null
        list.positionViewAtBeginning()
    }

    function focusNeighbor(index, direction, x) {
        var target = index + direction
        if (target < 0 || target >= list.count)
            return
        list.positionViewAtIndex(target, ListView.Contain)
        var item = list.itemAtIndex(target)
        if (!item)
            return
        if (direction > 0) item.focusFromAbove(x)
        else item.focusFromBelow(x)
    }

    function scrollBy(dy) {
        var maxY = list.originY + list.contentHeight - list.height
        list.contentY = Math.max(list.originY, Math.min(maxY, list.contentY + dy))
    }

    // Przewijanie do kursora liczymy po zakończeniu bieżącego układu (wysokości delegatów
    // mogą się jeszcze zmieniać, np. przy wczytywaniu dokumentu).
    property var pendingVisible: null

    function ensureVisible(item, area) {
        pendingVisible = { item: item, area: area }
        Qt.callLater(applyEnsureVisible)
    }

    function applyEnsureVisible() {
        var req = pendingVisible
        pendingVisible = null
        if (!req || !req.item || !list.contentItem)
            return
        var p = req.item.mapToItem(list, req.area.x, req.area.y)
        var h = req.area.height * zoom
        if (p.y < 24)
            scrollBy(p.y - 24)
        else if (p.y + h > list.height - 24)
            scrollBy(p.y + h - list.height + 24)
    }

    // --- przeciąganie: wyznaczanie miejsca upuszczenia --------------------------------------
    function updateDrop() {
        if (!dragCtl.active || (dragCtl.kind !== "block" && dragCtl.kind !== "insert")) {
            dropVisible = false
            return
        }
        var p = list.mapFromItem(null, dragCtl.scenePos.x, dragCtl.scenePos.y)
        if (p.x < 0 || p.y < 0 || p.x > list.width || p.y > list.height) {
            if (dropVisible)
                dragCtl.overTarget = false
            dropVisible = false
            return
        }
        var cy = list.contentY + p.y
        var idx = list.indexAt(10, cy)
        var dest, lineY
        if (idx < 0) {
            var first = list.itemAtIndex(0)
            if (first && cy < first.y) {
                dest = 0
                lineY = first.y
            } else {
                dest = list.count
                var last = list.itemAtIndex(list.count - 1)
                lineY = last ? last.y + last.height : list.contentY + p.y
            }
        } else {
            var it = list.itemAtIndex(idx)
            var before = cy - it.y < it.height / 2
            dest = before ? idx : idx + 1
            lineY = before ? it.y : it.y + it.height
        }
        var problem = dragCtl.kind === "block" ? doc.moveBlockProblem(dragCtl.sourceId, dest) : ""
        dropIndex = dest
        dropLine.y = lineY - list.contentY - dropLine.height / 2
        dropLine.allowed = problem === ""
        dropVisible = problem !== "noop"
        dragCtl.overTarget = problem !== "noop"
        dragCtl.dropAllowed = problem === ""
        dragCtl.problem = problem === "noop" ? "" : problem
    }

    Connections {
        target: docView.dragCtl
        function onScenePosChanged() { docView.updateDrop() }
        function onReleased(cancelled) {
            var visible = docView.dropVisible
            docView.dropVisible = false
            if (cancelled || !visible || !docView.dragCtl.dropAllowed)
                return
            if (docView.dragCtl.kind === "block") {
                docView.doc.moveBlock(docView.dragCtl.sourceId, docView.dropIndex)
            } else if (docView.dragCtl.kind === "insert") {
                var kind = docView.dragCtl.insertKind
                docView.editor.pendingInsertIndex = docView.dropIndex
                if (kind === "table")
                    docView.editor.insertTableRequested()
                else if (kind === "image")
                    docView.editor.imageRequested("")
                else
                    docView.editor.insert(kind, docView.dragCtl.insertOptions)
            }
        }
    }

    Connections {
        target: docView.doc
        function onFocusRequested(blockId, start, end, row, col) { docView.focusBlock(blockId, start, end, row, col) }
    }

    Connections {
        target: docView.editor
        function onEnsureVisibleRequested(item, area) { docView.ensureVisible(item, area) }
    }

    Rectangle {
        anchors.fill: parent
        color: Theme.workspace
    }

    ListView {
        id: list
        anchors.fill: parent
        model: docView.doc
        interactive: false
        clip: true
        reuseItems: false
        cacheBuffer: 1600
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: Math.max(width, docView.pageWidth * docView.zoom + 48)
        flickableDirection: Flickable.HorizontalAndVerticalFlick
        activeFocusOnTab: false
        Accessible.role: Accessible.List
        Accessible.name: "Dokument"

        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded; minimumSize: 0.04 }
        ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AsNeeded }

        header: Item {
            width: list.contentWidth
            height: 28 + docView.marginTop * docView.zoom
            Rectangle {
                x: docView.paperX
                y: 28
                width: docView.pageWidth * docView.zoom
                height: parent.height - 28
                color: Theme.paper
                Rectangle { width: parent.width; height: 1; color: Theme.border }
                Rectangle { width: 1; height: parent.height; color: Theme.border }
                Rectangle { x: parent.width - 1; width: 1; height: parent.height; color: Theme.border }
                // Znaczniki narożników obszaru tekstu (widoczne marginesy).
                Repeater {
                    model: 2
                    delegate: Item {
                        required property int index
                        x: (index === 0 ? docView.marginLeft : docView.pageWidth - docView.marginRight) * docView.zoom
                        y: parent.height - 1
                        Rectangle { x: index === 0 ? -14 : 0; y: 0; width: 14; height: 1; color: Theme.borderStrong }
                        Rectangle { x: 0; y: -14; width: 1; height: 14; color: Theme.borderStrong }
                    }
                }
            }
        }

        footer: Item {
            width: list.contentWidth
            height: docView.marginBottom * docView.zoom + 120
            Rectangle {
                id: footerPaper
                x: docView.paperX
                width: docView.pageWidth * docView.zoom
                height: docView.marginBottom * docView.zoom
                color: Theme.paper
                Rectangle { y: parent.height - 1; width: parent.width; height: 1; color: Theme.border }
                Rectangle { width: 1; height: parent.height; color: Theme.border }
                Rectangle { x: parent.width - 1; width: 1; height: parent.height; color: Theme.border }
            }
            Button {
                anchors.horizontalCenter: footerPaper.horizontalCenter
                y: footerPaper.height + 16
                flat: true
                text: "+ Dodaj akapit na końcu"
                font.pointSize: Theme.fontSmall
                onClicked: docView.doc.insertBlock(-1, "paragraph", {})
            }
        }

        onContentHeightChanged: Qt.callLater(docView.bumpFloats)
        onCountChanged: Qt.callLater(docView.bumpFloats)

        delegate: BlockDelegate {
            doc: docView.doc
            editor: docView.editor
            dragCtl: docView.dragCtl
            view: docView
            zoom: docView.zoom
            pageWidth: docView.pageWidth
            marginLeft: docView.marginLeft
            marginRight: docView.marginRight
            marginTop: docView.marginTop
            marginBottom: docView.marginBottom
        }
    }

    // Przewijanie kółkiem (lista nie jest „flickable” myszą, żeby nie kolidować z zaznaczaniem tekstu).
    WheelHandler {
        target: null
        acceptedModifiers: Qt.NoModifier
        onWheel: function(event) {
            docView.scrollBy(-event.angleDelta.y * 0.9)
            if (event.angleDelta.x !== 0)
                list.contentX = Math.max(0, Math.min(list.contentWidth - list.width, list.contentX - event.angleDelta.x))
        }
    }
    WheelHandler {
        target: null
        acceptedModifiers: Qt.ShiftModifier
        onWheel: function(event) {
            var d = event.angleDelta.y !== 0 ? event.angleDelta.y : event.angleDelta.x
            list.contentX = Math.max(0, Math.min(list.contentWidth - list.width, list.contentX - d))
        }
    }
    WheelHandler {
        target: null
        acceptedModifiers: Qt.ControlModifier
        onWheel: function(event) {
            docView.zoomRequested(docView.zoom + (event.angleDelta.y > 0 ? 0.1 : -0.1))
        }
    }

    // Zaznaczanie przeciąganiem przez granice bloków (uchwyt pasywny – edytor tekstu dalej działa).
    PointHandler {
        id: selectPointer
        target: null
        acceptedButtons: Qt.LeftButton
        onActiveChanged: {
            if (active) {
                var item = docView.delegateAtScene(point.scenePosition.x, point.scenePosition.y)
                docView.pressBlockId = item && item.isTextLike ? item.blockId : ""
                docView.pressAnchor = null
                if (docView.editor.rangeActive && !(point.modifiers & Qt.ShiftModifier))
                    docView.editor.clearRange()
            } else {
                if (docView.editor.rangeActive && docView.editor.painterActive)
                    docView.editor.applyPainter(null)
                docView.pressBlockId = ""
                docView.pressAnchor = null
            }
        }
        onPointChanged: if (active && docView.pressBlockId) docView.updatePointerSelection(point.scenePosition)
    }

    Timer {
        interval: 40
        repeat: true
        running: selectPointer.active && docView.editor.rangeActive
        onTriggered: {
            var p = list.mapFromItem(null, selectPointer.point.scenePosition.x, selectPointer.point.scenePosition.y)
            if (p.y < 30) docView.scrollBy(-Math.max(4, (30 - p.y) / 2))
            else if (p.y > list.height - 30) docView.scrollBy(Math.max(4, (p.y - list.height + 30) / 2))
            else return
            docView.updatePointerSelection(selectPointer.point.scenePosition)
        }
    }

    DropLine {
        id: dropLine
        visible: docView.dropVisible
        x: docView.paperX - list.contentX + docView.marginLeft * docView.zoom - 14
        width: (docView.pageWidth - docView.marginLeft - docView.marginRight) * docView.zoom + 14
    }

    // Autoprzewijanie przy krawędziach podczas przeciągania
    Timer {
        interval: 30
        repeat: true
        running: docView.dragCtl && docView.dragCtl.active && (docView.dragCtl.kind === "block" || docView.dragCtl.kind === "insert")
        onTriggered: {
            var p = list.mapFromItem(null, docView.dragCtl.scenePos.x, docView.dragCtl.scenePos.y)
            if (p.x < 0 || p.x > list.width)
                return
            if (p.y < 60 && p.y > -40)
                docView.scrollBy(-Math.max(4, (60 - p.y) / 3))
            else if (p.y > list.height - 60 && p.y < list.height + 40)
                docView.scrollBy(Math.max(4, (p.y - list.height + 60) / 3))
            else
                return
            docView.updateDrop()
        }
    }
}
