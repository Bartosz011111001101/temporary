import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QmlWord.Backend
import ".."
import "../controls"

// Formuła komórki tabeli (wynik liczony automatycznie przy każdej zmianie tabeli).
Dialog {
    id: dialog

    property DocumentModel doc
    property string blockId: ""
    property int row: -1
    property int col: -1

    function openFor(id, r, c) {
        blockId = id
        row = r
        col = c
        field.text = doc.cellFormula(id, r, c) || "=SUMA(POWYŻEJ)"
        open()
    }

    function columnName(c) {
        var s = ""
        c += 1
        while (c > 0) { var m = (c - 1) % 26; s = String.fromCharCode(65 + m) + s; c = Math.floor((c - 1) / 26) }
        return s
    }

    title: "Formuła komórki " + (col >= 0 ? columnName(col) + (row + 1) : "")
    modal: true
    anchors.centerIn: Overlay.overlay
    width: 520
    focus: true

    onOpened: { field.forceActiveFocus(); field.selectAll() }

    ColumnLayout {
        anchors.fill: parent
        spacing: 8
        FieldLabel { text: "Formuła" }
        TextField {
            id: field
            Layout.fillWidth: true
            font.family: "Consolas"
            selectByMouse: true
            onAccepted: okButton.clicked()
        }
        FieldLabel { text: "Szybki wybór" }
        Flow {
            Layout.fillWidth: true
            spacing: 4
            Repeater {
                model: ["=SUMA(POWYŻEJ)", "=SUMA(LEWO)", "=ŚREDNIA(POWYŻEJ)", "=MAX(POWYŻEJ)", "=MIN(POWYŻEJ)", "=ILE(POWYŻEJ)"]
                delegate: Button {
                    required property string modelData
                    text: modelData
                    font.family: "Consolas"
                    font.pointSize: Theme.fontSmall
                    onClicked: field.text = modelData
                }
            }
        }
        Text {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            font.pointSize: Theme.fontSmall
            color: Theme.textMuted
            text: "Funkcje: SUMA, ŚREDNIA, MIN, MAX, ILE, ILOCZYN, ZAOKR(liczba; miejsca).\n"
                  + "Zakresy: POWYŻEJ, PONIŻEJ, LEWO, PRAWO albo adresy komórek (A1, B2:B5). "
                  + "Działania: + − * / i nawiasy, np. =B2*C2 albo =ZAOKR(SUMA(LEWO); 2).\n"
                  + "Kolumny oznaczane są literami (A, B, C…), wiersze liczbami od 1."
        }
    }

    footer: DialogButtonBox {
        Button {
            text: "Usuń formułę"
            DialogButtonBox.buttonRole: DialogButtonBox.DestructiveRole
            onClicked: {
                dialog.doc.tableSetFormula(dialog.blockId, dialog.row, dialog.col, "")
                dialog.close()
            }
        }
        Button {
            text: "Anuluj"
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            onClicked: dialog.close()
        }
        Button {
            id: okButton
            text: "OK"
            highlighted: true
            DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
            onClicked: {
                dialog.doc.tableSetFormula(dialog.blockId, dialog.row, dialog.col, field.text)
                dialog.close()
            }
        }
    }
}
