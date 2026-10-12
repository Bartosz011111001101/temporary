import QtQuick
import ".."

// Blok typu nieznanego tej wersji aplikacji – wyświetlany, ale zachowywany bez zmian.
Item {
    id: block

    property var blockData: ({})
    property real contentWidth: 600

    signal navigateUp(real x)
    signal navigateDown(real x)

    implicitHeight: box.height + 8

    function focusAt(start, end) {}
    function focusFromAbove(x) {}
    function focusFromBelow(x) {}

    Rectangle {
        id: box
        y: 4
        width: block.contentWidth
        height: label.implicitHeight + 16
        radius: 4
        color: "#f4f5f7"
        border.color: Theme.border
        Text {
            id: label
            x: 10
            y: 8
            width: parent.width - 20
            wrapMode: Text.Wrap
            font.family: Theme.uiFont
            font.pointSize: Theme.fontSmall
            color: Theme.textMuted
            text: "Nieobsługiwany element (typ „" + (block.blockData.type || "?")
                  + "”). Zostanie zachowany bez zmian przy zapisie."
        }
    }
}
