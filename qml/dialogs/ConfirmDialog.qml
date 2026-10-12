import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

// Potwierdzenie operacji usuwającej większą ilość treści.
// options: { title, message, acceptText, secondaryText?, action(choice) }
Dialog {
    id: dialog

    property var options: ({})

    function ask(opts) {
        options = opts
        open()
    }

    title: options.title || "Potwierdź"
    modal: true
    anchors.centerIn: Overlay.overlay
    width: 460
    focus: true

    onOpened: cancelButton.forceActiveFocus()

    Text {
        width: parent.width
        wrapMode: Text.Wrap
        text: dialog.options.message || ""
        font.family: Theme.uiFont
        font.pointSize: Theme.fontNormal
        color: Theme.text
    }

    footer: DialogButtonBox {
        Button {
            text: dialog.options.secondaryText || ""
            visible: !!dialog.options.secondaryText
            DialogButtonBox.buttonRole: DialogButtonBox.ActionRole
            onClicked: {
                var action = dialog.options.action
                dialog.close()
                if (action) action("secondary")
            }
        }
        Button {
            id: cancelButton
            text: "Anuluj"
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            onClicked: dialog.close()
        }
        Button {
            text: dialog.options.acceptText || "OK"
            palette.buttonText: Theme.danger
            DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
            onClicked: {
                var action = dialog.options.action
                dialog.close()
                if (action) action("accept")
            }
        }
    }
}
