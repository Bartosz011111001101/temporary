import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QmlWord.Backend
import ".."
import "../controls"

// Ustawienia strony: rozmiar, orientacja, marginesy (z miniaturą strony).
Dialog {
    id: dialog

    property DocumentModel doc
    readonly property var sizes: ({ "A4": [210, 297], "A5": [148, 210], "Letter": [215.9, 279.4], "Legal": [215.9, 355.6] })

    title: "Ustawienia strony"
    modal: true
    anchors.centerIn: Overlay.overlay
    standardButtons: Dialog.Ok | Dialog.Cancel
    focus: true

    onOpened: {
        var p = doc.page
        sizeBox.currentIndex = Math.max(0, ["A4", "A5", "Letter", "Legal"].indexOf(p.size))
        landscapeRadio.checked = p.landscape
        portraitRadio.checked = !p.landscape
        topField.realValue = p.marginTop
        bottomField.realValue = p.marginBottom
        leftField.realValue = p.marginLeft
        rightField.realValue = p.marginRight
        sizeBox.forceActiveFocus()
    }
    onAccepted: doc.setPageSettings({
        size: sizeBox.currentText,
        landscape: landscapeRadio.checked,
        marginTop: topField.realValue, marginBottom: bottomField.realValue,
        marginLeft: leftField.realValue, marginRight: rightField.realValue
    })

    RowLayout {
        spacing: 20

        ColumnLayout {
            spacing: 8
            FieldLabel { text: "Rozmiar papieru" }
            ComboBox {
                id: sizeBox
                Layout.fillWidth: true
                model: ["A4", "A5", "Letter", "Legal"]
            }
            FieldLabel { text: "Orientacja" }
            RowLayout {
                RadioButton { id: portraitRadio; text: "Pionowa"; checked: true }
                RadioButton { id: landscapeRadio; text: "Pozioma" }
            }
            FieldLabel { text: "Marginesy" }
            GridLayout {
                columns: 2
                columnSpacing: 8
                rowSpacing: 6
                FieldLabel { text: "Górny" }
                NumberField { id: topField; realFrom: 0; realTo: 80; decimals: 0; suffix: "mm"; onEdited: function(v) { realValue = v } }
                FieldLabel { text: "Dolny" }
                NumberField { id: bottomField; realFrom: 0; realTo: 80; decimals: 0; suffix: "mm"; onEdited: function(v) { realValue = v } }
                FieldLabel { text: "Lewy" }
                NumberField { id: leftField; realFrom: 0; realTo: 80; decimals: 0; suffix: "mm"; onEdited: function(v) { realValue = v } }
                FieldLabel { text: "Prawy" }
                NumberField { id: rightField; realFrom: 0; realTo: 80; decimals: 0; suffix: "mm"; onEdited: function(v) { realValue = v } }
            }
            Button {
                text: "Przywróć domyślne (25 mm)"
                flat: true
                onClicked: { topField.realValue = 25; bottomField.realValue = 25; leftField.realValue = 25; rightField.realValue = 25 }
            }
        }

        // Miniatura strony z obszarem tekstu
        Item {
            readonly property var dims: dialog.sizes[sizeBox.currentText] || [210, 297]
            readonly property real wMm: landscapeRadio.checked ? dims[1] : dims[0]
            readonly property real hMm: landscapeRadio.checked ? dims[0] : dims[1]
            readonly property real k: 170 / Math.max(wMm, hMm)
            Layout.preferredWidth: 180
            Layout.preferredHeight: 180
            Rectangle {
                anchors.centerIn: parent
                width: parent.wMm * parent.k
                height: parent.hMm * parent.k
                color: Theme.paper
                border.color: Theme.borderStrong
                Rectangle {
                    x: leftField.realValue * parent.parent.k
                    y: topField.realValue * parent.parent.k
                    width: Math.max(4, parent.width - (leftField.realValue + rightField.realValue) * parent.parent.k)
                    height: Math.max(4, parent.height - (topField.realValue + bottomField.realValue) * parent.parent.k)
                    color: Theme.accentSofter
                    border.color: Theme.accent
                    border.width: 1
                }
            }
        }
    }
}
