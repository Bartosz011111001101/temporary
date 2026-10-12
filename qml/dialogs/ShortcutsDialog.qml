import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

// Ściąga skrótów klawiszowych (F1).
Dialog {
    id: dialog

    title: "Skróty klawiszowe"
    modal: true
    anchors.centerIn: Overlay.overlay
    width: Math.min(720, Overlay.overlay ? Overlay.overlay.width - 40 : 720)
    height: Math.min(560, Overlay.overlay ? Overlay.overlay.height - 40 : 560)
    standardButtons: Dialog.Close
    focus: true

    readonly property var groups: [
        { title: "Plik", items: [["Ctrl+N", "Nowy dokument"], ["Ctrl+O", "Otwórz"], ["Ctrl+S", "Zapisz"],
                                 ["Ctrl+Shift+S", "Zapisz jako"], ["Ctrl+Shift+E", "Eksport PDF"], ["Ctrl+Shift+P", "Podgląd stron"]] },
        { title: "Edycja", items: [["Ctrl+Z", "Cofnij"], ["Ctrl+Y / Ctrl+Shift+Z", "Ponów"], ["Ctrl+X / C / V", "Wytnij / kopiuj / wklej"],
                                   ["Ctrl+F", "Szukaj"], ["F3 / Shift+F3", "Następny / poprzedni wynik"],
                                   ["Enter", "Nowy akapit"], ["Shift+Enter", "Nowy wiersz w akapicie"], ["Ctrl+Enter", "Podział strony"]] },
        { title: "Formatowanie", items: [["Ctrl+B / I / U", "Pogrubienie / kursywa / podkreślenie"], ["Ctrl+Shift+X", "Przekreślenie"],
                                         ["Ctrl+Spacja", "Wyczyść formatowanie"], ["Ctrl+L / E / R / J", "Wyrównanie"],
                                         ["Ctrl+Alt+0…3", "Tekst / nagłówki 1–3"], ["Ctrl+Shift+L", "Lista punktowana"], ["Ctrl+K", "Link"]] },
        { title: "Struktura", items: [["Alt+Shift+↑ / ↓", "Przenieś blok"], ["Ctrl+Shift+N", "Nowa sekcja"], ["Ctrl+Alt+T", "Wstaw tabelę"],
                                      ["Tab / Shift+Tab", "Następna komórka tabeli / wcięcie listy"],
                                      ["W panelu sekcji: Ctrl+↑/↓", "Kolejność sekcji"], ["W panelu sekcji: Ctrl+←/→", "Poziom sekcji"],
                                      ["W panelu sekcji: F2", "Zmień nazwę"]] },
        { title: "Widok", items: [["F6", "Przełącz: sekcje → dokument → właściwości"], ["Ctrl+Shift+1 / 2", "Pokaż/ukryj panele"],
                                  ["Ctrl++ / Ctrl+− / Ctrl+0", "Powiększenie"], ["Ctrl+kółko", "Powiększenie"]] }
    ]

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        GridLayout {
            width: parent.width
            columns: dialog.width > 600 ? 2 : 1
            columnSpacing: 24
            rowSpacing: 14
            Repeater {
                model: dialog.groups
                delegate: ColumnLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    spacing: 3
                    Text {
                        text: modelData.title
                        font.pointSize: Theme.fontLarge
                        font.weight: Font.DemiBold
                        color: Theme.text
                    }
                    Repeater {
                        model: modelData.items
                        delegate: RowLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            Text {
                                Layout.preferredWidth: 150
                                text: modelData[0]
                                font.family: "Consolas"
                                font.pointSize: Theme.fontSmall
                                color: Theme.accent
                                wrapMode: Text.Wrap
                            }
                            Text {
                                Layout.fillWidth: true
                                text: modelData[1]
                                font.pointSize: Theme.fontSmall
                                color: Theme.text
                                wrapMode: Text.Wrap
                            }
                        }
                    }
                }
            }
        }
    }
}
