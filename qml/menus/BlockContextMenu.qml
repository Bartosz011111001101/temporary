import QtQuick
import QtQuick.Controls
import QmlWord.Backend
import ".."

// Menu bloku (uchwyt w marginesie, podział strony, pusty blok, podpis).
Menu {
    id: menu

    property DocumentModel doc
    property EditorController editor
    property var payload: ({})
    readonly property string blockId: payload.blockId || ""
    readonly property string type: doc && blockId ? doc.blockType(blockId) : ""
    readonly property bool isText: type === "paragraph" || type === "heading"

    Menu {
        title: "Zmień styl"
        enabled: menu.isText || menu.type === "placeholder"
        MenuItem { text: "Tekst podstawowy"; onTriggered: menu.doc.setStyle(menu.blockId, "body") }
        MenuItem { text: "Tytuł"; onTriggered: menu.doc.setStyle(menu.blockId, "title") }
        MenuItem { text: "Nagłówek 1"; onTriggered: menu.doc.setStyle(menu.blockId, "h1") }
        MenuItem { text: "Nagłówek 2"; onTriggered: menu.doc.setStyle(menu.blockId, "h2") }
        MenuItem { text: "Nagłówek 3"; onTriggered: menu.doc.setStyle(menu.blockId, "h3") }
    }
    InsertSubMenu { doc: menu.doc; editor: menu.editor; blockId: menu.blockId; above: true }
    InsertSubMenu { doc: menu.doc; editor: menu.editor; blockId: menu.blockId }
    MenuSeparator {}
    MenuItem { text: menu.type === "heading" ? "Przenieś sekcję w górę" : "Przenieś w górę"; onTriggered: menu.doc.moveBlockBy(menu.blockId, -1) }
    MenuItem { text: menu.type === "heading" ? "Przenieś sekcję w dół" : "Przenieś w dół"; onTriggered: menu.doc.moveBlockBy(menu.blockId, 1) }
    MenuItem { text: menu.type === "heading" ? "Kopiuj sekcję" : "Kopiuj blok"; onTriggered: menu.doc.copyBlock(menu.blockId) }
    MenuItem { text: menu.type === "heading" ? "Wytnij sekcję" : "Wytnij blok"; onTriggered: menu.doc.cutBlock(menu.blockId) }
    MenuItem {
        text: menu.isText ? "Wklej na końcu bloku" : "Wklej pod blokiem"
        onTriggered: {
            var len = menu.doc.blockLength(menu.blockId)
            menu.doc.paste(menu.blockId, len, len, -1, -1, "source")
        }
    }
    MenuItem { text: "Duplikuj"; enabled: menu.type !== "caption"; onTriggered: menu.doc.duplicateBlock(menu.blockId) }
    MenuItem { text: "Usuń"; onTriggered: menu.editor.removeBlock(menu.blockId) }
}
