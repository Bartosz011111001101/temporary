import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QmlWord.Backend
import ".."
import "../controls"

// Właściwości prostych bloków (podział strony, pusty blok, nieznany typ).
ColumnLayout {
    id: props

    property DocumentModel doc
    property EditorController editor
    property var blockData: ({})
    readonly property string blockId: blockData.id || ""

    spacing: 10

    PropertyGroup {
        title: props.blockData.type === "pageBreak" ? "Podział strony"
             : props.blockData.type === "placeholder" ? "Pusty blok" : "Element"

        Text {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            font.pointSize: Theme.fontSmall
            color: Theme.textMuted
            text: props.blockData.type === "pageBreak"
                  ? "Treść za tym miejscem zaczyna się od nowej strony w podglądzie i w PDF."
                  : props.blockData.type === "placeholder"
                    ? "Miejsce na treść. Zacznij pisać, aby utworzyć akapit, albo zamień je na inny element."
                    : "Element nieobsługiwany przez tę wersję aplikacji – zostanie zachowany w pliku."
        }

        Repeater {
            model: props.blockData.type === "placeholder"
                   ? [{ kind: "paragraph", label: "Zamień na akapit" }, { kind: "heading", label: "Zamień na sekcję" },
                      { kind: "pageBreak", label: "Zamień na podział strony" }] : []
            delegate: Button {
                required property var modelData
                Layout.fillWidth: true
                text: modelData.label
                onClicked: props.doc.replacePlaceholder(props.blockId, modelData.kind, {})
            }
        }

        Button {
            Layout.fillWidth: true
            text: "Usuń"
            palette.buttonText: Theme.danger
            onClicked: props.doc.removeBlock(props.blockId)
        }
    }
}
