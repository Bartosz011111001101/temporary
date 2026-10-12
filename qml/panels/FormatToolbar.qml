import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QmlWord.Backend
import ".."
import "../controls"

// Pasek formatowania: styl, krój, rozmiar, wyróżnienia, kolory, wyrównanie, listy, odstępy i wstawianie.
Rectangle {
    id: bar

    property DocumentModel doc
    property EditorController editor
    readonly property var fmt: editor ? editor.format : ({})
    readonly property bool textOk: editor && editor.hasTextEditor
    readonly property bool paraOk: editor && editor.currentIsText
    readonly property string align: editor && editor.currentData ? editor.currentAlign() : "left"

    signal linkRequested()
    signal tableRequested()
    signal imageRequested()

    readonly property var styleModel: [
        { key: "body", label: "Tekst podstawowy" },
        { key: "title", label: "Tytuł" },
        { key: "h1", label: "Nagłówek 1" },
        { key: "h2", label: "Nagłówek 2" },
        { key: "h3", label: "Nagłówek 3" },
        { key: "h4", label: "Nagłówek 4" },
        { key: "h5", label: "Nagłówek 5" },
        { key: "h6", label: "Nagłówek 6" }
    ]

    function styleIndex(key) {
        for (var i = 0; i < styleModel.length; ++i)
            if (styleModel[i].key === key)
                return i
        return -1
    }

    implicitHeight: flow.implicitHeight + 8
    color: Theme.header

    Flow {
        id: flow
        x: 6
        y: 4
        width: parent.width - 12
        spacing: 2

        // --- schowek i malarz formatów ---
        DropdownButton {
            iconName: "paste"
            tip: "Wklej (Ctrl+V) · strzałka: wklej specjalnie"
            menu: Menu {
                MenuItem { text: "Wklej z formatowaniem źródła"; onTriggered: bar.editor.paste("source") }
                MenuItem { text: "Wklej i dopasuj do dokumentu"; onTriggered: bar.editor.paste("merge") }
                MenuItem { text: "Wklej tylko tekst  (Ctrl+Shift+V)"; onTriggered: bar.editor.paste("plain") }
                MenuSeparator {}
                MenuItem { text: "Wklej specjalnie…  (Ctrl+Alt+V)"; onTriggered: bar.editor.pasteSpecialRequested() }
            }
        }
        IconButton {
            iconName: "cut"
            enabled: bar.editor && (bar.editor.rangeActive || bar.editor.activeEditor !== null || bar.editor.currentBlockId !== "")
            tip: "Wytnij"
            shortcutText: "Ctrl+X"
            onClicked: bar.editor.cut()
        }
        IconButton {
            iconName: "copy"
            enabled: bar.editor && (bar.editor.rangeActive || bar.editor.activeEditor !== null || bar.editor.currentBlockId !== "")
            tip: "Kopiuj"
            shortcutText: "Ctrl+C"
            onClicked: bar.editor.copy()
        }
        IconButton {
            iconName: "brush"
            checked: bar.editor && bar.editor.painterActive
            enabled: bar.textOk || (bar.editor && bar.editor.painterActive)
            tip: "Malarz formatów – kliknij: jednorazowo, dwuklik: wielokrotnie (Esc kończy)"
            onClicked: { if (!clickTimer.running) clickTimer.start() }
            onDoubleClicked: { clickTimer.stop(); bar.editor.cancelPainter(); bar.editor.startPainter(true) }
            Timer {
                id: clickTimer
                interval: 250
                onTriggered: bar.editor.startPainter(false)
            }
        }

        VSeparator {}

        ComboBox {
            id: styleBox
            width: 150
            height: Theme.controlHeight
            model: bar.styleModel
            textRole: "label"
            valueRole: "key"
            enabled: bar.paraOk || (bar.editor && bar.editor.currentType === "placeholder")
            currentIndex: bar.styleIndex(bar.editor ? bar.editor.currentStyle : "")
            displayText: currentIndex >= 0 ? bar.styleModel[currentIndex].label : "Styl"
            font.pointSize: Theme.fontNormal
            Accessible.name: "Styl akapitu"
            ToolTip.visible: hovered
            ToolTip.delay: 600
            ToolTip.text: "Styl akapitu (Ctrl+Alt+0…3)"
            onActivated: function(index) { bar.editor.setStyle(bar.styleModel[index].key) }
        }

        ComboBox {
            id: fontBox
            width: 150
            height: Theme.controlHeight
            model: AppUtils.fontFamilies
            enabled: bar.textOk
            editable: false
            displayText: bar.fmt.fontFamily ? bar.fmt.fontFamily
                         : (bar.doc ? bar.doc.meta.fontFamily + " (styl)" : "")
            font.pointSize: Theme.fontNormal
            Accessible.name: "Krój pisma"
            onActivated: function(index) { bar.editor.applyChar({ fontFamily: AppUtils.fontFamilies[index] }) }
        }

        ComboBox {
            id: sizeBox
            width: 64
            height: Theme.controlHeight
            model: AppUtils.fontSizes
            enabled: bar.textOk
            font.pointSize: Theme.fontNormal
            Accessible.name: "Rozmiar czcionki"
            ToolTip.visible: hovered
            ToolTip.delay: 600
            ToolTip.text: "Rozmiar czcionki (dowolna wartość: panel właściwości)"
            displayText: bar.fmt.fontSize ? String(bar.fmt.fontSize)
                         : (bar.editor && bar.editor.activeEditor ? String(bar.editor.activeEditor.font.pointSize) : "–")
            onActivated: function(index) { bar.editor.applyChar({ fontSize: AppUtils.fontSizes[index] }) }
        }

        VSeparator {}

        IconButton {
            glyph: "B"
            glyphFont.bold: true
            checked: !!bar.fmt.bold
            enabled: bar.textOk
            tip: "Pogrubienie"
            shortcutText: "Ctrl+B"
            onClicked: { bar.editor.toggle("bold"); bar.editor.restoreFocus() }
        }
        IconButton {
            glyph: "I"
            glyphFont.italic: true
            glyphFont.family: "Georgia"
            checked: !!bar.fmt.italic
            enabled: bar.textOk
            tip: "Kursywa"
            shortcutText: "Ctrl+I"
            onClicked: { bar.editor.toggle("italic"); bar.editor.restoreFocus() }
        }
        IconButton {
            glyph: "U"
            glyphFont.underline: true
            checked: !!bar.fmt.underline
            enabled: bar.textOk
            tip: "Podkreślenie"
            shortcutText: "Ctrl+U"
            onClicked: { bar.editor.toggle("underline"); bar.editor.restoreFocus() }
        }
        IconButton {
            glyph: "S"
            glyphFont.strikeout: true
            checked: !!bar.fmt.strike
            enabled: bar.textOk
            tip: "Przekreślenie"
            shortcutText: "Ctrl+Shift+X"
            onClicked: { bar.editor.toggle("strike"); bar.editor.restoreFocus() }
        }
        ColorButton {
            iconName: "textColor"
            enabled: bar.textOk
            tip: "Kolor tekstu"
            colors: Theme.textColors
            currentColor: bar.fmt.color || ""
            noneLabel: "Kolor stylu (automatyczny)"
            onColorPicked: function(color) { bar.editor.applyChar({ color: color }) }
        }
        ColorButton {
            iconName: "highlight"
            enabled: bar.textOk
            tip: "Kolor zaznaczenia (zakreślacz)"
            colors: Theme.highlightColors
            currentColor: bar.fmt.highlight || ""
            lastColor: "#fff3a3"
            noneLabel: "Bez zakreślenia"
            onColorPicked: function(color) { bar.editor.applyChar({ highlight: color }) }
        }
        IconButton {
            glyph: "Tx"
            glyphFont.pointSize: 9
            enabled: bar.textOk
            tip: "Wyczyść formatowanie znaków"
            shortcutText: "Ctrl+Spacja"
            onClicked: bar.editor.applyChar({ bold: null, italic: null, underline: null, strike: null,
                                               color: "", highlight: "", fontFamily: "", fontSize: 0,
                                               vertical: "", smallCaps: null })
        }
        IconButton {
            glyph: "x²"
            glyphFont.pointSize: 9.5
            checked: bar.fmt.vertical === "super"
            enabled: bar.textOk
            tip: "Indeks górny"
            shortcutText: "Ctrl+Shift+="
            onClicked: { bar.editor.toggleVertical("super"); bar.editor.restoreFocus() }
        }
        IconButton {
            glyph: "x₂"
            glyphFont.pointSize: 9.5
            checked: bar.fmt.vertical === "sub"
            enabled: bar.textOk
            tip: "Indeks dolny"
            shortcutText: "Ctrl+="
            onClicked: { bar.editor.toggleVertical("sub"); bar.editor.restoreFocus() }
        }
        IconButton {
            glyph: "Kᴀᴘ"
            glyphFont.pointSize: 8.5
            checked: !!bar.fmt.smallCaps
            enabled: bar.textOk
            tip: "Kapitaliki"
            shortcutText: "Ctrl+Shift+K"
            onClicked: { bar.editor.toggle("smallCaps"); bar.editor.restoreFocus() }
        }
        DropdownButton {
            glyph: "Aa"
            glyphFont.pointSize: 9.5
            enabled: bar.textOk
            tip: "Zmień wielkość liter"
            menu: Menu {
                MenuItem { text: "Jak w zdaniu."; onTriggered: bar.editor.changeCase("sentence") }
                MenuItem { text: "małe litery"; onTriggered: bar.editor.changeCase("lower") }
                MenuItem { text: "WIELKIE LITERY"; onTriggered: bar.editor.changeCase("upper") }
                MenuItem { text: "Każdy Wyraz Wielką Literą"; onTriggered: bar.editor.changeCase("title") }
                MenuItem { text: "zAMIANA wIELKOŚCI lITER"; onTriggered: bar.editor.changeCase("toggle") }
            }
        }

        VSeparator {}

        Repeater {
            model: [
                { a: "left", icon: "alignLeft", tip: "Do lewej", key: "Ctrl+L" },
                { a: "center", icon: "alignCenter", tip: "Do środka", key: "Ctrl+E" },
                { a: "right", icon: "alignRight", tip: "Do prawej", key: "Ctrl+R" },
                { a: "justify", icon: "alignJustify", tip: "Wyjustuj", key: "Ctrl+J" }
            ]
            delegate: IconButton {
                required property var modelData
                iconName: modelData.icon
                checked: bar.align === modelData.a && bar.editor.currentType !== ""
                enabled: bar.paraOk || (bar.editor && bar.editor.inTableCell)
                         || (bar.editor && bar.editor.currentType === "image" && modelData.a !== "justify")
                tip: modelData.tip
                shortcutText: modelData.key
                onClicked: bar.editor.setAlign(modelData.a)
            }
        }

        VSeparator {}

        IconButton {
            iconName: "listBullet"
            checked: bar.editor && bar.editor.currentPara.list === "bullet"
            enabled: bar.editor && bar.editor.currentType === "paragraph"
            tip: "Lista punktowana"
            shortcutText: "Ctrl+Shift+L"
            onClicked: bar.editor.toggleList("bullet")
        }
        DropdownButton {
            arrowOnly: true
            enabled: bar.editor && (bar.editor.currentType === "paragraph" || bar.editor.rangeActive)
            tip: "Styl punktorów"
            menu: Menu {
                Repeater {
                    model: bar.doc ? Object.keys(bar.doc.listStyleLabels.bullet) : []
                    delegate: MenuItem {
                        required property string modelData
                        text: bar.doc.listStyleLabels.bullet[modelData]
                        onTriggered: bar.editor.setListStyle("bullet", modelData)
                    }
                }
            }
        }
        IconButton {
            iconName: "listNumber"
            checked: bar.editor && bar.editor.currentPara.list === "number"
            enabled: bar.editor && bar.editor.currentType === "paragraph"
            tip: "Lista numerowana"
            onClicked: bar.editor.toggleList("number")
        }
        DropdownButton {
            arrowOnly: true
            enabled: bar.editor && (bar.editor.currentType === "paragraph" || bar.editor.rangeActive)
            tip: "Format numeracji"
            menu: Menu {
                Repeater {
                    model: bar.doc ? Object.keys(bar.doc.listStyleLabels.number) : []
                    delegate: MenuItem {
                        required property string modelData
                        text: bar.doc.listStyleLabels.number[modelData]
                        onTriggered: bar.editor.setListStyle("number", modelData)
                    }
                }
                MenuSeparator {}
                MenuItem { text: "Zacznij numerację od 1"; onTriggered: bar.editor.setParagraph({ listStart: 1, listContinue: false }) }
                MenuItem { text: "Kontynuuj numerację"; onTriggered: bar.editor.setParagraph({ listStart: 0, listContinue: true }) }
            }
        }
        IconButton {
            iconName: "indentLess"
            enabled: bar.editor && bar.editor.currentType === "paragraph" && (bar.editor.currentPara.indent || 0) > 0
            tip: "Zmniejsz wcięcie"
            shortcutText: "Shift+Tab (lista)"
            onClicked: bar.editor.indent(-1)
        }
        IconButton {
            iconName: "indentMore"
            enabled: bar.editor && bar.editor.currentType === "paragraph" && (bar.editor.currentPara.indent || 0) < 8
            tip: "Zwiększ wcięcie"
            shortcutText: "Tab (lista)"
            onClicked: bar.editor.indent(1)
        }
        IconButton {
            id: spacingButton
            iconName: "lineSpacing"
            enabled: bar.paraOk
            tip: "Interlinia i odstępy"
            onClicked: spacingMenu.popup(spacingButton, 0, spacingButton.height)

            Menu {
                id: spacingMenu
                Repeater {
                    model: [1.0, 1.15, 1.5, 2.0]
                    delegate: MenuItem {
                        required property real modelData
                        text: "Interlinia " + modelData.toLocaleString(Qt.locale(), 'f', modelData === 1.15 ? 2 : 1)
                        checked: Math.abs((bar.editor.currentPara.lineHeight || 0) - modelData) < 0.01
                        onTriggered: bar.editor.setParagraph({ lineHeight: modelData })
                    }
                }
                MenuSeparator {}
                MenuItem { text: "Bez odstępu przed"; onTriggered: bar.editor.setParagraph({ spaceBefore: 0 }) }
                MenuItem { text: "Odstęp przed: 12 pt"; onTriggered: bar.editor.setParagraph({ spaceBefore: 12 }) }
                MenuItem { text: "Bez odstępu po"; onTriggered: bar.editor.setParagraph({ spaceAfter: 0 }) }
                MenuItem { text: "Odstęp po: 6 pt"; onTriggered: bar.editor.setParagraph({ spaceAfter: 6 }) }
                MenuItem { text: "Odstęp po: 12 pt"; onTriggered: bar.editor.setParagraph({ spaceAfter: 12 }) }
                MenuSeparator {}
                MenuItem { text: "Dokładne wartości w panelu właściwości"; enabled: false }
            }
        }

        VSeparator {}

        IconButton { iconName: "table"; tip: "Wstaw tabelę"; shortcutText: "Ctrl+Alt+T"; onClicked: bar.tableRequested() }
        IconButton { iconName: "image"; tip: "Wstaw obraz"; onClicked: bar.imageRequested() }
        IconButton { iconName: "link"; enabled: bar.textOk; tip: "Wstaw lub edytuj link"; shortcutText: "Ctrl+K"; onClicked: bar.linkRequested() }
        IconButton {
            iconName: "caption"
            tip: "Dodaj podpis do zaznaczonej tabeli lub obrazu"
            enabled: bar.editor && bar.editor.currentData && bar.editor.canAddCaption()
            onClicked: bar.editor.insertCaption()
        }
        IconButton { iconName: "pageBreak"; tip: "Wstaw podział strony"; shortcutText: "Ctrl+Enter"; onClicked: bar.editor.insert("pageBreak", {}) }
        IconButton {
            glyph: "Ω"
            glyphFont.pointSize: 10.5
            enabled: bar.textOk
            tip: "Wstaw symbol lub znak specjalny"
            onClicked: bar.editor.symbolsRequested()
        }

        VSeparator {}

        IconButton {
            glyph: "¶"
            glyphFont.pointSize: 11
            checked: bar.editor && bar.editor.showMarks
            tip: "Pokaż znaki niedrukowalne"
            shortcutText: "Ctrl+Shift+8"
            onClicked: bar.editor.showMarks = !bar.editor.showMarks
        }
    }

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: Theme.border
    }
}
