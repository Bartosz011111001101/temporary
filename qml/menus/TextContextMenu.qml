import QtQuick
import QtQuick.Controls
import QmlWord.Backend
import ".."

// Menu kontekstowe tekstu (akapit, tytuł, nagłówek).
Menu {
    id: menu

    property DocumentModel doc
    property EditorController editor
    property var payload: ({})
    readonly property string blockId: payload.blockId || ""
    readonly property var ed: payload.editorItem || null
    readonly property bool ranged: editor && editor.rangeActive
    readonly property bool hasSel: ranged || (ed && ed.selectionStart !== ed.selectionEnd)
    readonly property bool isHeading: doc && blockId ? doc.blockType(blockId) === "heading" : false
    signal linkRequested()
    signal descriptionRequested(string blockId)

    MenuItem { text: "Wytnij"; enabled: menu.hasSel; onTriggered: menu.editor.cut() }
    MenuItem { text: "Kopiuj"; enabled: menu.hasSel; onTriggered: menu.editor.copy() }
    MenuItem { text: "Wklej"; onTriggered: menu.editor.paste("source") }
    Menu {
        title: "Wklej specjalnie"
        MenuItem { text: "Dopasuj do formatowania dokumentu"; onTriggered: menu.editor.paste("merge") }
        MenuItem { text: "Tylko tekst"; onTriggered: menu.editor.paste("plain") }
        MenuItem { text: "Więcej…"; onTriggered: menu.editor.pasteSpecialRequested() }
    }
    MenuItem { text: "Zaznacz wszystko"; onTriggered: menu.ed.selectAll() }
    MenuSeparator {}
    Menu {
        title: "Wielkość liter"
        enabled: menu.hasSel
        MenuItem { text: "Jak w zdaniu."; onTriggered: menu.editor.changeCase("sentence") }
        MenuItem { text: "małe litery"; onTriggered: menu.editor.changeCase("lower") }
        MenuItem { text: "WIELKIE LITERY"; onTriggered: menu.editor.changeCase("upper") }
        MenuItem { text: "Każdy Wyraz Wielką Literą"; onTriggered: menu.editor.changeCase("title") }
        MenuItem { text: "zAMIANA wIELKOŚCI lITER"; onTriggered: menu.editor.changeCase("toggle") }
    }
    MenuItem { text: "Wstaw symbol…"; onTriggered: menu.editor.symbolsRequested() }
    MenuItem {
        text: menu.ranged ? "Konwertuj zaznaczone akapity na tabelę…" : "Konwertuj akapit na tabelę…"
        onTriggered: menu.editor.convertRequested("textToTable", menu.blockId)
    }
    MenuSeparator {}
    MenuItem { text: "Link…"; onTriggered: menu.linkRequested() }
    MenuItem {
        text: "Usuń link"
        enabled: menu.ed && menu.ed.linkUnderCursor() !== ""
        onTriggered: menu.ed.removeLink()
    }
    Menu {
        title: "Styl akapitu"
        MenuItem { text: "Tekst podstawowy"; onTriggered: menu.doc.setStyle(menu.blockId, "body") }
        MenuItem { text: "Tytuł"; onTriggered: menu.doc.setStyle(menu.blockId, "title") }
        MenuItem { text: "Nagłówek 1"; onTriggered: menu.doc.setStyle(menu.blockId, "h1") }
        MenuItem { text: "Nagłówek 2"; onTriggered: menu.doc.setStyle(menu.blockId, "h2") }
        MenuItem { text: "Nagłówek 3"; onTriggered: menu.doc.setStyle(menu.blockId, "h3") }
    }
    MenuItem {
        text: "Dodaj opis sekcji"
        visible: menu.isHeading
        height: visible ? implicitHeight : 0
        onTriggered: menu.descriptionRequested(menu.blockId)
    }
    MenuSeparator {}
    InsertSubMenu { doc: menu.doc; editor: menu.editor; blockId: menu.blockId; above: true }
    InsertSubMenu { doc: menu.doc; editor: menu.editor; blockId: menu.blockId }
    MenuSeparator {}
    MenuItem { text: menu.isHeading ? "Przenieś sekcję w górę" : "Przenieś w górę"; onTriggered: menu.doc.moveBlockBy(menu.blockId, -1) }
    MenuItem { text: menu.isHeading ? "Przenieś sekcję w dół" : "Przenieś w dół"; onTriggered: menu.doc.moveBlockBy(menu.blockId, 1) }
    MenuItem { text: "Duplikuj akapit"; onTriggered: menu.doc.duplicateBlock(menu.blockId) }
    MenuItem { text: menu.isHeading ? "Usuń nagłówek / sekcję…" : "Usuń akapit"; onTriggered: menu.editor.removeBlock(menu.blockId) }
}
