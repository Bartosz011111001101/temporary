import QtQuick
import QtQuick.Controls
import QmlWord.Backend
import ".."

// Menu kontekstowe tabeli (komórki i cała tabela).
Menu {
    id: menu

    property DocumentModel doc
    property EditorController editor
    property var payload: ({})
    readonly property string blockId: payload.blockId || ""
    readonly property int row: payload.row !== undefined ? payload.row : -1
    readonly property int col: payload.col !== undefined ? payload.col : -1
    readonly property var ed: payload.editorItem || null
    readonly property bool inCell: row >= 0
    readonly property bool hasRange: editor && editor.tableSelection && editor.tableSelection.blockId === blockId
    readonly property var cell: {
        if (!inCell || !doc) return null
        var t = doc.blockData(blockId).table
        return t && t.cells[row] ? t.cells[row][col] : null
    }

    MenuItem { text: "Wytnij"; visible: menu.inCell; height: visible ? implicitHeight : 0; enabled: menu.ed && menu.ed.selectedText !== ""; onTriggered: menu.ed.cut() }
    MenuItem { text: "Kopiuj"; visible: menu.inCell; height: visible ? implicitHeight : 0; enabled: menu.ed && menu.ed.selectedText !== ""; onTriggered: menu.ed.copy() }
    MenuItem { text: "Wklej"; visible: menu.inCell; height: visible ? implicitHeight : 0; enabled: menu.ed && menu.ed.canPaste; onTriggered: menu.ed.paste() }
    MenuSeparator { visible: menu.inCell; height: visible ? implicitHeight : 0 }

    Menu {
        title: "Wstaw"
        enabled: menu.inCell
        MenuItem { text: "Wiersz powyżej"; onTriggered: menu.doc.tableInsertRow(menu.blockId, menu.row) }
        MenuItem { text: "Wiersz poniżej"; onTriggered: menu.doc.tableInsertRow(menu.blockId, menu.row + (menu.cell ? menu.cell.rowSpan || 1 : 1)) }
        MenuItem { text: "Kolumnę z lewej"; onTriggered: menu.doc.tableInsertColumn(menu.blockId, menu.col) }
        MenuItem { text: "Kolumnę z prawej"; onTriggered: menu.doc.tableInsertColumn(menu.blockId, menu.col + (menu.cell ? menu.cell.colSpan || 1 : 1)) }
    }
    Menu {
        title: "Usuń"
        MenuItem { text: "Wiersz"; enabled: menu.inCell; onTriggered: menu.doc.tableRemoveRow(menu.blockId, menu.row) }
        MenuItem { text: "Kolumnę"; enabled: menu.inCell; onTriggered: menu.doc.tableRemoveColumn(menu.blockId, menu.col) }
        MenuItem { text: "Całą tabelę…"; onTriggered: menu.editor.removeBlock(menu.blockId) }
    }
    MenuItem {
        text: "Scal zaznaczone komórki"
        enabled: menu.hasRange
        onTriggered: {
            var r = menu.editor.tableSelection
            if (menu.doc.tableMerge(menu.blockId, r.r1, r.c1, r.r2, r.c2))
                menu.editor.tableSelection = null
        }
    }
    MenuItem {
        text: "Podziel komórkę"
        enabled: menu.cell !== null && ((menu.cell.rowSpan || 1) > 1 || (menu.cell.colSpan || 1) > 1)
        onTriggered: menu.doc.tableSplit(menu.blockId, menu.row, menu.col)
    }
    Menu {
        title: "Wyrównanie komórek"
        enabled: menu.inCell
        MenuItem { text: "Do lewej"; onTriggered: menu.editor.setAlign("left") }
        MenuItem { text: "Do środka"; onTriggered: menu.editor.setAlign("center") }
        MenuItem { text: "Do prawej"; onTriggered: menu.editor.setAlign("right") }
        MenuItem { text: "Wyjustuj"; onTriggered: menu.editor.setAlign("justify") }
    }
    Menu {
        title: "Krawędzie komórek"
        enabled: menu.inCell
        Repeater {
            model: [{ key: "all", label: "Wszystkie" }, { key: "outside", label: "Zewnętrzne" },
                    { key: "inside", label: "Wewnętrzne" }, { key: "thickOutside", label: "Gruba ramka" },
                    { key: "bottom", label: "Dolna" }, { key: "top", label: "Górna" },
                    { key: "none", label: "Bez krawędzi" }, { key: "reset", label: "Jak w stylu tabeli" }]
            delegate: MenuItem {
                required property var modelData
                text: modelData.label
                onTriggered: {
                    var r = menu.editor.selectionRect()
                    menu.doc.tableSetBorders(menu.blockId, r.r1, r.c1, r.r2, r.c2, modelData.key)
                }
            }
        }
    }
    Menu {
        title: "Styl tabeli"
        Repeater {
            model: menu.doc ? menu.doc.tableStyles : []
            delegate: MenuItem {
                required property var modelData
                text: modelData.label
                onTriggered: menu.doc.tableSetOptions(menu.blockId, { style: modelData.key })
            }
        }
    }
    Menu {
        title: "Sortuj wiersze"
        enabled: menu.inCell
        MenuItem { text: "Rosnąco wg tej kolumny"; onTriggered: menu.doc.tableSort(menu.blockId, menu.col, false) }
        MenuItem { text: "Malejąco wg tej kolumny"; onTriggered: menu.doc.tableSort(menu.blockId, menu.col, true) }
    }
    MenuItem {
        text: "Formuła…"
        enabled: menu.inCell
        onTriggered: menu.editor.formulaRequested(menu.blockId, menu.row, menu.col)
    }
    MenuItem { text: "Konwertuj tabelę na tekst…"; onTriggered: menu.editor.convertRequested("tableToText", menu.blockId) }
    MenuSeparator {}
    MenuItem {
        text: menu.doc && menu.blockId && menu.doc.captionOf(menu.blockId) ? "Przejdź do podpisu" : "Dodaj podpis"
        onTriggered: menu.doc.addCaption(menu.blockId)
    }
    InsertSubMenu { doc: menu.doc; editor: menu.editor; blockId: menu.blockId }
    MenuItem { text: "Przenieś tabelę w górę"; onTriggered: menu.doc.moveBlockBy(menu.blockId, -1) }
    MenuItem { text: "Przenieś tabelę w dół"; onTriggered: menu.doc.moveBlockBy(menu.blockId, 1) }
    MenuItem { text: "Duplikuj tabelę"; onTriggered: menu.doc.duplicateBlock(menu.blockId) }
    MenuItem { text: "Kopiuj całą tabelę"; onTriggered: menu.doc.copyBlock(menu.blockId) }
    MenuItem { text: "Wytnij całą tabelę"; onTriggered: menu.doc.cutBlock(menu.blockId) }
}
