import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QmlWord.Backend
import ".."
import "../controls"

// Pasek stanu: bieżąca sekcja, statystyki, kopia robocza, liczba stron i powiększenie.
Rectangle {
    id: bar

    property DocumentModel doc
    property EditorController editor
    property real zoom: 1
    property string draftTime: ""
    property bool previewMode: false
    property int pageCount: 0
    signal zoomRequested(real value)

    readonly property var section: doc && editor && editor.currentSectionId && doc.revision >= 0
                                   ? doc.sectionInfo(editor.currentSectionId) : ({})

    implicitHeight: Theme.statusHeight
    color: Theme.header

    Rectangle {
        width: parent.width
        height: 1
        color: Theme.border
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 10
        anchors.rightMargin: 6
        spacing: 14

        Text {
            Layout.maximumWidth: bar.width * 0.4
            elide: Text.ElideRight
            text: bar.section.title !== undefined ? "Sekcja " + bar.section.number + ": " + bar.section.title : "Poza sekcjami"
            font.family: Theme.uiFont
            font.pointSize: Theme.fontSmall
            color: Theme.textMuted
        }
        Text {
            text: "Słowa: " + (bar.doc ? bar.doc.wordCount : 0)
            font.family: Theme.uiFont
            font.pointSize: Theme.fontSmall
            color: Theme.textMuted
        }
        Text {
            visible: bar.previewMode && bar.pageCount > 0
            text: "Strony: " + bar.pageCount
            font.family: Theme.uiFont
            font.pointSize: Theme.fontSmall
            color: Theme.textMuted
        }
        Item { Layout.fillWidth: true }
        Text {
            visible: bar.draftTime !== ""
            text: "Kopia robocza: " + bar.draftTime
            font.family: Theme.uiFont
            font.pointSize: Theme.fontSmall
            color: Theme.textFaint
        }

        IconButton {
            implicitHeight: 22
            implicitWidth: 22
            iconName: "zoomOut"
            tip: "Pomniejsz"
            shortcutText: "Ctrl+−"
            enabled: bar.zoom > 0.5
            onClicked: bar.zoomRequested(bar.zoom - 0.1)
        }
        Slider {
            Layout.preferredWidth: 110
            from: 0.5
            to: 2.0
            stepSize: 0.05
            value: bar.zoom
            onMoved: bar.zoomRequested(value)
            Accessible.name: "Powiększenie"
        }
        IconButton {
            implicitHeight: 22
            implicitWidth: 22
            iconName: "zoomIn"
            tip: "Powiększ"
            shortcutText: "Ctrl++"
            enabled: bar.zoom < 2.0
            onClicked: bar.zoomRequested(bar.zoom + 0.1)
        }
        Button {
            flat: true
            implicitHeight: 22
            text: Math.round(bar.zoom * 100) + "%"
            font.pointSize: Theme.fontSmall
            ToolTip.visible: hovered
            ToolTip.text: "Przywróć 100% (Ctrl+0)"
            onClicked: bar.zoomRequested(1.0)
        }
    }
}
