import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QmlWord.Backend
import ".."
import "../controls"

// Właściwości podpisu: element, do którego należy, numer i treść.
ColumnLayout {
    id: props

    property DocumentModel doc
    property EditorController editor
    property var blockData: ({})
    readonly property string blockId: blockData.id || ""
    readonly property var caption: blockData.caption || ({})
    readonly property var info: doc && blockId && doc.revision >= 0 ? doc.captionInfo(blockId) : ({})

    spacing: 10

    PropertyGroup {
        title: "Podpis elementu"

        Text {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: (props.info.label || "Podpis") + " " + (props.info.number || "")
                  + " – podpis jest powiązany ze swoim elementem i przenosi się razem z nim. Numer nadawany jest automatycznie."
            font.pointSize: Theme.fontSmall
            color: Theme.textMuted
        }

        FieldLabel { text: "Treść" }
        TextField {
            Layout.fillWidth: true
            text: props.caption.text || ""
            placeholderText: "Treść podpisu"
            selectByMouse: true
            onEditingFinished: if (text !== (props.caption.text || "")) props.doc.setCaptionText(props.blockId, text)
        }

        Button {
            Layout.fillWidth: true
            text: "Przejdź do " + ((props.info.label || "") === "Tabela" ? "tabeli" : "obrazu")
            onClicked: props.doc.requestFocus(props.caption.targetId, 0, 0, 0, 0)
        }
        Button {
            Layout.fillWidth: true
            text: "Usuń podpis"
            palette.buttonText: Theme.danger
            onClicked: props.doc.removeBlock(props.blockId)
        }
    }
}
