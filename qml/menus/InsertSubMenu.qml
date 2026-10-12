import QtQuick
import QtQuick.Controls
import QmlWord.Backend
import ".."

// Podmenu „Wstaw poniżej/powyżej” wspólne dla menu kontekstowych.
Menu {
    id: menu

    property DocumentModel doc
    property EditorController editor
    property string blockId: ""
    property bool above: false

    title: above ? "Wstaw powyżej" : "Wstaw poniżej"

    function place(kind, options) {
        if (above) doc.insertBefore(blockId, kind, options)
        else doc.insertAfter(blockId, kind, options)
    }
    function placeAt() {
        var i = doc.indexOf(blockId)
        var count = above ? 0 : doc.movableCount(blockId)
        if (doc.blockType(blockId) === "heading" && !above)
            count = 1
        editor.pendingInsertIndex = above ? i : i + Math.max(1, count)
    }

    MenuItem { text: "Akapit"; onTriggered: menu.place("paragraph", {}) }
    MenuItem { text: "Sekcja (Nagłówek 1)"; onTriggered: menu.place("heading", { level: 1 }) }
    MenuItem { text: "Podsekcja (Nagłówek 2)"; onTriggered: menu.place("heading", { level: 2 }) }
    MenuItem { text: "Tabela…"; onTriggered: { menu.placeAt(); menu.editor.insertTableRequested() } }
    MenuItem { text: "Obraz…"; onTriggered: { menu.placeAt(); menu.editor.imageRequested("") } }
    MenuItem { text: "Podział strony"; onTriggered: menu.place("pageBreak", {}) }
    MenuItem { text: "Pusty blok"; onTriggered: menu.place("placeholder", {}) }
}
