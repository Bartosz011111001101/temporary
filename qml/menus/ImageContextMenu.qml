import QtQuick
import QtQuick.Controls
import QmlWord.Backend
import ".."

// Menu kontekstowe obrazu.
Menu {
    id: menu

    property DocumentModel doc
    property EditorController editor
    property var payload: ({})
    readonly property string blockId: payload.blockId || ""

    MenuItem { text: "Zmień plik obrazu…"; onTriggered: menu.editor.imageRequested(menu.blockId) }
    Menu {
        title: "Szerokość"
        Repeater {
            model: [0.25, 0.5, 0.75, 1.0]
            delegate: MenuItem {
                required property real modelData
                text: Math.round(modelData * 100) + "% obszaru tekstu"
                onTriggered: menu.doc.setImage(menu.blockId, { width: modelData })
            }
        }
    }
    Menu {
        title: "Wyrównanie"
        MenuItem { text: "Do lewej"; onTriggered: menu.doc.setImage(menu.blockId, { align: "left" }) }
        MenuItem { text: "Do środka"; onTriggered: menu.doc.setImage(menu.blockId, { align: "center" }) }
        MenuItem { text: "Do prawej"; onTriggered: menu.doc.setImage(menu.blockId, { align: "right" }) }
    }
    Menu {
        title: "Opływanie tekstem"
        MenuItem { text: "W linii z tekstem"; onTriggered: menu.doc.setImage(menu.blockId, { wrap: "inline" }) }
        MenuItem { text: "Z lewej, tekst z prawej"; onTriggered: menu.doc.setImage(menu.blockId, { wrap: "left" }) }
        MenuItem { text: "Z prawej, tekst z lewej"; onTriggered: menu.doc.setImage(menu.blockId, { wrap: "right" }) }
    }
    Menu {
        title: "Obróć"
        MenuItem {
            text: "W prawo o 90°"
            onTriggered: menu.doc.setImage(menu.blockId, { rotation: ((menu.doc.blockData(menu.blockId).image.rotation || 0) + 90) % 360 })
        }
        MenuItem {
            text: "W lewo o 90°"
            onTriggered: menu.doc.setImage(menu.blockId, { rotation: ((menu.doc.blockData(menu.blockId).image.rotation || 0) + 270) % 360 })
        }
    }
    MenuItem {
        text: menu.doc && menu.blockId && menu.doc.captionOf(menu.blockId) ? "Przejdź do podpisu" : "Dodaj podpis"
        onTriggered: menu.doc.addCaption(menu.blockId)
    }
    MenuSeparator {}
    InsertSubMenu { doc: menu.doc; editor: menu.editor; blockId: menu.blockId; above: true }
    InsertSubMenu { doc: menu.doc; editor: menu.editor; blockId: menu.blockId }
    MenuItem { text: "Przenieś w górę"; onTriggered: menu.doc.moveBlockBy(menu.blockId, -1) }
    MenuItem { text: "Przenieś w dół"; onTriggered: menu.doc.moveBlockBy(menu.blockId, 1) }
    MenuItem { text: "Kopiuj"; onTriggered: menu.doc.copyBlock(menu.blockId) }
    MenuItem { text: "Wytnij"; onTriggered: menu.doc.cutBlock(menu.blockId) }
    MenuItem { text: "Duplikuj"; onTriggered: menu.doc.duplicateBlock(menu.blockId) }
    MenuItem { text: "Usuń obraz"; onTriggered: menu.editor.removeBlock(menu.blockId) }
}
