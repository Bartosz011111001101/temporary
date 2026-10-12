import QtQuick
import QtQuick.Controls
import QmlWord.Backend
import ".."

// Menu kontekstowe sekcji w panelu nawigacji.
Menu {
    id: menu

    property DocumentModel doc
    property EditorController editor
    property OutlineModel outline
    property var payload: ({})
    readonly property string sectionId: payload.sectionId || ""
    readonly property var row: payload.delegate || null
    signal descriptionRequested(string blockId)

    MenuItem { text: "Przejdź do sekcji"; onTriggered: menu.doc.requestFocus(menu.sectionId, 0, 0, -1, -1) }
    MenuItem { text: "Zmień nazwę (F2)"; enabled: menu.row !== null; onTriggered: menu.row.startRename() }
    MenuItem { text: "Dodaj opis sekcji"; onTriggered: menu.descriptionRequested(menu.sectionId) }
    MenuSeparator {}
    MenuItem { text: "Dodaj podsekcję"; onTriggered: menu.doc.addSection(menu.sectionId, true) }
    MenuItem { text: "Dodaj sekcję poniżej"; onTriggered: menu.doc.addSection(menu.sectionId, false) }
    MenuSeparator {}
    MenuItem { text: "Przenieś w górę (Ctrl+↑)"; onTriggered: menu.doc.moveSectionStep(menu.sectionId, -1) }
    MenuItem { text: "Przenieś w dół (Ctrl+↓)"; onTriggered: menu.doc.moveSectionStep(menu.sectionId, 1) }
    MenuItem { text: "Podnieś poziom (Ctrl+←)"; onTriggered: menu.doc.changeSectionLevel(menu.sectionId, -1) }
    MenuItem { text: "Obniż poziom (Ctrl+→)"; onTriggered: menu.doc.changeSectionLevel(menu.sectionId, 1) }
    MenuSeparator {}
    MenuItem { text: "Zwiń / rozwiń"; enabled: menu.row !== null && menu.row.hasChildren; onTriggered: menu.outline.toggle(menu.sectionId) }
    MenuItem { text: "Usuń sekcję z zawartością…"; onTriggered: menu.editor.removeSection(menu.sectionId) }
}
