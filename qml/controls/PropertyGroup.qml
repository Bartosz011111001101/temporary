import QtQuick
import QtQuick.Layouts
import ".."

// Grupa właściwości w prawym panelu: nagłówek + zawartość, oddzielone cienką linią.
ColumnLayout {
    id: group

    property string title: ""
    default property alias content: body.data

    Layout.fillWidth: true
    spacing: 6

    Rectangle {
        Layout.fillWidth: true
        Layout.topMargin: 4
        implicitHeight: 1
        color: Theme.divider
    }

    Text {
        text: group.title.toUpperCase()
        font.family: Theme.uiFont
        font.pointSize: Theme.fontSmall - 0.5
        font.letterSpacing: 0.6
        font.weight: Font.DemiBold
        color: Theme.textMuted
        Layout.topMargin: 4
    }

    ColumnLayout {
        id: body
        Layout.fillWidth: true
        spacing: 8
    }
}
