import QtQuick
import QtQuick.Controls
import QtQuick.Controls.impl
import QmlWord.Backend
import ".."

// Jeden blok dokumentu na „kartce”: tło strony, uchwyt przeciągania w marginesie
// i właściwy edytor wybrany wg typu bloku. Zawartość jest skalowana o powiększenie.
Item {
    id: root

    required property int index
    required property string blockId
    required property string blockType
    required property var blockData
    required property int listNumber
    required property string listMarker
    required property int borderJoin
    required property string captionLabel
    required property int captionNumber
    required property bool hasCaption
    required property url imageUrl

    property DocumentModel doc
    property EditorController editor
    property DragController dragCtl
    property var view            // DocumentView – nawigacja między blokami, opływanie
    property real zoom: 1
    property real pageWidth: 794
    property real marginLeft: 94
    property real marginRight: 94
    property real marginTop: 94
    property real marginBottom: 94
    readonly property real contentWidth: pageWidth - marginLeft - marginRight
    readonly property bool isCurrent: editor && editor.currentBlockId === blockId
    readonly property bool isPageBreak: blockType === "pageBreak"
    readonly property bool isTextLike: blockType === "paragraph" || blockType === "heading"
    readonly property real paperX: Math.max(16, (width - pageWidth * zoom) / 2)
    readonly property alias blockItem: loader.item
    readonly property string rangeRole: editor && editor.rangeActive ? editor.rangeRole(index) : ""

    // Obraz z opływaniem: { side, width, height } w px strony – tekst kolejnych bloków go omija.
    readonly property var floatBox: blockType === "image" && loader.item && loader.item.floating
                                    ? { side: loader.item.floatSide, width: loader.item.floatWidth, height: loader.item.floatHeight }
                                    : null
    // Pływający obraz wyżej, obok którego leży ten blok (null = brak).
    readonly property var floatInfo: view && blockType !== "image" ? view.floatFor(index, y) : null
    // Bloki inne niż tekst nie opływają obrazu – zaczynają się pod nim.
    readonly property real floatPush: floatInfo && !isTextLike && blockType !== "caption"
                                      ? Math.max(0, (floatInfo.bottom - y) / zoom) : 0

    width: ListView.view ? ListView.view.contentWidth : 800
    height: Math.ceil(page.height * zoom)
    z: floatBox ? 5 : 0

    function focusBlock(start, end, row, col) {
        var it = loader.item
        if (!it)
            return
        if (blockType === "table" && row >= 0)
            it.focusCell(row, col, start, end)
        else
            it.focusAt(start, end)
    }
    function focusFromAbove(x) { if (loader.item) loader.item.focusFromAbove(x) }
    function focusFromBelow(x) { if (loader.item) loader.item.focusFromBelow(x) }
    function positionAtScene(sx, sy) {
        var it = loader.item
        return it && it.positionAtItem ? it.positionAtItem(null, sx, sy) : 0
    }

    function dragLabel() {
        switch (blockType) {
        case "heading": {
            var info = doc.sectionInfo(blockId)
            return "Sekcja: " + (info.title || "(bez tytułu)") + (info.blockCount > 1 ? " · " + info.blockCount + " el." : "")
        }
        case "table": return hasCaption ? "Tabela " + captionNumber + " (z podpisem)" : "Tabela"
        case "image": return hasCaption ? "Rysunek " + captionNumber + " (z podpisem)" : "Obraz"
        case "caption": return captionLabel + " " + captionNumber + " (z elementem)"
        case "pageBreak": return "Podział strony"
        case "placeholder": return "Pusty blok"
        default: {
            var t = doc.blockData(blockId)
            var text = ""
            for (var i = 0; t.runs && i < t.runs.length; ++i) text += t.runs[i].text
            return text ? "„" + (text.length > 40 ? text.substring(0, 40) + "…" : text) + "”" : "Pusty akapit"
        }
        }
    }

    // Tło kartki
    Rectangle {
        visible: !root.isPageBreak
        x: root.paperX
        width: root.pageWidth * root.zoom
        height: root.height
        color: Theme.paper
        Rectangle { width: 1; height: parent.height; color: Theme.border }
        Rectangle { x: parent.width - 1; width: 1; height: parent.height; color: Theme.border }
    }

    HoverHandler {
        id: hover
    }

    Item {
        id: page
        x: root.paperX
        width: root.pageWidth
        height: loader.item ? Math.max(loader.item.implicitHeight + root.floatPush, root.floatBox ? 2 : 8) : 24
        scale: root.zoom
        transformOrigin: Item.TopLeft

        // Pasek zaznaczonego bloku w lewym marginesie
        Rectangle {
            visible: root.isCurrent && !root.isPageBreak
            x: root.marginLeft - 10
            y: root.floatPush
            width: 3
            height: Math.max(8, parent.height - root.floatPush)
            radius: 1.5
            color: Theme.accent
            opacity: 0.55
        }

        // Uchwyt bloku: przeciągnij, aby przenieść; kliknij, aby otworzyć menu bloku.
        Rectangle {
            id: handle
            objectName: "handle:" + root.blockId
            x: root.marginLeft - 36
            y: root.isPageBreak ? root.marginBottom + 4 : root.floatPush + 2
            width: 22
            height: 22
            radius: 4
            visible: hover.hovered || dragHandler.active || root.isCurrent
            color: handleHover.hovered || dragHandler.active ? Theme.hover : "transparent"
            Accessible.role: Accessible.Button
            Accessible.name: "Przenieś lub otwórz menu bloku"

            IconImage {
                anchors.centerIn: parent
                source: Qt.resolvedUrl("../icons/grip.svg")
                sourceSize: Qt.size(16, 16)
                color: handleHover.hovered || dragHandler.active ? Theme.accent : Theme.textFaint
            }
            HoverHandler {
                id: handleHover
                cursorShape: dragHandler.active ? Qt.ClosedHandCursor : Qt.OpenHandCursor
            }
            ToolTip.visible: handleHover.hovered && !dragHandler.active
            ToolTip.delay: 700
            ToolTip.text: "Przeciągnij, aby przenieść · kliknij, aby otworzyć menu"

            DragHandler {
                id: dragHandler
                target: null
                dragThreshold: 4
                onActiveChanged: {
                    if (active) {
                        root.doc.flush()
                        root.editor.clearRange()
                        root.editor.select(root.blockId)
                        root.dragCtl.begin("block", root.blockId, root.dragLabel())
                        root.dragCtl.move(centroid.scenePosition)
                    } else {
                        root.dragCtl.finish(false)
                    }
                }
                onCentroidChanged: if (active) root.dragCtl.move(centroid.scenePosition)
            }
            TapHandler {
                onTapped: {
                    root.editor.select(root.blockId)
                    root.editor.contextMenuRequested(root.blockType === "table" ? "tableBlock"
                                                     : root.blockType === "image" ? "image" : "block",
                                                     { blockId: root.blockId })
                }
            }
        }

        Loader {
            id: loader
            x: root.marginLeft
            y: root.floatPush
            width: root.contentWidth
            sourceComponent: {
                switch (root.blockType) {
                case "paragraph":
                case "heading": return textComponent
                case "table": return tableComponent
                case "image": return imageComponent
                case "caption": return captionComponent
                case "pageBreak": return pageBreakComponent
                case "placeholder": return placeholderComponent
                default: return unknownComponent
                }
            }
        }

        // Bloki nietekstowe w zaznaczeniu wielu bloków – podświetlenie całego bloku.
        Rectangle {
            visible: root.rangeRole !== "" && !root.isTextLike && root.blockType !== "caption"
            x: root.marginLeft - 4
            y: root.floatPush
            width: root.contentWidth + 8
            height: Math.max(8, parent.height - root.floatPush)
            color: Qt.rgba(0.16, 0.36, 0.62, 0.16)
            border.width: 1
            border.color: Theme.accent
            radius: 2
            z: 20
        }

        Connections {
            target: loader.item
            ignoreUnknownSignals: true
            function onNavigateUp(x) { root.view.focusNeighbor(root.index, -1, x) }
            function onNavigateDown(x) { root.view.focusNeighbor(root.index, 1, x) }
        }
    }

    Component {
        id: textComponent
        TextBlock {
            doc: root.doc
            editor: root.editor
            blockId: root.blockId
            blockData: root.blockData
            listMarker: root.listMarker
            borderJoin: root.borderJoin
            rangeRole: root.rangeRole
            contentWidth: root.contentWidth
            floatSide: root.floatInfo ? root.floatInfo.side : ""
            floatWidth: root.floatInfo ? root.floatInfo.width : 0
        }
    }
    Component {
        id: tableComponent
        TableBlock {
            doc: root.doc
            editor: root.editor
            blockId: root.blockId
            blockData: root.blockData
            contentWidth: root.contentWidth
        }
    }
    Component {
        id: imageComponent
        ImageBlock {
            doc: root.doc
            editor: root.editor
            blockId: root.blockId
            blockData: root.blockData
            imageUrl: root.imageUrl
            contentWidth: root.contentWidth
        }
    }
    Component {
        id: captionComponent
        CaptionBlock {
            doc: root.doc
            editor: root.editor
            blockId: root.blockId
            blockData: root.blockData
            captionLabel: root.captionLabel
            captionNumber: root.captionNumber
            contentWidth: root.contentWidth
        }
    }
    Component {
        id: pageBreakComponent
        PageBreakBlock {
            doc: root.doc
            editor: root.editor
            blockId: root.blockId
            contentWidth: root.contentWidth
            pageWidth: root.pageWidth
            marginLeft: root.marginLeft
            marginTop: root.marginTop
            marginBottom: root.marginBottom
        }
    }
    Component {
        id: placeholderComponent
        PlaceholderBlock {
            doc: root.doc
            editor: root.editor
            blockId: root.blockId
            contentWidth: root.contentWidth
        }
    }
    Component {
        id: unknownComponent
        UnknownBlock {
            blockData: root.blockData
            contentWidth: root.contentWidth
        }
    }
}
