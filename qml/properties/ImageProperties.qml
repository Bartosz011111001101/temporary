import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QmlWord.Backend
import ".."
import "../controls"

// Właściwości obrazu: plik, szerokość, wyrównanie, tekst alternatywny, podpis.
ColumnLayout {
    id: props

    property DocumentModel doc
    property EditorController editor
    property var blockData: ({})
    readonly property string blockId: blockData.id || ""
    readonly property var img: blockData.image || ({})
    readonly property string captionId: doc && blockId && doc.revision >= 0 ? doc.captionOf(blockId) : ""

    spacing: 10

    PropertyGroup {
        title: "Obraz"

        FieldLabel { text: "Plik" }
        Text {
            Layout.fillWidth: true
            text: props.img.path || "(nie wybrano)"
            elide: Text.ElideMiddle
            font.pointSize: Theme.fontSmall
            color: Theme.text
        }
        Button {
            text: "Zmień plik…"
            onClicked: props.editor.imageRequested(props.blockId)
        }

        FieldLabel { text: "Szerokość: " + Math.round(widthSlider.value * 100) + "% obszaru tekstu" }
        Slider {
            id: widthSlider
            Layout.fillWidth: true
            from: 0.05
            to: 1.0
            stepSize: 0.01
            value: props.img.width || 0.6
            onMoved: props.doc.setImage(props.blockId, { width: Math.round(value * 100) / 100 })
        }

        FieldLabel { text: "Wyrównanie" }
        AlignSelector {
            allowJustify: false
            value: props.img.align || "center"
            onPicked: function(a) { props.doc.setImage(props.blockId, { align: a }) }
        }

        FieldLabel { text: "Tekst alternatywny" }
        TextField {
            Layout.fillWidth: true
            text: props.img.alt || ""
            placeholderText: "Opis obrazu dla czytników ekranu"
            selectByMouse: true
            onEditingFinished: if (text !== (props.img.alt || "")) props.doc.setImage(props.blockId, { alt: text })
        }
    }

    PropertyGroup {
        title: "Układ i opływanie"
        RowLayout {
            spacing: 2
            Repeater {
                model: [
                    { key: "inline", icon: "wrapInline", tip: "W linii z tekstem (osobny wiersz)" },
                    { key: "left", icon: "wrapLeft", tip: "Obraz z lewej, tekst opływa z prawej" },
                    { key: "right", icon: "wrapRight", tip: "Obraz z prawej, tekst opływa z lewej" }
                ]
                delegate: IconButton {
                    required property var modelData
                    iconName: modelData.icon
                    tip: modelData.tip
                    checked: (props.img.wrap || "inline") === modelData.key
                    onClicked: props.doc.setImage(props.blockId, { wrap: modelData.key })
                }
            }
        }
        Text {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            visible: (props.img.wrap || "inline") !== "inline"
            text: "Akapity obok obrazu są w edytorze zwężane w całości; w podglądzie stron i PDF tekst opływa obraz wiersz po wierszu."
            font.pointSize: Theme.fontSmall
            color: Theme.textFaint
        }
    }

    PropertyGroup {
        title: "Obrót i kadrowanie"
        RowLayout {
            IconButton {
                iconName: "rotateLeft"
                tip: "Obróć w lewo o 90°"
                onClicked: props.doc.setImage(props.blockId, { rotation: ((props.img.rotation || 0) + 270) % 360 })
            }
            IconButton {
                iconName: "rotateRight"
                tip: "Obróć w prawo o 90°"
                onClicked: props.doc.setImage(props.blockId, { rotation: ((props.img.rotation || 0) + 90) % 360 })
            }
            FieldLabel { text: "Obrót: " + (props.img.rotation || 0) + "°" }
        }
        FieldLabel { text: "Przytnij (% oryginału)" }
        GridLayout {
            columns: 4
            columnSpacing: 4
            rowSpacing: 4
            Layout.fillWidth: true
            Repeater {
                model: [{ key: "left", label: "Lewo" }, { key: "right", label: "Prawo" },
                        { key: "top", label: "Góra" }, { key: "bottom", label: "Dół" }]
                delegate: ColumnLayout {
                    required property var modelData
                    spacing: 1
                    FieldLabel { text: modelData.label }
                    NumberField {
                        Layout.preferredWidth: 62
                        realValue: Math.round(((props.img.crop || {})[modelData.key] || 0) * 100)
                        realFrom: 0; realTo: 45; realStep: 1; decimals: 0
                        onEdited: function(v) {
                            var crop = Object.assign({ left: 0, top: 0, right: 0, bottom: 0 }, props.img.crop || {})
                            crop[modelData.key] = v / 100
                            props.doc.setImage(props.blockId, { crop: crop })
                        }
                    }
                }
            }
        }
        Button {
            text: "Usuń kadrowanie"
            enabled: !!props.img.crop
            onClicked: props.doc.setImage(props.blockId, { crop: { left: 0, top: 0, right: 0, bottom: 0 } })
        }
    }

    PropertyGroup {
        title: "Ramka"
        RowLayout {
            FieldLabel { text: "Grubość" }
            NumberField {
                Layout.preferredWidth: 90
                realValue: props.img.border ? props.img.border.width : 0
                realFrom: 0; realTo: 12; realStep: 0.5; decimals: 1; suffix: "pt"
                onEdited: function(v) {
                    props.doc.setImage(props.blockId, { border: { width: v, color: props.img.border ? props.img.border.color : "#5b6570" } })
                }
            }
            ColorButton {
                iconName: "borders"
                tip: "Kolor ramki"
                colors: Theme.textColors
                currentColor: props.img.border ? props.img.border.color : ""
                noneLabel: "Domyślny (szary)"
                onColorPicked: function(c) {
                    props.doc.setImage(props.blockId, { border: { width: props.img.border ? props.img.border.width : 1, color: c || "#5b6570" } })
                }
            }
        }
    }

    PropertyGroup {
        title: "Podpis"
        Button {
            Layout.fillWidth: true
            text: props.captionId ? "Przejdź do podpisu" : "Dodaj podpis"
            onClicked: props.captionId ? props.doc.requestFocus(props.captionId, 0, 0, -1, -1) : props.doc.addCaption(props.blockId)
        }
        Button {
            Layout.fillWidth: true
            text: "Usuń obraz"
            palette.buttonText: Theme.danger
            onClicked: props.editor.removeBlock(props.blockId)
        }
    }
}
