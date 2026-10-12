import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

// Pytanie o niezapisane zmiany przed zamknięciem / nowym / otwarciem dokumentu.
Dialog {
    id: dialog

    property string documentName: ""
    signal saveChosen()
    signal discardChosen()

    title: "Niezapisane zmiany"
    modal: true
    anchors.centerIn: Overlay.overlay
    width: 440
    focus: true
    closePolicy: Popup.CloseOnEscape

    onOpened: saveButton.forceActiveFocus()

    Text {
        width: parent.width
        wrapMode: Text.Wrap
        text: "Dokument „" + dialog.documentName + "” zawiera niezapisane zmiany.\nCzy chcesz je zapisać przed kontynuowaniem?"
        font.family: Theme.uiFont
        font.pointSize: Theme.fontNormal
        color: Theme.text
    }

    footer: DialogButtonBox {
        Button {
            text: "Nie zapisuj"
            DialogButtonBox.buttonRole: DialogButtonBox.DestructiveRole
            onClicked: { dialog.close(); dialog.discardChosen() }
        }
        Button {
            text: "Anuluj"
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            onClicked: dialog.close()
        }
        Button {
            id: saveButton
            text: "Zapisz"
            highlighted: true
            DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
            onClicked: { dialog.close(); dialog.saveChosen() }
        }
    }
}
