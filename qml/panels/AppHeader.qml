import QtQuick
import QtQuick.Controls
import QtQuick.Controls.impl
import QtQuick.Layouts
import QmlWord.Backend
import ".."
import "../controls"

// Górny pasek: dokument i stan zapisu, operacje na plikach, cofanie, eksport, strona, wyszukiwanie.
Rectangle {
    id: header

    property DocumentModel doc
    property SearchController search
    property bool navOpen: true
    property bool propsOpen: true
    property bool previewMode: false
    property bool compact: width < 1100
    property alias searchField: searchField

    signal toggleNav()
    signal toggleProps()
    signal newRequested()
    signal openRequested()
    signal saveRequested()
    signal saveAsRequested()
    signal exportRequested()
    signal pageSetupRequested()
    signal previewToggled()
    signal helpRequested()

    implicitHeight: Theme.headerHeight
    color: Theme.header

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 6
        anchors.rightMargin: 6
        spacing: 2

        IconButton {
            iconName: "panelLeft"
            checked: header.navOpen
            tip: header.navOpen ? "Ukryj panel sekcji" : "Pokaż panel sekcji"
            shortcutText: "Ctrl+Shift+1"
            onClicked: header.toggleNav()
        }

        Image {
            source: Qt.resolvedUrl("../icons/app.svg")
            sourceSize: Qt.size(22, 22)
            Layout.leftMargin: 4
        }

        Column {
            Layout.leftMargin: 6
            Layout.preferredWidth: Math.min(260, Math.max(120, header.width * 0.16))
            spacing: 0
            Text {
                width: parent.width
                text: header.doc ? header.doc.fileName : ""
                elide: Text.ElideMiddle
                font.family: Theme.uiFont
                font.pointSize: Theme.fontLarge
                font.weight: Font.DemiBold
                color: Theme.text
            }
            Row {
                spacing: 5
                Rectangle {
                    width: 7
                    height: 7
                    radius: 3.5
                    anchors.verticalCenter: parent.verticalCenter
                    color: header.doc && header.doc.modified ? Theme.warning : Theme.success
                }
                Text {
                    text: !header.doc ? "" : header.doc.modified ? "Niezapisane zmiany"
                          : header.doc.filePath ? "Wszystkie zmiany zapisane" : "Nowy dokument"
                    font.family: Theme.uiFont
                    font.pointSize: Theme.fontSmall
                    color: header.doc && header.doc.modified ? Theme.warning : Theme.textMuted
                }
            }
        }

        VSeparator {}

        IconButton { iconName: "new"; text: "Nowy"; showLabel: !header.compact; tip: "Nowy dokument"; shortcutText: "Ctrl+N"; onClicked: header.newRequested() }
        IconButton { iconName: "open"; text: "Otwórz"; showLabel: !header.compact; tip: "Otwórz dokument"; shortcutText: "Ctrl+O"; onClicked: header.openRequested() }
        IconButton { iconName: "save"; text: "Zapisz"; showLabel: !header.compact; tip: "Zapisz"; shortcutText: "Ctrl+S"; onClicked: header.saveRequested() }
        IconButton { iconName: "saveAs"; tip: "Zapisz jako…"; shortcutText: "Ctrl+Shift+S"; onClicked: header.saveAsRequested() }

        VSeparator {}

        IconButton {
            iconName: "undo"
            enabled: header.doc && header.doc.canUndo
            tip: header.doc && header.doc.canUndo ? "Cofnij: " + header.doc.undoText : "Cofnij"
            shortcutText: "Ctrl+Z"
            onClicked: header.doc.undo()
        }
        IconButton {
            iconName: "redo"
            enabled: header.doc && header.doc.canRedo
            tip: header.doc && header.doc.canRedo ? "Ponów: " + header.doc.redoText : "Ponów"
            shortcutText: "Ctrl+Y"
            onClicked: header.doc.redo()
        }

        VSeparator {}

        IconButton { iconName: "export"; text: "PDF"; showLabel: !header.compact; tip: "Eksportuj do PDF"; shortcutText: "Ctrl+Shift+E"; onClicked: header.exportRequested() }
        IconButton { iconName: "pageSetup"; tip: "Ustawienia strony"; onClicked: header.pageSetupRequested() }
        IconButton {
            iconName: header.previewMode ? "edit" : "preview"
            text: header.previewMode ? "Edycja" : "Podgląd stron"
            showLabel: !header.compact
            checked: header.previewMode
            tip: header.previewMode ? "Wróć do edycji" : "Podgląd stron (podział na strony jak w PDF)"
            shortcutText: "Ctrl+Shift+P"
            onClicked: header.previewToggled()
        }

        Item { Layout.fillWidth: true }

        // Wyszukiwanie
        Rectangle {
            Layout.preferredWidth: header.compact ? 210 : 290
            Layout.preferredHeight: Theme.controlHeight
            radius: Theme.radius
            color: Theme.paper
            border.width: searchField.activeFocus ? 2 : 1
            border.color: searchField.activeFocus ? Theme.focusRing : Theme.border

            IconImage {
                x: 8
                anchors.verticalCenter: parent.verticalCenter
                source: Qt.resolvedUrl("../icons/search.svg")
                sourceSize: Qt.size(14, 14)
                color: Theme.textMuted
            }
            TextField {
                id: searchField
                x: 26
                width: parent.width - x - resultLabel.width - navButtons.width - 6
                anchors.verticalCenter: parent.verticalCenter
                placeholderText: "Szukaj w dokumencie"
                font.pointSize: Theme.fontNormal
                background: Item {}
                leftPadding: 2
                selectByMouse: true
                Accessible.name: "Szukaj w dokumencie"
                onTextChanged: header.search.query = text
                Keys.onReturnPressed: function(event) {
                    if (event.modifiers & Qt.ShiftModifier) header.search.previous()
                    else header.search.next()
                }
                Keys.onEscapePressed: {
                    text = ""
                    header.search.clear()
                }
            }
            Text {
                id: resultLabel
                anchors.right: navButtons.left
                anchors.rightMargin: 2
                anchors.verticalCenter: parent.verticalCenter
                text: header.search ? header.search.label : ""
                font.family: Theme.uiFont
                font.pointSize: Theme.fontSmall
                color: header.search && header.search.query && header.search.count === 0 ? Theme.danger : Theme.textMuted
            }
            Row {
                id: navButtons
                anchors.right: parent.right
                anchors.rightMargin: 2
                anchors.verticalCenter: parent.verticalCenter
                IconButton {
                    implicitHeight: 24
                    implicitWidth: 24
                    iconName: "chevronUp"
                    enabled: header.search && header.search.count > 0
                    tip: "Poprzedni wynik"
                    shortcutText: "Shift+F3"
                    onClicked: header.search.previous()
                }
                IconButton {
                    implicitHeight: 24
                    implicitWidth: 24
                    iconName: "chevronDown"
                    enabled: header.search && header.search.count > 0
                    tip: "Następny wynik"
                    shortcutText: "F3"
                    onClicked: header.search.next()
                }
            }
        }

        IconButton {
            iconName: "info"
            tip: "Skróty klawiszowe"
            shortcutText: "F1"
            onClicked: header.helpRequested()
        }
        IconButton {
            iconName: "panelRight"
            checked: header.propsOpen
            tip: header.propsOpen ? "Ukryj panel właściwości" : "Pokaż panel właściwości"
            shortcutText: "Ctrl+Shift+2"
            onClicked: header.toggleProps()
        }
    }

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: Theme.border
    }
}
