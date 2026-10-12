import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

// Wklej specjalnie: wybór, ile formatowania zachować przy wklejaniu.
Dialog {
    id: dialog

    signal modeChosen(string mode)

    title: "Wklej specjalnie"
    modal: true
    anchors.centerIn: Overlay.overlay
    width: 440
    focus: true
    standardButtons: Dialog.Ok | Dialog.Cancel

    onOpened: sourceRadio.forceActiveFocus()
    onAccepted: modeChosen(sourceRadio.checked ? "source" : mergeRadio.checked ? "merge" : "plain")

    ColumnLayout {
        anchors.fill: parent
        spacing: 10
        RadioButton {
            id: sourceRadio
            checked: true
            text: "Zachowaj formatowanie źródła"
        }
        Text {
            Layout.fillWidth: true
            Layout.leftMargin: 28
            wrapMode: Text.Wrap
            text: "Nagłówki, listy, tabele, kroje, rozmiary i kolory jak w kopiowanym tekście."
            font.pointSize: Theme.fontSmall
            color: Theme.textFaint
        }
        RadioButton {
            id: mergeRadio
            text: "Dopasuj do formatowania dokumentu"
        }
        Text {
            Layout.fillWidth: true
            Layout.leftMargin: 28
            wrapMode: Text.Wrap
            text: "Zachowuje strukturę (nagłówki, listy, tabele) i wyróżnienia (pogrubienie, kursywa, linki), ale krój, rozmiar i kolory bierze z dokumentu."
            font.pointSize: Theme.fontSmall
            color: Theme.textFaint
        }
        RadioButton {
            id: plainRadio
            text: "Tylko tekst"
        }
        Text {
            Layout.fillWidth: true
            Layout.leftMargin: 28
            wrapMode: Text.Wrap
            text: "Każdy wiersz staje się zwykłym akapitem (skrót: Ctrl+Shift+V)."
            font.pointSize: Theme.fontSmall
            color: Theme.textFaint
        }
    }
}
