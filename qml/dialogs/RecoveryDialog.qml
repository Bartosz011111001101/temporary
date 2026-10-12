import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QmlWord.Backend
import ".."

// Odzyskiwanie kopii roboczych po nieoczekiwanym zamknięciu aplikacji.
Dialog {
    id: dialog

    property AutosaveManager autosave
    property var items: []

    function offer(list) {
        items = list
        if (items.length > 0)
            open()
    }

    title: "Odzyskiwanie dokumentu"
    modal: true
    anchors.centerIn: Overlay.overlay
    width: 520
    focus: true
    closePolicy: Popup.CloseOnEscape

    ColumnLayout {
        anchors.fill: parent
        spacing: 10
        Text {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: "Aplikacja została poprzednio zamknięta nieoczekiwanie. Znaleziono kopie robocze niezapisanych dokumentów:"
            font.family: Theme.uiFont
            font.pointSize: Theme.fontNormal
            color: Theme.text
        }
        Repeater {
            model: dialog.items
            delegate: Rectangle {
                required property var modelData
                Layout.fillWidth: true
                implicitHeight: 54
                radius: Theme.radius
                color: Theme.panel
                border.color: Theme.border
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Text {
                            Layout.fillWidth: true
                            elide: Text.ElideMiddle
                            text: modelData.title + (modelData.originalPath ? "  —  " + modelData.originalPath : "  (niezapisany)")
                            font.pointSize: Theme.fontNormal
                            color: Theme.text
                        }
                        Text {
                            text: "Kopia z " + modelData.savedAt
                            font.pointSize: Theme.fontSmall
                            color: Theme.textMuted
                        }
                    }
                    Button {
                        text: "Odzyskaj"
                        highlighted: true
                        onClicked: {
                            dialog.autosave.recover(modelData.session)
                            dialog.close()
                        }
                    }
                    Button {
                        text: "Odrzuć"
                        flat: true
                        onClicked: {
                            dialog.autosave.discard(modelData.session)
                            var rest = dialog.items.filter(function(i) { return i.session !== modelData.session })
                            dialog.items = rest
                            if (rest.length === 0)
                                dialog.close()
                        }
                    }
                }
            }
        }
    }

    footer: DialogButtonBox {
        Button {
            text: "Zdecyduję później"
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            onClicked: dialog.close()
        }
    }
}
