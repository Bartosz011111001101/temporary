import QtQuick
import QtQuick.Controls
import QtQuick.Controls.impl
import QtQuick.Layouts
import ".."

// Komunikat o błędzie lub ostrzeżeniach (np. dokument wczytany z poprawkami).
Dialog {
    id: dialog

    property string message: ""
    property var details: []
    property bool isError: true

    function showError(t, msg) {
        title = t
        message = msg
        details = []
        isError = true
        open()
    }
    function showWarnings(t, items) {
        title = t
        message = "Plik został otwarty, ale wprowadzono następujące poprawki:"
        details = items
        isError = false
        open()
    }

    modal: true
    anchors.centerIn: Overlay.overlay
    width: 480
    standardButtons: Dialog.Ok
    focus: true

    RowLayout {
        width: parent.width
        spacing: 12
        IconImage {
            Layout.alignment: Qt.AlignTop
            source: Qt.resolvedUrl("../icons/" + (dialog.isError ? "warning" : "info") + ".svg")
            sourceSize: Qt.size(28, 28)
            color: dialog.isError ? Theme.danger : Theme.warning
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 8
            Text {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: dialog.message
                font.family: Theme.uiFont
                font.pointSize: Theme.fontNormal
                color: Theme.text
            }
            Repeater {
                model: dialog.details
                delegate: Text {
                    required property string modelData
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    text: "• " + modelData
                    font.family: Theme.uiFont
                    font.pointSize: Theme.fontSmall
                    color: Theme.textMuted
                }
            }
        }
    }
}
