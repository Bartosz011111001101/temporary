import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../controls"

// Wstawianie lub edycja linku w zaznaczonym tekście.
Dialog {
    id: dialog

    property bool hasSelection: false
    property string existingUrl: ""
    signal linkChosen(string text, string url)
    signal linkRemoved()

    title: existingUrl ? "Edytuj link" : "Wstaw link"
    modal: true
    anchors.centerIn: Overlay.overlay
    width: 420
    focus: true

    function openFor(selection, currentUrl) {
        hasSelection = selection
        existingUrl = currentUrl || ""
        textField.text = ""
        urlField.text = existingUrl
        open()
    }

    onOpened: urlField.forceActiveFocus()

    ColumnLayout {
        anchors.fill: parent
        spacing: 8
        FieldLabel { text: "Tekst do wyświetlenia"; visible: !dialog.hasSelection }
        TextField {
            id: textField
            visible: !dialog.hasSelection
            Layout.fillWidth: true
            placeholderText: "Domyślnie adres"
        }
        FieldLabel { text: "Adres (URL)" }
        TextField {
            id: urlField
            Layout.fillWidth: true
            placeholderText: "https://…"
            selectByMouse: true
            onAccepted: okButton.clicked()
        }
        Text {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: "Link otworzysz w dokumencie przez Ctrl+klik."
            font.pointSize: Theme.fontSmall
            color: Theme.textFaint
        }
    }

    footer: DialogButtonBox {
        Button {
            text: "Usuń link"
            visible: dialog.existingUrl !== ""
            DialogButtonBox.buttonRole: DialogButtonBox.DestructiveRole
            onClicked: { dialog.linkRemoved(); dialog.close() }
        }
        Button {
            text: "Anuluj"
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
        }
        Button {
            id: okButton
            text: "OK"
            highlighted: true
            enabled: urlField.text.trim() !== ""
            DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
            onClicked: {
                var url = AppUtils.normalizeUrl(urlField.text)
                dialog.linkChosen(textField.text.trim() || url, url)
                dialog.close()
            }
        }
        onRejected: dialog.close()
    }
}
