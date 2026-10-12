import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QmlWord.Backend
import ".."
import "../controls"

// Właściwości sekcji: nazwa, poziom (z podsekcjami lub bez), opis i operacje na strukturze.
ColumnLayout {
    id: props

    property DocumentModel doc
    property EditorController editor
    property var blockData: ({})
    readonly property string blockId: blockData.id || ""
    readonly property var info: doc && blockId && doc.revision >= 0 ? doc.sectionInfo(blockId) : ({})
    readonly property string title: {
        var t = ""
        var runs = blockData.runs || []
        for (var i = 0; i < runs.length; ++i) t += runs[i].text
        return t
    }

    spacing: 10

    PropertyGroup {
        title: "Sekcja"

        FieldLabel { text: "Nazwa" }
        TextField {
            id: nameField
            Layout.fillWidth: true
            text: props.title
            placeholderText: "Tytuł sekcji"
            selectByMouse: true
            onEditingFinished: if (text !== props.title) props.doc.setHeadingTitle(props.blockId, text)
        }

        RowLayout {
            Layout.fillWidth: true
            FieldLabel { text: "Poziom" }
            SpinBox {
                id: levelBox
                from: 1
                to: 6
                value: props.blockData.level || 1
                onValueModified: {
                    var delta = value - (props.blockData.level || 1)
                    if (withChildren.checked) props.doc.changeSectionLevel(props.blockId, delta)
                    else props.doc.setStyle(props.blockId, "h" + value)
                }
            }
        }
        CheckBox {
            id: withChildren
            text: "Zmieniaj poziom razem z podsekcjami"
            checked: true
        }

        Text {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            font.family: Theme.uiFont
            font.pointSize: Theme.fontSmall
            color: Theme.textMuted
            text: props.info.number ? "Numer w spisie: " + props.info.number
                                       + " · elementów: " + props.info.blockCount
                                       + (props.info.parentId ? " · w sekcji „" + props.doc.sectionInfo(props.info.parentId).title + "”" : " · sekcja główna")
                                    : ""
        }
    }

    PropertyGroup {
        title: "Opis sekcji"

        Text {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: "Krótki tekst pod nagłówkiem. To nie jest podpis tabeli ani obrazu."
            font.pointSize: Theme.fontSmall
            color: Theme.textFaint
        }
        TextArea {
            id: descArea
            Layout.fillWidth: true
            Layout.preferredHeight: Math.max(60, contentHeight + 16)
            wrapMode: TextEdit.Wrap
            text: props.blockData.description || ""
            placeholderText: "Brak opisu"
            selectByMouse: true
            onActiveFocusChanged: if (!activeFocus && text !== (props.blockData.description || ""))
                                      props.doc.setDescription(props.blockId, text)
        }
    }

    PropertyGroup {
        title: "Struktura"

        GridLayout {
            columns: 2
            columnSpacing: 4
            rowSpacing: 4
            Layout.fillWidth: true

            Button { Layout.fillWidth: true; text: "Dodaj podsekcję"; onClicked: props.doc.addSection(props.blockId, true) }
            Button { Layout.fillWidth: true; text: "Sekcja poniżej"; onClicked: props.doc.addSection(props.blockId, false) }
            Button { Layout.fillWidth: true; text: "↑ W górę"; onClicked: props.doc.moveSectionStep(props.blockId, -1) }
            Button { Layout.fillWidth: true; text: "↓ W dół"; onClicked: props.doc.moveSectionStep(props.blockId, 1) }
            Button { Layout.fillWidth: true; text: "← Podnieś"; enabled: (props.blockData.level || 1) > 1; onClicked: props.doc.changeSectionLevel(props.blockId, -1) }
            Button { Layout.fillWidth: true; text: "Obniż →"; onClicked: props.doc.changeSectionLevel(props.blockId, 1) }
        }
        Button {
            Layout.fillWidth: true
            text: "Usuń sekcję z zawartością…"
            palette.buttonText: Theme.danger
            onClicked: props.editor.removeSection(props.blockId)
        }
    }
}
