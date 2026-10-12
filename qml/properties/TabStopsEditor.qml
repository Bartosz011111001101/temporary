import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../controls"

// Edycja tabulatorów akapitu: pozycja (cm), wyrównanie i wypełnienie (np. kropki do numeru strony).
ColumnLayout {
    id: editor

    property var tabs: []
    signal changed(var tabs)

    spacing: 6

    readonly property var aligns: [
        { key: "left", label: "Do lewej" }, { key: "center", label: "Do środka" },
        { key: "right", label: "Do prawej" }, { key: "decimal", label: "Dziesiętny" }
    ]
    readonly property var leaders: [
        { key: "none", label: "Brak" }, { key: "dot", label: "Kropki ……" },
        { key: "dash", label: "Kreski - - -" }, { key: "line", label: "Linia ___" }
    ]

    function indexOfKey(list, key) {
        for (var i = 0; i < list.length; ++i)
            if (list[i].key === key) return i
        return 0
    }

    function update(i, field, value) {
        var copy = JSON.parse(JSON.stringify(tabs))
        copy[i][field] = value
        copy.sort(function(a, b) { return a.position - b.position })
        changed(copy)
    }

    Text {
        Layout.fillWidth: true
        visible: editor.tabs.length === 0
        wrapMode: Text.Wrap
        text: "Brak własnych tabulatorów (Tab przesuwa tekst co 1,25 cm). Dodaj tabulator, np. do prawej z kropkami dla spisu treści."
        font.pointSize: Theme.fontSmall
        color: Theme.textFaint
    }

    Repeater {
        model: editor.tabs
        delegate: RowLayout {
            required property var modelData
            required property int index
            Layout.fillWidth: true
            spacing: 4
            NumberField {
                Layout.preferredWidth: 78
                realValue: modelData.position / 10
                realFrom: 0; realTo: 40; realStep: 0.5; decimals: 1; suffix: "cm"
                onEdited: function(v) { editor.update(index, "position", Math.round(v * 100) / 10) }
            }
            ComboBox {
                Layout.fillWidth: true
                model: editor.aligns
                textRole: "label"
                currentIndex: editor.indexOfKey(editor.aligns, modelData.align)
                onActivated: function(i) { editor.update(index, "align", editor.aligns[i].key) }
            }
            ComboBox {
                Layout.fillWidth: true
                model: editor.leaders
                textRole: "label"
                currentIndex: editor.indexOfKey(editor.leaders, modelData.leader)
                onActivated: function(i) { editor.update(index, "leader", editor.leaders[i].key) }
            }
            IconButton {
                iconName: "close"
                tip: "Usuń tabulator"
                onClicked: {
                    var copy = editor.tabs.slice()
                    copy.splice(index, 1)
                    editor.changed(copy)
                }
            }
        }
    }

    RowLayout {
        Button {
            text: "+ Tabulator"
            onClicked: {
                var copy = JSON.parse(JSON.stringify(editor.tabs))
                var last = copy.length ? copy[copy.length - 1].position : 0
                copy.push({ position: Math.min(400, last + 40), align: "left", leader: "none" })
                editor.changed(copy)
            }
        }
        Button {
            text: "Spis treści (kropki)"
            ToolTip.visible: hovered
            ToolTip.delay: 500
            ToolTip.text: "Tabulator do prawej krawędzi tekstu z kropkami"
            onClicked: editor.changed([{ position: 159, align: "right", leader: "dot" }])
        }
    }
}
