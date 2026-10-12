import QtQuick
import QtQuick.Layouts
import ".."

// Grupa przycisków wyrównania (opcjonalnie bez „wyjustuj”).
RowLayout {
    id: selector

    property string value: "left"
    property bool allowJustify: true
    signal picked(string align)

    spacing: 2

    Repeater {
        model: [
            { a: "left", icon: "alignLeft", tip: "Do lewej" },
            { a: "center", icon: "alignCenter", tip: "Do środka" },
            { a: "right", icon: "alignRight", tip: "Do prawej" },
            { a: "justify", icon: "alignJustify", tip: "Wyjustuj" }
        ]
        delegate: IconButton {
            required property var modelData
            visible: selector.allowJustify || modelData.a !== "justify"
            iconName: modelData.icon
            tip: modelData.tip
            checked: selector.value === modelData.a
            onClicked: selector.picked(modelData.a)
        }
    }
}
