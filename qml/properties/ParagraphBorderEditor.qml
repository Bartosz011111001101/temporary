import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../controls"

// Obramowanie i cieniowanie akapitu. Sąsiednie akapity o tych samych ustawieniach
// dostają jedną wspólną ramkę.
ColumnLayout {
    id: editor

    property var para: ({})
    readonly property var border: para.border || ({ kind: "none", color: "#5b6570", width: 0.75 })
    signal changed(var patch)

    spacing: 6

    readonly property var kinds: [
        { key: "none", label: "Brak" }, { key: "box", label: "Ramka" }, { key: "top", label: "Linia u góry" },
        { key: "bottom", label: "Linia u dołu" }, { key: "topBottom", label: "Góra i dół" },
        { key: "left", label: "Pasek z lewej (akcent)" }
    ]

    function borderPatch(kind, color, width) {
        return { border: { kind: kind, color: color || editor.border.color, width: width || editor.border.width } }
    }

    FieldLabel { text: "Obramowanie" }
    ComboBox {
        Layout.fillWidth: true
        model: editor.kinds
        textRole: "label"
        currentIndex: {
            for (var i = 0; i < editor.kinds.length; ++i)
                if (editor.kinds[i].key === editor.border.kind) return i
            return 0
        }
        onActivated: function(i) { editor.changed(editor.borderPatch(editor.kinds[i].key)) }
    }
    RowLayout {
        visible: editor.border.kind !== "none"
        FieldLabel { text: "Kolor" }
        ColorButton {
            iconName: "borders"
            tip: "Kolor linii"
            colors: Theme.textColors
            currentColor: editor.border.color
            noneLabel: "Domyślny (szary)"
            onColorPicked: function(c) { editor.changed(editor.borderPatch(editor.border.kind, c || "#5b6570")) }
        }
        FieldLabel { text: "Grubość" }
        NumberField {
            Layout.preferredWidth: 90
            realValue: editor.border.width
            realFrom: 0.25; realTo: 6; realStep: 0.25; decimals: 2; suffix: "pt"
            onEdited: function(v) { editor.changed(editor.borderPatch(editor.border.kind, "", v)) }
        }
    }
    RowLayout {
        FieldLabel { text: "Cieniowanie (tło)" }
        ColorButton {
            iconName: "highlight"
            tip: "Kolor tła akapitu"
            colors: Theme.highlightColors
            currentColor: editor.para.shading || ""
            lastColor: "#e9ecef"
            noneLabel: "Bez tła"
            onColorPicked: function(c) { editor.changed({ shading: c }) }
        }
    }
}
