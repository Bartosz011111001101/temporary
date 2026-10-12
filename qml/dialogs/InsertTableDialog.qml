import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../controls"

// Wstawianie tabeli: siatka do szybkiego wyboru + dokładne pola wierszy/kolumn.
Dialog {
    id: dialog

    signal tableChosen(int rows, int cols, bool headerRow, bool caption, string captionText)

    title: "Wstaw tabelę"
    modal: true
    anchors.centerIn: Overlay.overlay
    standardButtons: Dialog.Ok | Dialog.Cancel
    focus: true

    property int hoverRows: 0
    property int hoverCols: 0

    onOpened: {
        rowsBox.value = 3
        colsBox.value = 3
        captionCheck.checked = false
        captionField.text = ""
        rowsBox.forceActiveFocus()
    }
    onAccepted: tableChosen(rowsBox.value, colsBox.value, headerCheck.checked, captionCheck.checked, captionField.text)

    ColumnLayout {
        spacing: 10

        FieldLabel { text: "Wskaż rozmiar myszą lub wpisz poniżej" }
        Grid {
            id: picker
            columns: 10
            spacing: 2
            Repeater {
                model: 80
                delegate: Rectangle {
                    required property int index
                    readonly property int r: Math.floor(index / 10) + 1
                    readonly property int c: index % 10 + 1
                    width: 18
                    height: 18
                    radius: 2
                    color: r <= dialog.hoverRows && c <= dialog.hoverCols ? Theme.accentSoft : Theme.paper
                    border.color: r <= dialog.hoverRows && c <= dialog.hoverCols ? Theme.accent : Theme.border
                    HoverHandler {
                        onHoveredChanged: if (hovered) { dialog.hoverRows = parent.r; dialog.hoverCols = parent.c }
                    }
                    TapHandler {
                        onTapped: {
                            rowsBox.value = parent.r
                            colsBox.value = parent.c
                            dialog.accept()
                        }
                    }
                }
            }
        }
        FieldLabel { text: dialog.hoverRows > 0 ? dialog.hoverRows + " × " + dialog.hoverCols : " " }

        GridLayout {
            columns: 2
            columnSpacing: 10
            FieldLabel { text: "Wiersze" }
            SpinBox { id: rowsBox; from: 1; to: 500; value: 3; editable: true }
            FieldLabel { text: "Kolumny" }
            SpinBox { id: colsBox; from: 1; to: 50; value: 3; editable: true }
        }
        CheckBox { id: headerCheck; text: "Pierwszy wiersz jako nagłówek (powtarzany na stronach)"; checked: true }
        CheckBox { id: captionCheck; text: "Dodaj podpis pod tabelą" }
        TextField {
            id: captionField
            Layout.fillWidth: true
            enabled: captionCheck.checked
            placeholderText: "Treść podpisu (numer zostanie nadany automatycznie)"
        }
    }
}
