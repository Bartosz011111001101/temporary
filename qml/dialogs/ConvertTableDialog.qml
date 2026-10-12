import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../controls"

// Konwersja zaznaczonych akapitów na tabelę albo tabeli na tekst – wybór separatora kolumn.
Dialog {
    id: dialog

    property string kind: "textToTable"   // textToTable | tableToText
    signal separatorChosen(string kind, string separator)

    function openFor(k) {
        kind = k
        tabRadio.checked = true
        open()
    }

    title: kind === "textToTable" ? "Konwertuj tekst na tabelę" : "Konwertuj tabelę na tekst"
    modal: true
    anchors.centerIn: Overlay.overlay
    width: 420
    focus: true
    standardButtons: Dialog.Ok | Dialog.Cancel

    onAccepted: separatorChosen(kind, tabRadio.checked ? "\t" : semicolonRadio.checked ? ";"
                                     : commaRadio.checked ? "," : (otherField.text || ";"))

    ColumnLayout {
        anchors.fill: parent
        spacing: 6
        Text {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: dialog.kind === "textToTable"
                  ? "Każdy zaznaczony akapit stanie się wierszem tabeli, a separator wyznaczy kolumny."
                  : "Każdy wiersz tabeli stanie się akapitem, a komórki zostaną rozdzielone separatorem."
            font.pointSize: Theme.fontNormal
            color: Theme.text
        }
        FieldLabel { text: "Separator kolumn" }
        ButtonGroup { id: separatorGroup }
        RadioButton { id: tabRadio; text: "Tabulator"; checked: true; ButtonGroup.group: separatorGroup }
        RadioButton { id: semicolonRadio; text: "Średnik ;"; ButtonGroup.group: separatorGroup }
        RadioButton { id: commaRadio; text: "Przecinek ,"; ButtonGroup.group: separatorGroup }
        RowLayout {
            RadioButton { id: otherRadio; text: "Inny:"; ButtonGroup.group: separatorGroup }
            TextField {
                id: otherField
                Layout.preferredWidth: 60
                maximumLength: 3
                enabled: otherRadio.checked
            }
        }
    }
}
