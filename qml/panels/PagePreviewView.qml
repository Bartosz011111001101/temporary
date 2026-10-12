import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import QmlWord.Backend
import ".."
import "../controls"

// Podgląd stron: rzeczywisty podział na strony (ten sam układ, który trafia do PDF).
Rectangle {
    id: view

    property DocumentModel doc
    property PageLayout pageLayout
    property real zoom: 1
    signal exportRequested()
    signal closeRequested()

    color: Theme.workspace

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 38
            color: Theme.accentSofter
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 8
                Text {
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                    text: "Podgląd stron – tak dokument wygląda po eksporcie do PDF ("
                          + (view.pageLayout ? view.pageLayout.pageCount : 0) + " str.). "
                          + "Nagłówki tabel powtarzają się na kolejnych stronach, jeśli włączono tę opcję."
                    font.family: Theme.uiFont
                    font.pointSize: Theme.fontSmall
                    color: Theme.text
                }
                Button { text: "Eksportuj PDF…"; onClicked: view.exportRequested() }
                Button { text: "Wróć do edycji"; highlighted: true; onClicked: view.closeRequested() }
            }
        }

        ListView {
            id: pages
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 20
            topMargin: 24
            bottomMargin: 24
            model: view.pageLayout ? view.pageLayout.pageCount : 0
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            activeFocusOnTab: true
            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_PageDown) { contentY += height * 0.9; event.accepted = true }
                else if (event.key === Qt.Key_PageUp) { contentY -= height * 0.9; event.accepted = true }
                else if (event.key === Qt.Key_Escape) { view.closeRequested(); event.accepted = true }
            }

            delegate: Item {
                required property int index
                width: pages.width
                height: page.height
                Rectangle {
                    // cień kartki
                    x: page.x + 2
                    y: 3
                    width: page.width
                    height: page.height
                    color: "#00000018"
                    radius: 1
                }
                PagePreview {
                    id: page
                    pageLayout: view.pageLayout
                    pageIndex: index
                    pixelRatio: Screen.devicePixelRatio
                    width: Math.min(pages.width - 48, view.pageLayout.pageWidth * view.zoom)
                    height: width * view.pageLayout.pageHeight / view.pageLayout.pageWidth
                    x: (pages.width - width) / 2
                }
                Text {
                    anchors.top: page.bottom
                    anchors.topMargin: 3
                    anchors.horizontalCenter: page.horizontalCenter
                    text: "Strona " + (index + 1)
                    font.pointSize: Theme.fontSmall - 0.5
                    color: Theme.textFaint
                }
            }
        }
    }
}
