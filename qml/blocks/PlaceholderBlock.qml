import QtQuick
import QtQuick.Controls
import QmlWord.Backend
import ".."

// Pusty blok: miejsce na treść. Pisanie zamienia go w akapit, przyciski – w wybrany element.
Item {
    id: block

    property DocumentModel doc
    property EditorController editor
    property string blockId: ""
    property real contentWidth: 600

    signal navigateUp(real x)
    signal navigateDown(real x)

    implicitHeight: frame.height + 10

    function focusAt(start, end) { edit.focusAt(0, 0) }
    function focusFromAbove(x) { edit.focusAt(0, 0) }
    function focusFromBelow(x) { edit.focusAt(0, 0) }

    Rectangle {
        id: frame
        y: 5
        width: block.contentWidth
        height: content.implicitHeight + 16
        radius: 4
        color: edit.activeFocus ? Theme.accentSofter : "transparent"
        border.width: 1
        border.color: edit.activeFocus ? Theme.accent : Theme.borderStrong

        Column {
            id: content
            x: 10
            y: 8
            width: parent.width - 20
            spacing: 6

            RichTextEditor {
                id: edit
                width: parent.width
                doc: block.doc
                editor: block.editor
                blockId: block.blockId
                styleFont: block.doc ? block.doc.textStyles["body"] : ({})
                placeholderText: "Pusty blok – zacznij pisać albo wybierz element poniżej"
                placeholderAlways: true
                // Pierwszy znak od razu zamienia blok w akapit.
                onTextChanged: if (!loading && length > 0) Qt.callLater(commit)
                onNavigateUp: function(x) { block.navigateUp(x) }
                onNavigateDown: function(x) { block.navigateDown(x) }
            }

            Flow {
                width: parent.width
                spacing: 4
                Repeater {
                    model: [
                        { kind: "paragraph", label: "Akapit", icon: "paragraph" },
                        { kind: "heading", label: "Sekcja", icon: "heading" },
                        { kind: "table", label: "Tabela…", icon: "table" },
                        { kind: "image", label: "Obraz…", icon: "image" },
                        { kind: "pageBreak", label: "Podział strony", icon: "pageBreak" }
                    ]
                    delegate: IconButtonLite {
                        required property var modelData
                        text: modelData.label
                        iconName: modelData.icon
                        onClicked: {
                            block.editor.select(block.blockId)
                            if (modelData.kind === "table")
                                block.editor.insertTableRequested()
                            else if (modelData.kind === "image")
                                block.editor.imageRequested("")
                            else
                                block.doc.replacePlaceholder(block.blockId, modelData.kind, {})
                        }
                    }
                }
            }
        }
    }
}
