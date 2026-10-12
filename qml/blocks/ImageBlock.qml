import QtQuick
import QtQuick.Controls
import QtQuick.Controls.impl
import QmlWord.Backend
import ".."

// Obraz: szerokość (uchwyt w rogu), wyrównanie, kadrowanie, obrót, ramka, opływanie tekstem.
// Przy opływaniu blok ma zerową wysokość – kolejne akapity układają się obok obrazu.
FocusScope {
    id: block

    property DocumentModel doc
    property EditorController editor
    property string blockId: ""
    property var blockData: ({})
    property url imageUrl
    property real contentWidth: 600
    readonly property var img: blockData.image || ({})
    readonly property var crop: img.crop || ({ left: 0, top: 0, right: 0, bottom: 0 })
    readonly property int imgRotation: img.rotation || 0
    readonly property bool rotated: imgRotation === 90 || imgRotation === 270
    readonly property real borderPx: img.border ? img.border.width * Theme.pxPerPt : 0
    readonly property bool isCurrent: editor && editor.currentBlockId === blockId
    property real liveWidth: -1
    readonly property real fraction: liveWidth >= 0 ? liveWidth : (img.width || 0.6)
    readonly property bool ready: picture.status === Image.Ready
    // Rozmiar widocznego (przyciętego) fragmentu oryginału
    readonly property real cropW: Math.max(1, picture.implicitWidth * (1 - (crop.left || 0) - (crop.right || 0)))
    readonly property real cropH: Math.max(1, picture.implicitHeight * (1 - (crop.top || 0) - (crop.bottom || 0)))
    readonly property real aspect: rotated ? cropW / cropH : cropH / cropW

    // Opływanie
    readonly property bool floating: (img.wrap === "left" || img.wrap === "right") && ready
    readonly property string floatSide: img.wrap || ""
    readonly property real floatGap: 14
    readonly property real floatWidth: frame.width + floatGap
    readonly property real floatHeight: frame.y + frame.height + (captionLoader.item ? captionLoader.item.implicitHeight : 0) + 10
    readonly property string captionId: doc && blockId && doc.revision >= 0 ? doc.captionOf(blockId) : ""

    signal navigateUp(real x)
    signal navigateDown(real x)

    implicitHeight: floating ? 2 : frame.height + 12
    activeFocusOnTab: true
    Accessible.role: Accessible.Graphic
    Accessible.name: img.alt || "Obraz"

    function focusAt(start, end) { forceActiveFocus() }
    function focusFromAbove(x) { forceActiveFocus() }
    function focusFromBelow(x) { forceActiveFocus() }

    onActiveFocusChanged: if (activeFocus && editor) editor.select(blockId)

    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Delete || event.key === Qt.Key_Backspace) {
            editor.removeBlock(blockId)
            event.accepted = true
        } else if (event.key === Qt.Key_Up) {
            navigateUp(frame.x)
            event.accepted = true
        } else if (event.key === Qt.Key_Down) {
            navigateDown(frame.x)
            event.accepted = true
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            doc.insertAfter(blockId, "paragraph", {})
            event.accepted = true
        } else if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_C) {
            doc.copyBlock(blockId)
            event.accepted = true
        } else if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_X) {
            doc.cutBlock(blockId)
            event.accepted = true
        }
    }

    Item {
        id: frame
        y: 6
        width: Math.max(40, block.contentWidth * block.fraction)
        height: block.ready ? width * block.aspect : 140
        x: block.floating ? (block.floatSide === "left" ? 0 : block.contentWidth - width)
           : block.img.align === "left" ? 0 : block.img.align === "right" ? block.contentWidth - width
                                                                            : (block.contentWidth - width) / 2

        // Przycięty i obrócony obraz
        Item {
            id: viewport
            anchors.fill: parent
            clip: true
            Item {
                // Układ przed obrotem: przy 90/270° szerokość i wysokość się zamieniają.
                width: block.rotated ? viewport.height : viewport.width
                height: block.rotated ? viewport.width : viewport.height
                anchors.centerIn: parent
                rotation: block.imgRotation
                Image {
                    id: picture
                    source: block.imageUrl
                    fillMode: Image.Stretch
                    asynchronous: true
                    smooth: true
                    mipmap: true
                    sourceSize.width: 1800
                    readonly property real fullW: parent.width / Math.max(0.05, 1 - (block.crop.left || 0) - (block.crop.right || 0))
                    readonly property real fullH: parent.height / Math.max(0.05, 1 - (block.crop.top || 0) - (block.crop.bottom || 0))
                    width: fullW
                    height: fullH
                    x: -(block.crop.left || 0) * fullW
                    y: -(block.crop.top || 0) * fullH
                }
            }
        }

        Rectangle {
            anchors.fill: parent
            visible: block.borderPx > 0 && block.ready
            color: "transparent"
            border.width: block.borderPx
            border.color: block.img.border ? block.img.border.color : "transparent"
        }

        Rectangle {
            anchors.fill: parent
            visible: !block.ready
            color: "#f6f7f9"
            border.color: Theme.borderStrong
            border.width: 1
            radius: 3
            Column {
                anchors.centerIn: parent
                width: parent.width - 24
                spacing: 8
                IconImage {
                    anchors.horizontalCenter: parent.horizontalCenter
                    source: Qt.resolvedUrl("../icons/" + (picture.status === Image.Loading ? "image" : "warning") + ".svg")
                    sourceSize: Qt.size(22, 22)
                    color: picture.status === Image.Loading ? Theme.textMuted : Theme.warning
                }
                Text {
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.Wrap
                    font.family: Theme.uiFont
                    font.pointSize: Theme.fontSmall
                    color: Theme.textMuted
                    text: picture.status === Image.Loading ? "Wczytywanie obrazu…"
                        : !block.img.path ? "Nie wybrano pliku obrazu."
                        : "Nie można wczytać obrazu:\n" + block.img.path
                }
                Button {
                    anchors.horizontalCenter: parent.horizontalCenter
                    visible: picture.status !== Image.Loading
                    text: "Wybierz plik…"
                    onClicked: block.editor.imageRequested(block.blockId)
                }
            }
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: -3
            color: "transparent"
            border.width: block.activeFocus ? 2 : 1
            border.color: block.activeFocus ? Theme.focusRing : Theme.accent
            visible: block.isCurrent || block.activeFocus
            radius: 2
        }

        TapHandler {
            onTapped: block.forceActiveFocus()
        }
        TapHandler {
            acceptedButtons: Qt.RightButton
            onTapped: {
                block.forceActiveFocus()
                block.editor.contextMenuRequested("image", { blockId: block.blockId })
            }
        }

        // Uchwyt zmiany szerokości
        Rectangle {
            id: grip
            visible: block.isCurrent && block.ready
            width: 12
            height: 12
            radius: 2
            x: parent.width - 6
            y: parent.height - 6
            color: Theme.paper
            border.color: Theme.accent
            border.width: 2
            MouseArea {
                anchors.fill: parent
                anchors.margins: -4
                cursorShape: Qt.SizeFDiagCursor
                preventStealing: true
                onPositionChanged: function(mouse) {
                    if (!pressed)
                        return
                    var p = mapToItem(block, mouse.x, mouse.y)
                    var w
                    if (!block.floating && block.img.align === "center")
                        w = 2 * Math.abs(p.x - block.contentWidth / 2)
                    else if (block.floating ? block.floatSide === "right" : block.img.align === "right")
                        w = block.contentWidth - p.x + 6
                    else
                        w = p.x - frame.x
                    block.liveWidth = Math.max(0.05, Math.min(1.0, w / block.contentWidth))
                }
                onReleased: {
                    if (block.liveWidth >= 0)
                        block.doc.setImage(block.blockId, { width: Math.round(block.liveWidth * 100) / 100 })
                    block.liveWidth = -1
                }
            }
        }

        Rectangle {
            visible: block.liveWidth >= 0
            anchors.centerIn: parent
            color: "#2b3138"
            radius: 4
            width: sizeLabel.implicitWidth + 12
            height: sizeLabel.implicitHeight + 6
            Text {
                id: sizeLabel
                anchors.centerIn: parent
                color: "white"
                font.pointSize: Theme.fontSmall
                text: Math.round(block.fraction * 100) + "% szerokości"
            }
        }
    }

    // Podpis obrazu pływającego jest częścią ramki (pod obrazem).
    Loader {
        id: captionLoader
        active: block.floating && block.captionId !== ""
        x: frame.x
        y: frame.y + frame.height + 2
        width: frame.width
        sourceComponent: CaptionBlock {
            doc: block.doc
            editor: block.editor
            blockId: block.captionId
            blockData: block.doc.blockData(block.captionId)
            captionLabel: block.doc.captionInfo(block.captionId).label || "Rysunek"
            captionNumber: block.doc.captionInfo(block.captionId).number || 0
            contentWidth: frame.width
            embedded: true
        }
    }
}
