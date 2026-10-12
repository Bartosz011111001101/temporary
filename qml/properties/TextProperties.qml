import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QmlWord.Backend
import ".."
import "../controls"

// Właściwości akapitu/nagłówka: styl, wyrównanie, lista, wcięcie, odstępy i format zaznaczenia.
ColumnLayout {
    id: props

    property DocumentModel doc
    property EditorController editor
    property var blockData: ({})
    readonly property string blockId: blockData.id || ""
    readonly property var para: blockData.para || ({})
    readonly property bool isParagraph: blockData.type === "paragraph"
    readonly property var fmt: editor ? editor.format : ({})

    spacing: 10

    readonly property var styles: [
        { key: "body", label: "Tekst podstawowy" }, { key: "title", label: "Tytuł" },
        { key: "h1", label: "Nagłówek 1" }, { key: "h2", label: "Nagłówek 2" }, { key: "h3", label: "Nagłówek 3" },
        { key: "h4", label: "Nagłówek 4" }, { key: "h5", label: "Nagłówek 5" }, { key: "h6", label: "Nagłówek 6" }
    ]
    readonly property string styleKey: blockData.type === "heading" ? "h" + blockData.level : (blockData.style || "body")

    PropertyGroup {
        title: "Akapit"

        FieldLabel { text: "Styl" }
        ComboBox {
            Layout.fillWidth: true
            model: props.styles
            textRole: "label"
            currentIndex: {
                for (var i = 0; i < props.styles.length; ++i)
                    if (props.styles[i].key === props.styleKey) return i
                return 0
            }
            onActivated: function(index) { props.doc.setStyle(props.blockId, props.styles[index].key) }
        }

        FieldLabel { text: "Wyrównanie" }
        AlignSelector {
            value: props.para.align || "left"
            onPicked: function(a) { props.doc.setParagraph(props.blockId, { align: a }) }
        }

        FieldLabel { text: "Lista"; visible: props.isParagraph }
        ComboBox {
            visible: props.isParagraph
            Layout.fillWidth: true
            model: ["Brak", "Punktowana", "Numerowana"]
            currentIndex: props.para.list === "bullet" ? 1 : props.para.list === "number" ? 2 : 0
            onActivated: function(index) {
                props.doc.setParagraph(props.blockId, { list: ["none", "bullet", "number"][index] })
            }
        }

        FieldLabel {
            visible: props.isParagraph && props.para.list && props.para.list !== "none"
            text: props.para.list === "bullet" ? "Punktor" : "Format numeracji"
        }
        ComboBox {
            id: listStyleBox
            visible: props.isParagraph && props.para.list && props.para.list !== "none"
            Layout.fillWidth: true
            readonly property var labels: props.doc && props.para.list && props.para.list !== "none"
                                          ? props.doc.listStyleLabels[props.para.list] : ({})
            readonly property var keys: Object.keys(labels)
            model: [props.para.list === "bullet" ? "Domyślny (wg poziomu)" : "Domyślny (1., a), i.)"].concat(
                       keys.map(function(k) { return listStyleBox.labels[k] }))
            currentIndex: props.para.listStyle ? keys.indexOf(props.para.listStyle) + 1 : 0
            onActivated: function(i) { props.doc.setParagraph(props.blockId, { listStyle: i === 0 ? "" : keys[i - 1] }) }
        }
        RowLayout {
            visible: props.isParagraph && props.para.list === "number"
            Layout.fillWidth: true
            FieldLabel { text: "Zacznij od" }
            SpinBox {
                from: 0
                to: 9999
                value: props.para.listStart || 0
                editable: true
                textFromValue: function(v) { return v === 0 ? "auto" : String(v) }
                valueFromText: function(t) { var n = parseInt(t); return isNaN(n) ? 0 : n }
                onValueModified: props.doc.setParagraph(props.blockId, { listStart: value })
            }
            CheckBox {
                text: "Kontynuuj"
                checked: !!props.para.listContinue
                onToggled: props.doc.setParagraph(props.blockId, { listContinue: checked })
            }
        }

        FieldLabel { text: "Wcięcie (poziomy po 1,25 cm)"; visible: props.isParagraph }
        SpinBox {
            visible: props.isParagraph
            from: 0
            to: 8
            value: props.para.indent || 0
            onValueModified: props.doc.setParagraph(props.blockId, { indent: value })
        }
    }

    PropertyGroup {
        title: "Odstępy"

        GridLayout {
            columns: 2
            columnSpacing: 8
            rowSpacing: 6
            Layout.fillWidth: true

            FieldLabel { text: "Przed akapitem" }
            NumberField {
                Layout.fillWidth: true
                realValue: props.para.spaceBefore || 0
                realFrom: 0; realTo: 144; realStep: 1; decimals: 0; suffix: "pt"
                onEdited: function(v) { props.doc.setParagraph(props.blockId, { spaceBefore: v }) }
            }
            FieldLabel { text: "Po akapicie" }
            NumberField {
                Layout.fillWidth: true
                realValue: props.para.spaceAfter || 0
                realFrom: 0; realTo: 144; realStep: 1; decimals: 0; suffix: "pt"
                onEdited: function(v) { props.doc.setParagraph(props.blockId, { spaceAfter: v }) }
            }
            FieldLabel { text: "Interlinia" }
            NumberField {
                Layout.fillWidth: true
                realValue: props.para.lineHeight || 1.15
                realFrom: 0.8; realTo: 4; realStep: 0.05; decimals: 2; suffix: "×"
                onEdited: function(v) { props.doc.setParagraph(props.blockId, { lineHeight: v }) }
            }
        }
    }

    PropertyGroup {
        title: "Wcięcia"

        GridLayout {
            columns: 2
            columnSpacing: 8
            rowSpacing: 6
            Layout.fillWidth: true

            FieldLabel { text: "Z lewej" }
            NumberField {
                Layout.fillWidth: true
                realValue: (props.para.leftMm || 0) / 10
                realFrom: -5; realTo: 20; realStep: 0.25; decimals: 2; suffix: "cm"
                onEdited: function(v) { props.doc.setParagraph(props.blockId, { leftMm: Math.round(v * 1000) / 100 }) }
            }
            FieldLabel { text: "Z prawej" }
            NumberField {
                Layout.fillWidth: true
                realValue: (props.para.rightMm || 0) / 10
                realFrom: -5; realTo: 20; realStep: 0.25; decimals: 2; suffix: "cm"
                onEdited: function(v) { props.doc.setParagraph(props.blockId, { rightMm: Math.round(v * 1000) / 100 }) }
            }
            FieldLabel { text: "Specjalne" }
            ComboBox {
                id: specialBox
                Layout.fillWidth: true
                model: ["Brak", "Pierwszy wiersz", "Wysunięcie"]
                readonly property real first: props.para.firstLineMm || 0
                currentIndex: first > 0 ? 1 : first < 0 ? 2 : 0
                onActivated: function(i) {
                    var amount = Math.abs(specialBox.first) || 12.5
                    props.doc.setParagraph(props.blockId, { firstLineMm: i === 0 ? 0 : i === 1 ? amount : -amount })
                }
            }
            FieldLabel { text: "O ile"; visible: specialBox.currentIndex > 0 }
            NumberField {
                visible: specialBox.currentIndex > 0
                Layout.fillWidth: true
                realValue: Math.abs(specialBox.first) / 10
                realFrom: 0; realTo: 10; realStep: 0.25; decimals: 2; suffix: "cm"
                onEdited: function(v) {
                    var mm = Math.round(v * 1000) / 100
                    props.doc.setParagraph(props.blockId, { firstLineMm: specialBox.currentIndex === 2 ? -mm : mm })
                }
            }
        }
    }

    PropertyGroup {
        title: "Tabulatory"
        TabStopsEditor {
            Layout.fillWidth: true
            tabs: props.para.tabs || []
            onChanged: function(tabs) { props.doc.setParagraph(props.blockId, { tabs: tabs }) }
        }
    }

    PropertyGroup {
        title: "Obramowanie i cieniowanie"
        ParagraphBorderEditor {
            Layout.fillWidth: true
            para: props.para
            onChanged: function(patch) { props.doc.setParagraph(props.blockId, patch) }
        }
    }

    PropertyGroup {
        title: "Zaznaczony tekst"
        visible: props.editor && props.editor.activeEditor !== null && props.editor.activeEditor.blockId === props.blockId

        FieldLabel { text: "Krój pisma" }
        ComboBox {
            Layout.fillWidth: true
            model: AppUtils.fontFamilies
            displayText: props.fmt.fontFamily || "Z dokumentu (" + (props.doc ? props.doc.meta.fontFamily : "") + ")"
            onActivated: function(index) { props.editor.applyChar({ fontFamily: AppUtils.fontFamilies[index] }) }
        }
        RowLayout {
            Layout.fillWidth: true
            FieldLabel { text: "Rozmiar" }
            NumberField {
                realValue: props.fmt.fontSize || (props.editor && props.editor.activeEditor ? props.editor.activeEditor.font.pointSize : 11)
                realFrom: 4; realTo: 144; realStep: 1; decimals: 1; suffix: "pt"
                onEdited: function(v) { props.editor.applyChar({ fontSize: v }) }
            }
            Item { Layout.fillWidth: true }
            ColorButton {
                iconName: "textColor"
                tip: "Kolor tekstu"
                colors: Theme.textColors
                currentColor: props.fmt.color || ""
                noneLabel: "Kolor stylu (automatyczny)"
                onColorPicked: function(c) { props.editor.applyChar({ color: c }) }
            }
            ColorButton {
                iconName: "highlight"
                tip: "Zakreślenie"
                colors: Theme.highlightColors
                currentColor: props.fmt.highlight || ""
                lastColor: "#fff3a3"
                noneLabel: "Bez zakreślenia"
                onColorPicked: function(c) { props.editor.applyChar({ highlight: c }) }
            }
        }
        RowLayout {
            visible: !!props.fmt.link
            Layout.fillWidth: true
            FieldLabel { text: "Link:"; }
            Text {
                Layout.fillWidth: true
                text: props.fmt.link || ""
                elide: Text.ElideMiddle
                color: Theme.accent
                font.pointSize: Theme.fontSmall
            }
            Button {
                text: "Usuń"
                onClicked: if (props.editor.activeEditor) props.editor.activeEditor.removeLink()
            }
        }
    }
}
