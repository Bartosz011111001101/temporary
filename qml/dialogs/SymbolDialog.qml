import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

// Symbole i znaki specjalne (w tym twarda spacja i łącznik nierozdzielający).
Dialog {
    id: dialog

    signal symbolChosen(string text)
    property var recent: []

    title: "Symbole i znaki specjalne"
    modal: true
    anchors.centerIn: Overlay.overlay
    width: 560
    focus: true
    standardButtons: Dialog.Close

    readonly property var groups: [
        { title: "Typografia", chars: ["„", "”", "«", "»", "‚", "’", "–", "—", "…", "•", "·", "§", "¶", "†", "‡", "©", "®", "™", "°", "№"] },
        { title: "Matematyka", chars: ["±", "×", "÷", "≠", "≈", "≤", "≥", "∞", "√", "∑", "∏", "∫", "∂", "∆", "π", "µ", "‰", "¹", "²", "³", "½", "¼", "¾", "∈", "∉", "∩", "∪", "⊂", "∀", "∃"] },
        { title: "Greckie", chars: ["α", "β", "γ", "δ", "ε", "ζ", "η", "θ", "λ", "ξ", "ρ", "σ", "τ", "φ", "χ", "ψ", "ω", "Γ", "Δ", "Θ", "Λ", "Σ", "Φ", "Ψ", "Ω"] },
        { title: "Waluty i strzałki", chars: ["€", "£", "$", "¥", "¢", "₿", "←", "→", "↑", "↓", "↔", "⇒", "⇐", "⇔", "↵"] },
        { title: "Znaczniki", chars: ["✓", "✔", "✗", "✘", "★", "☆", "♥", "♦", "♣", "♠", "☐", "☑", "☒", "●", "○", "■", "□", "▲", "▼", "◆"] }
    ]
    readonly property var specials: [
        { label: "Twarda spacja", text: " ", hint: "Ctrl+Shift+Spacja – nie łamie wiersza (np. „5 kg”)" },
        { label: "Łącznik nierozdzielający", text: "‑", hint: "Myślnik, w miejscu którego wiersz się nie złamie" },
        { label: "Miękki łącznik", text: "­", hint: "Miejsce, w którym słowo może zostać podzielone" },
        { label: "Półpauza –", text: "–", hint: "Np. zakresy: 10–20" },
        { label: "Pauza —", text: "—", hint: "Myślnik w zdaniu" }
    ]

    function choose(text) {
        var r = recent.filter(function(c) { return c !== text })
        r.unshift(text)
        recent = r.slice(0, 16)
        symbolChosen(text)
    }

    ScrollView {
        anchors.fill: parent
        implicitHeight: 420
        contentWidth: availableWidth
        ColumnLayout {
            width: parent.width
            spacing: 10

            Text {
                visible: dialog.recent.length > 0
                text: "Ostatnio używane"
                font.weight: Font.DemiBold
                color: Theme.text
            }
            Flow {
                visible: dialog.recent.length > 0
                Layout.fillWidth: true
                spacing: 3
                Repeater {
                    model: dialog.recent
                    delegate: SymbolCell { required property string modelData; symbol: modelData; onPicked: dialog.choose(modelData) }
                }
            }

            Repeater {
                model: dialog.groups
                delegate: ColumnLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: modelData.title; font.weight: Font.DemiBold; color: Theme.text }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 3
                        Repeater {
                            model: modelData.chars
                            delegate: SymbolCell { required property string modelData; symbol: modelData; onPicked: dialog.choose(modelData) }
                        }
                    }
                }
            }

            Text { text: "Znaki specjalne"; font.weight: Font.DemiBold; color: Theme.text }
            Repeater {
                model: dialog.specials
                delegate: RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    Button {
                        Layout.preferredWidth: 190
                        text: modelData.label
                        onClicked: dialog.choose(modelData.text)
                    }
                    Text {
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        text: modelData.hint
                        font.pointSize: Theme.fontSmall
                        color: Theme.textMuted
                    }
                }
            }
        }
    }
}
