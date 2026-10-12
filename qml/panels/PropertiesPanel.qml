import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QmlWord.Backend
import ".."
import "../properties"

// Prawy panel: właściwości zaznaczonego elementu (zależne od typu) albo całego dokumentu.
Rectangle {
    id: panel

    property DocumentModel doc
    property EditorController editor
    property OutlineModel outline
    property int tab: 0
    signal pageSetupRequested()

    readonly property var current: editor ? editor.currentData : ({})
    readonly property string type: current.type || ""
    readonly property string typeLabel: ({
        paragraph: current.style === "title" ? "Tytuł" : "Akapit",
        heading: "Sekcja (nagłówek " + (current.level || 1) + ")",
        table: "Tabela", image: "Obraz", caption: "Podpis",
        pageBreak: "Podział strony", placeholder: "Pusty blok", unknown: "Nieznany element"
    })[type] || "Nic nie zaznaczono"

    color: Theme.panel

    Rectangle {
        width: 1
        height: parent.height
        color: Theme.border
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 1
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.margins: 8
            Layout.bottomMargin: 4
            spacing: 4
            Repeater {
                model: ["Element", "Dokument"]
                delegate: Button {
                    required property string modelData
                    required property int index
                    Layout.fillWidth: true
                    text: modelData
                    checked: panel.tab === index
                    flat: !checked
                    font.pointSize: Theme.fontNormal
                    onClicked: panel.tab = index
                }
            }
        }

        Text {
            Layout.fillWidth: true
            Layout.leftMargin: 12
            Layout.rightMargin: 12
            visible: panel.tab === 0
            text: panel.typeLabel
            font.family: Theme.uiFont
            font.pointSize: Theme.fontTitle
            font.weight: Font.DemiBold
            color: Theme.text
            elide: Text.ElideRight
        }

        ScrollView {
            id: scroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            clip: true

            Loader {
                width: scroll.availableWidth - 24
                x: 12
                y: 4
                sourceComponent: panel.tab === 1 ? documentProps
                               : panel.type === "paragraph" ? textProps
                               : panel.type === "heading" ? sectionProps
                               : panel.type === "table" ? tableProps
                               : panel.type === "image" ? imageProps
                               : panel.type === "caption" ? captionProps
                               : panel.type !== "" ? blockProps : emptyProps
            }
        }
    }

    Component {
        id: textProps
        TextProperties { doc: panel.doc; editor: panel.editor; blockData: panel.current }
    }
    Component {
        id: sectionProps
        ColumnLayout {
            spacing: 10
            SectionProperties { Layout.fillWidth: true; doc: panel.doc; editor: panel.editor; blockData: panel.current }
            TextProperties { Layout.fillWidth: true; doc: panel.doc; editor: panel.editor; blockData: panel.current }
        }
    }
    Component {
        id: tableProps
        TableProperties { doc: panel.doc; editor: panel.editor; blockData: panel.current }
    }
    Component {
        id: imageProps
        ImageProperties { doc: panel.doc; editor: panel.editor; blockData: panel.current }
    }
    Component {
        id: captionProps
        CaptionProperties { doc: panel.doc; editor: panel.editor; blockData: panel.current }
    }
    Component {
        id: blockProps
        BlockProperties { doc: panel.doc; editor: panel.editor; blockData: panel.current }
    }
    Component {
        id: documentProps
        DocumentProperties {
            doc: panel.doc
            outline: panel.outline
            onPageSetupRequested: panel.pageSetupRequested()
        }
    }
    Component {
        id: emptyProps
        Text {
            wrapMode: Text.Wrap
            text: "Kliknij akapit, sekcję, tabelę lub obraz, aby zobaczyć jego właściwości.\n\nUstawienia całego dokumentu są w zakładce „Dokument”."
            font.family: Theme.uiFont
            font.pointSize: Theme.fontSmall
            color: Theme.textMuted
        }
    }
}
