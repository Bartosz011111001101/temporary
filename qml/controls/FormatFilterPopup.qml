import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

// Wybór formatowania do wyszukiwania („szukaj tylko pogrubionego”) albo do zamiany
// („zamień na pogrubione, czerwone”). Każda cecha: dowolna / tak / nie.
Popup {
    id: popup

    property var value: ({})
    property bool forReplace: false
    signal accepted(var format)

    padding: 12
    focus: true
    width: 330

    readonly property var boolKeys: [
        { key: "bold", label: "Pogrubienie" }, { key: "italic", label: "Kursywa" },
        { key: "underline", label: "Podkreślenie" }, { key: "strike", label: "Przekreślenie" },
        { key: "smallCaps", label: "Kapitaliki" }
    ]
    readonly property var styles: [
        { key: "", label: "Dowolny" }, { key: "body", label: "Tekst podstawowy" }, { key: "title", label: "Tytuł" },
        { key: "h1", label: "Nagłówek 1" }, { key: "h2", label: "Nagłówek 2" }, { key: "h3", label: "Nagłówek 3" },
        { key: "h4", label: "Nagłówek 4" }, { key: "h5", label: "Nagłówek 5" }, { key: "h6", label: "Nagłówek 6" }
    ]
    property var draft: ({})

    onOpened: draft = JSON.parse(JSON.stringify(value || {}))

    function setKey(key, v) {
        var d = JSON.parse(JSON.stringify(draft))
        if (v === undefined || v === null) delete d[key]
        else d[key] = v
        draft = d
    }

    background: Rectangle {
        color: Theme.paper
        border.color: Theme.border
        radius: Theme.radius
    }

    contentItem: ColumnLayout {
        spacing: 6
        Text {
            text: popup.forReplace ? "Zamień na formatowanie" : "Szukaj tylko tekstu z formatowaniem"
            font.weight: Font.DemiBold
            color: Theme.text
        }
        Repeater {
            model: popup.boolKeys
            delegate: RowLayout {
                required property var modelData
                Layout.fillWidth: true
                Text {
                    Layout.fillWidth: true
                    text: modelData.label
                    color: Theme.text
                }
                ComboBox {
                    Layout.preferredWidth: 130
                    model: popup.forReplace ? ["bez zmian", "włącz", "wyłącz"] : ["dowolne", "tak", "nie"]
                    currentIndex: (popup.draft || {})[modelData.key] === true ? 1 : (popup.draft || {})[modelData.key] === false ? 2 : 0
                    onActivated: function(i) { popup.setKey(modelData.key, i === 0 ? null : i === 1) }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Text { Layout.fillWidth: true; text: "Kolor tekstu"; color: Theme.text }
            ColorButton {
                iconName: "textColor"
                colors: Theme.textColors
                currentColor: (popup.draft || {}).color || ""
                noneLabel: popup.forReplace ? "Bez zmian" : "Dowolny"
                onColorPicked: function(c) { popup.setKey("color", c || null) }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Text { Layout.fillWidth: true; text: "Zakreślenie"; color: Theme.text }
            ColorButton {
                iconName: "highlight"
                colors: Theme.highlightColors
                currentColor: (popup.draft || {}).highlight || ""
                lastColor: "#fff3a3"
                noneLabel: popup.forReplace ? "Bez zmian" : "Dowolne"
                onColorPicked: function(c) { popup.setKey("highlight", c || null) }
            }
        }
        RowLayout {
            visible: !popup.forReplace
            Layout.fillWidth: true
            Text { Layout.fillWidth: true; text: "Styl akapitu"; color: Theme.text }
            ComboBox {
                Layout.preferredWidth: 160
                model: popup.styles
                textRole: "label"
                currentIndex: {
                    for (var i = 0; i < popup.styles.length; ++i)
                        if (popup.styles[i].key === ((popup.draft || {}).style || "")) return i
                    return 0
                }
                onActivated: function(i) { popup.setKey("style", popup.styles[i].key || null) }
            }
        }
        RowLayout {
            Layout.topMargin: 6
            Button {
                text: "Wyczyść"
                onClicked: { popup.draft = {}; popup.accepted({}); popup.close() }
            }
            Item { Layout.fillWidth: true }
            Button {
                text: "Zastosuj"
                highlighted: true
                onClicked: { popup.accepted(popup.draft); popup.close() }
            }
        }
    }
}
