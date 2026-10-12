import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QmlWord.Backend
import ".."
import "../controls"

// Pasek „Znajdź i zamień”: wielkość liter, całe wyrazy, formatowanie (szukane i docelowe),
// zamiana bieżącego wyniku i wszystkich naraz (jeden krok cofania).
Rectangle {
    id: bar

    property SearchController search
    property bool replaceMode: false
    property alias findField: findField
    signal closeRequested()

    implicitHeight: column.implicitHeight + 10
    color: Theme.panel

    function describe(fmt, forReplace) {
        var parts = []
        var names = { bold: "pogrubienie", italic: "kursywa", underline: "podkreślenie", strike: "przekreślenie", smallCaps: "kapitaliki" }
        for (var k in names)
            if (fmt[k] !== undefined) parts.push((fmt[k] ? "" : "bez: ") + names[k])
        if (fmt.color) parts.push("kolor " + fmt.color)
        if (fmt.highlight) parts.push("zakreślenie")
        if (fmt.style) parts.push("styl " + fmt.style.toUpperCase())
        return parts.length ? parts.join(", ") : (forReplace ? "bez zmiany formatu" : "dowolne formatowanie")
    }

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: Theme.border
    }

    ColumnLayout {
        id: column
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 6
        spacing: 4

        RowLayout {
            Layout.fillWidth: true
            spacing: 4
            IconButton {
                iconName: bar.replaceMode ? "chevronDown" : "chevronRight"
                tip: bar.replaceMode ? "Ukryj zamianę" : "Pokaż zamianę"
                shortcutText: "Ctrl+H"
                onClicked: bar.replaceMode = !bar.replaceMode
            }
            TextField {
                id: findField
                Layout.preferredWidth: 260
                placeholderText: "Znajdź"
                selectByMouse: true
                text: bar.search ? bar.search.query : ""
                onTextEdited: bar.search.query = text
                Keys.onReturnPressed: function(event) {
                    if (event.modifiers & Qt.ShiftModifier) bar.search.previous()
                    else bar.search.next()
                }
                Keys.onEscapePressed: bar.closeRequested()
            }
            IconButton {
                glyph: "Aa"
                checked: bar.search && bar.search.caseSensitive
                tip: "Uwzględnij wielkość liter"
                onClicked: bar.search.caseSensitive = !bar.search.caseSensitive
            }
            IconButton {
                glyph: "„ab”"
                checked: bar.search && bar.search.wholeWords
                tip: "Tylko całe wyrazy"
                onClicked: bar.search.wholeWords = !bar.search.wholeWords
            }
            Button {
                id: findFormatButton
                text: "Format…"
                highlighted: bar.search && Object.keys(bar.search.findFormat).length > 0
                ToolTip.visible: hovered
                ToolTip.delay: 500
                ToolTip.text: "Szukaj: " + bar.describe(bar.search ? bar.search.findFormat : {}, false)
                onClicked: findPopup.open()
                FormatFilterPopup {
                    id: findPopup
                    y: findFormatButton.height + 2
                    value: bar.search ? bar.search.findFormat : ({})
                    onAccepted: function(f) { bar.search.findFormat = f }
                }
            }
            Text {
                Layout.leftMargin: 6
                text: bar.search ? bar.search.label : ""
                font.pointSize: Theme.fontSmall
                color: bar.search && bar.search.active && bar.search.count === 0 ? Theme.danger : Theme.textMuted
            }
            IconButton {
                iconName: "chevronUp"
                enabled: bar.search && bar.search.count > 0
                tip: "Poprzedni"
                shortcutText: "Shift+F3"
                onClicked: bar.search.previous()
            }
            IconButton {
                iconName: "chevronDown"
                enabled: bar.search && bar.search.count > 0
                tip: "Następny"
                shortcutText: "F3"
                onClicked: bar.search.next()
            }
            Item { Layout.fillWidth: true }
            Text {
                visible: bar.search && Object.keys(bar.search.findFormat).length > 0
                Layout.maximumWidth: 240
                elide: Text.ElideRight
                text: "Format: " + bar.describe(bar.search ? bar.search.findFormat : {}, false)
                font.pointSize: Theme.fontSmall
                color: Theme.accent
            }
            IconButton {
                iconName: "close"
                tip: "Zamknij (Esc)"
                onClicked: bar.closeRequested()
            }
        }

        RowLayout {
            visible: bar.replaceMode
            Layout.fillWidth: true
            Layout.leftMargin: Theme.controlHeight + 4
            spacing: 4
            TextField {
                id: replaceField
                Layout.preferredWidth: 260
                placeholderText: "Zamień na (puste + format = tylko zmiana formatu)"
                selectByMouse: true
                text: bar.search ? bar.search.replacement : ""
                onTextEdited: bar.search.replacement = text
                Keys.onReturnPressed: bar.search.replaceCurrent()
                Keys.onEscapePressed: bar.closeRequested()
            }
            Button {
                id: replaceFormatButton
                text: "Format…"
                highlighted: bar.search && Object.keys(bar.search.replaceFormat).length > 0
                ToolTip.visible: hovered
                ToolTip.delay: 500
                ToolTip.text: "Zamień na: " + bar.describe(bar.search ? bar.search.replaceFormat : {}, true)
                onClicked: replacePopup.open()
                FormatFilterPopup {
                    id: replacePopup
                    forReplace: true
                    y: replaceFormatButton.height + 2
                    value: bar.search ? bar.search.replaceFormat : ({})
                    onAccepted: function(f) { bar.search.replaceFormat = f }
                }
            }
            Button {
                text: "Zamień"
                enabled: bar.search && bar.search.count > 0
                onClicked: bar.search.replaceCurrent()
            }
            Button {
                text: "Zamień wszystko"
                enabled: bar.search && bar.search.count > 0
                onClicked: bar.search.replaceAll()
            }
            Item { Layout.fillWidth: true }
            Text {
                visible: bar.search && Object.keys(bar.search.replaceFormat).length > 0
                Layout.maximumWidth: 240
                elide: Text.ElideRight
                text: "Na: " + bar.describe(bar.search ? bar.search.replaceFormat : {}, true)
                font.pointSize: Theme.fontSmall
                color: Theme.accent
            }
        }
    }
}
