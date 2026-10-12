import QtQuick
import QtQuick.Controls
import QtQuick.Controls.impl
import QmlWord.Backend
import ".."

// Lista wstawiania: kliknięcie wstawia element pod kursorem, przeciągnięcie – w wybrane miejsce.
Item {
    id: panel

    property DocumentModel doc
    property EditorController editor
    property DragController dragCtl

    readonly property var items: [
        { kind: "paragraph", label: "Akapit", hint: "Zwykły tekst", icon: "paragraph", options: {} },
        { kind: "title", label: "Tytuł", hint: "Tytuł dokumentu", icon: "title", options: {} },
        { kind: "heading", label: "Sekcja (Nagłówek 1)", hint: "Nowa sekcja główna", icon: "heading", options: { level: 1 } },
        { kind: "heading", label: "Podsekcja (Nagłówek 2)", hint: "Sekcja drugiego poziomu", icon: "subsection", options: { level: 2 } },
        { kind: "heading", label: "Nagłówek 3", hint: "Trzeci poziom", icon: "subsection", options: { level: 3 } },
        { kind: "table", label: "Tabela…", hint: "Wybierz liczbę wierszy i kolumn", icon: "table", options: {} },
        { kind: "image", label: "Obraz…", hint: "Plik PNG, JPG, GIF, BMP, SVG", icon: "image", options: {} },
        { kind: "caption", label: "Podpis", hint: "Pod zaznaczoną tabelą lub obrazem", icon: "caption", options: {}, noDrag: true },
        { kind: "pageBreak", label: "Podział strony", hint: "Kolejna treść od nowej strony", icon: "pageBreak", options: {} },
        { kind: "placeholder", label: "Pusty blok", hint: "Miejsce na treść do uzupełnienia", icon: "placeholder", options: {} }
    ]

    function activate(item) {
        if (item.kind === "table")
            editor.insertTableRequested()
        else if (item.kind === "image")
            editor.imageRequested("")
        else if (item.kind === "caption")
            editor.insertCaption()
        else
            editor.insert(item.kind, item.options)
    }

    ListView {
        id: list
        anchors.fill: parent
        anchors.margins: 6
        model: panel.items
        spacing: 2
        clip: true
        keyNavigationEnabled: true
        activeFocusOnTab: true
        currentIndex: 0
        Accessible.role: Accessible.List
        Accessible.name: "Lista wstawiania"
        Keys.onReturnPressed: panel.activate(panel.items[currentIndex])
        Keys.onSpacePressed: panel.activate(panel.items[currentIndex])

        header: Text {
            width: list.width
            bottomPadding: 8
            wrapMode: Text.Wrap
            text: "Kliknij, aby wstawić pod kursorem, lub przeciągnij do dokumentu."
            font.family: Theme.uiFont
            font.pointSize: Theme.fontSmall
            color: Theme.textMuted
        }

        delegate: Rectangle {
            id: entry
            required property var modelData
            required property int index
            width: list.width
            height: 44
            radius: Theme.radius
            color: drag.active ? Theme.accentSofter : hover.hovered ? Theme.hover : "transparent"
            border.width: list.currentIndex === index && list.activeFocus ? 2 : 0
            border.color: Theme.focusRing
            Accessible.role: Accessible.Button
            Accessible.name: modelData.label

            IconImage {
                x: 10
                anchors.verticalCenter: parent.verticalCenter
                source: Qt.resolvedUrl("../icons/" + entry.modelData.icon + ".svg")
                sourceSize: Qt.size(18, 18)
                color: Theme.accent
            }
            Column {
                x: 38
                width: parent.width - 44
                anchors.verticalCenter: parent.verticalCenter
                Text {
                    width: parent.width
                    text: entry.modelData.label
                    elide: Text.ElideRight
                    font.family: Theme.uiFont
                    font.pointSize: Theme.fontNormal
                    color: Theme.text
                }
                Text {
                    width: parent.width
                    text: entry.modelData.hint
                    elide: Text.ElideRight
                    font.family: Theme.uiFont
                    font.pointSize: Theme.fontSmall
                    color: Theme.textFaint
                }
            }

            HoverHandler {
                id: hover
                cursorShape: entry.modelData.noDrag ? Qt.PointingHandCursor : Qt.OpenHandCursor
            }
            TapHandler {
                onTapped: {
                    list.currentIndex = entry.index
                    panel.activate(entry.modelData)
                }
            }
            DragHandler {
                id: drag
                target: null
                enabled: !entry.modelData.noDrag
                dragThreshold: 6
                onActiveChanged: {
                    if (active) {
                        panel.doc.flush()
                        var kind = entry.modelData.kind
                        var opts = entry.modelData.options
                        if (kind === "title") { kind = "title" }
                        panel.dragCtl.begin("insert", "", "Wstaw: " + entry.modelData.label, kind, opts)
                        panel.dragCtl.move(centroid.scenePosition)
                    } else {
                        panel.dragCtl.finish(false)
                    }
                }
                onCentroidChanged: if (active) panel.dragCtl.move(centroid.scenePosition)
            }
        }
    }
}
