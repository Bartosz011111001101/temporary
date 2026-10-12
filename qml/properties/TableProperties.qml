import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QmlWord.Backend
import ".."
import "../controls"

// Właściwości tabeli: wiersze/kolumny, komórki (wyrównanie, tło, scalanie), nagłówek, rozmiary, podpis.
ColumnLayout {
    id: props

    property DocumentModel doc
    property EditorController editor
    property var blockData: ({})
    readonly property string blockId: blockData.id || ""
    readonly property var table: blockData.table || ({ cells: [], colWidths: [], rowHeights: [] })
    readonly property int rows: table.cells ? table.cells.length : 0
    readonly property int cols: rows > 0 ? table.cells[0].length : 0
    readonly property int row: editor && editor.activeRow >= 0 && editor.currentBlockId === blockId ? editor.activeRow : -1
    readonly property int col: editor && editor.activeCol >= 0 && editor.currentBlockId === blockId ? editor.activeCol : -1
    readonly property var cell: row >= 0 && table.cells[row] ? table.cells[row][col] : null
    readonly property var rect: editor ? editor.selectionRect() : null
    readonly property bool hasRange: editor && editor.tableSelection && editor.tableSelection.blockId === blockId
    readonly property string captionId: doc && blockId && doc.revision >= 0 ? doc.captionOf(blockId) : ""

    spacing: 10

    PropertyGroup {
        title: "Tabela " + props.rows + " × " + props.cols

        Text {
            Layout.fillWidth: true
            visible: props.row < 0
            wrapMode: Text.Wrap
            text: "Kliknij komórkę, aby edytować wiersze, kolumny i formatowanie. Shift+klik zaznacza zakres."
            font.pointSize: Theme.fontSmall
            color: Theme.textFaint
        }

        GridLayout {
            columns: 2
            columnSpacing: 4
            rowSpacing: 4
            Layout.fillWidth: true
            enabled: props.row >= 0

            Button { Layout.fillWidth: true; text: "Wiersz powyżej"; onClicked: props.doc.tableInsertRow(props.blockId, props.row) }
            Button { Layout.fillWidth: true; text: "Wiersz poniżej"; onClicked: props.doc.tableInsertRow(props.blockId, props.row + (props.cell ? props.cell.rowSpan || 1 : 1)) }
            Button { Layout.fillWidth: true; text: "Kolumna z lewej"; onClicked: props.doc.tableInsertColumn(props.blockId, props.col) }
            Button { Layout.fillWidth: true; text: "Kolumna z prawej"; onClicked: props.doc.tableInsertColumn(props.blockId, props.col + (props.cell ? props.cell.colSpan || 1 : 1)) }
            Button { Layout.fillWidth: true; text: "Usuń wiersz"; enabled: props.rows > 1; onClicked: props.doc.tableRemoveRow(props.blockId, props.row) }
            Button { Layout.fillWidth: true; text: "Usuń kolumnę"; enabled: props.cols > 1; onClicked: props.doc.tableRemoveColumn(props.blockId, props.col) }
        }
    }

    PropertyGroup {
        title: props.hasRange ? "Zaznaczone komórki" : "Komórka"
        visible: props.row >= 0

        FieldLabel { text: "Wyrównanie tekstu" }
        AlignSelector {
            value: props.cell ? props.cell.align || "left" : "left"
            onPicked: function(a) { props.editor.setAlign(a) }
        }
        RowLayout {
            FieldLabel { text: "Tło" }
            ColorButton {
                iconName: "highlight"
                tip: "Kolor tła komórek"
                colors: Theme.highlightColors
                currentColor: props.cell ? props.cell.background || "" : ""
                lastColor: "#e9ecef"
                noneLabel: "Bez tła"
                onColorPicked: function(c) {
                    var r = props.editor.selectionRect()
                    props.doc.tableSetBackground(props.blockId, r.r1, r.c1, r.r2, r.c2, c)
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Button {
                Layout.fillWidth: true
                text: "Scal komórki"
                enabled: props.hasRange
                onClicked: {
                    var r = props.editor.tableSelection
                    if (props.doc.tableMerge(props.blockId, r.r1, r.c1, r.r2, r.c2))
                        props.editor.tableSelection = null
                }
            }
            Button {
                Layout.fillWidth: true
                text: "Podziel komórkę"
                enabled: !!props.cell && ((props.cell.rowSpan || 1) > 1 || (props.cell.colSpan || 1) > 1)
                onClicked: props.doc.tableSplit(props.blockId, props.row, props.col)
            }
        }
        RowLayout {
            Layout.fillWidth: true
            FieldLabel { text: "Min. wysokość wiersza" }
            NumberField {
                Layout.fillWidth: true
                realValue: props.row >= 0 ? props.table.rowHeights[props.row] || 0 : 0
                realFrom: 0; realTo: 600; realStep: 4; decimals: 0; suffix: "px"
                onEdited: function(v) { props.doc.tableSetRowHeight(props.blockId, props.row, v) }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            FieldLabel { text: "Szerokość kolumny" }
            NumberField {
                Layout.fillWidth: true
                realValue: props.col >= 0 ? Math.round((props.table.colWidths[props.col] || 0) * 1000) / 10 : 0
                realFrom: 4; realTo: 96; realStep: 1; decimals: 1; suffix: "%"
                onEdited: function(v) {
                    // Pozostałe kolumny dzielą resztę proporcjonalnie.
                    var w = props.table.colWidths.slice()
                    var target = v / 100
                    var rest = 1 - w[props.col]
                    var newRest = 1 - target
                    for (var i = 0; i < w.length; ++i)
                        w[i] = i === props.col ? target : (rest > 0 ? w[i] * newRest / rest : newRest / (w.length - 1))
                    props.doc.tableSetColumnWidths(props.blockId, w)
                }
            }
        }
        Button {
            text: "Wyrównaj szerokości kolumn"
            onClicked: {
                var w = []
                for (var i = 0; i < props.cols; ++i) w.push(1 / props.cols)
                props.doc.tableSetColumnWidths(props.blockId, w)
            }
        }
    }

    PropertyGroup {
        title: "Krawędzie komórek"
        visible: props.row >= 0
        Text {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: props.hasRange ? "Dotyczy zaznaczonego zakresu (Shift+klik)." : "Dotyczy bieżącej komórki – zaznacz zakres Shift+klikiem."
            font.pointSize: Theme.fontSmall
            color: Theme.textFaint
        }
        GridLayout {
            columns: 2
            columnSpacing: 4
            rowSpacing: 4
            Layout.fillWidth: true
            Repeater {
                model: [
                    { key: "all", label: "Wszystkie" }, { key: "outside", label: "Zewnętrzne" },
                    { key: "inside", label: "Wewnętrzne" }, { key: "thickOutside", label: "Gruba ramka" },
                    { key: "top", label: "Górna" }, { key: "bottom", label: "Dolna" },
                    { key: "left", label: "Lewa" }, { key: "right", label: "Prawa" },
                    { key: "none", label: "Bez krawędzi" }, { key: "reset", label: "Jak w stylu" }
                ]
                delegate: Button {
                    required property var modelData
                    Layout.fillWidth: true
                    text: modelData.label
                    onClicked: {
                        var r = props.editor.selectionRect()
                        props.doc.tableSetBorders(props.blockId, r.r1, r.c1, r.r2, r.c2, modelData.key)
                    }
                }
            }
        }
    }

    PropertyGroup {
        title: "Styl tabeli"
        ComboBox {
            Layout.fillWidth: true
            model: props.doc ? props.doc.tableStyles : []
            textRole: "label"
            currentIndex: {
                var list = props.doc ? props.doc.tableStyles : []
                for (var i = 0; i < list.length; ++i)
                    if (list[i].key === (props.table.style || "grid")) return i
                return 0
            }
            onActivated: function(i) { props.doc.tableSetOptions(props.blockId, { style: props.doc.tableStyles[i].key }) }
        }
        CheckBox {
            text: "Pasy (co drugi wiersz z tłem)"
            checked: !!props.table.bandedRows
            onToggled: props.doc.tableSetOptions(props.blockId, { bandedRows: checked })
        }
        CheckBox {
            text: "Wyróżniona pierwsza kolumna"
            checked: !!props.table.firstColumn
            onToggled: props.doc.tableSetOptions(props.blockId, { firstColumn: checked })
        }
    }

    PropertyGroup {
        title: "Dane"
        RowLayout {
            Layout.fillWidth: true
            enabled: props.col >= 0
            IconButton {
                iconName: "sortAsc"
                text: "Sortuj A→Z"
                showLabel: true
                tip: "Sortuj wiersze rosnąco wg bieżącej kolumny (nagłówek zostaje na miejscu)"
                onClicked: props.doc.tableSort(props.blockId, props.col, false)
            }
            IconButton {
                iconName: "sortDesc"
                text: "Z→A"
                showLabel: true
                tip: "Sortuj malejąco wg bieżącej kolumny"
                onClicked: props.doc.tableSort(props.blockId, props.col, true)
            }
        }
        RowLayout {
            Layout.fillWidth: true
            enabled: props.row >= 0
            IconButton {
                iconName: "formula"
                text: props.cell && props.cell.formula ? "Edytuj formułę" : "Wstaw formułę…"
                showLabel: true
                onClicked: props.editor.formulaRequested(props.blockId, props.row, props.col)
            }
            Text {
                Layout.fillWidth: true
                visible: !!(props.cell && props.cell.formula)
                text: props.cell ? props.cell.formula || "" : ""
                elide: Text.ElideRight
                font.family: "Consolas"
                font.pointSize: Theme.fontSmall
                color: Theme.accent
            }
        }
        Button {
            Layout.fillWidth: true
            text: "Konwertuj tabelę na tekst…"
            onClicked: props.editor.convertRequested("tableToText", props.blockId)
        }
    }

    PropertyGroup {
        title: "Nagłówek tabeli"
        CheckBox {
            text: "Pierwszy wiersz jest nagłówkiem"
            checked: !!props.table.headerRow
            onToggled: props.doc.tableSetOptions(props.blockId, { headerRow: checked })
        }
        CheckBox {
            text: "Powtarzaj nagłówek na kolejnych stronach"
            enabled: !!props.table.headerRow
            checked: !!props.table.repeatHeader
            onToggled: props.doc.tableSetOptions(props.blockId, { repeatHeader: checked })
        }
        Text {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: "Powtarzanie widać w podglądzie stron i w PDF."
            font.pointSize: Theme.fontSmall
            color: Theme.textFaint
        }
    }

    PropertyGroup {
        title: "Podpis"
        Button {
            Layout.fillWidth: true
            text: props.captionId ? "Przejdź do podpisu" : "Dodaj podpis"
            onClicked: props.captionId ? props.doc.requestFocus(props.captionId, 0, 0, -1, -1) : props.doc.addCaption(props.blockId)
        }
        Button {
            Layout.fillWidth: true
            text: "Usuń tabelę…"
            palette.buttonText: Theme.danger
            onClicked: props.editor.removeBlock(props.blockId)
        }
    }
}
