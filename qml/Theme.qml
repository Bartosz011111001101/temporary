pragma Singleton
import QtQuick

// Wspólne kolory, typografia i odstępy interfejsu.
QtObject {
    // Powierzchnie
    readonly property color window: "#f3f4f6"
    readonly property color workspace: "#e4e7eb"
    readonly property color panel: "#f8f9fa"
    readonly property color header: "#fcfcfd"
    readonly property color paper: "#ffffff"
    readonly property color border: "#d9dde2"
    readonly property color borderStrong: "#b9c0c8"
    readonly property color divider: "#e6e9ec"

    // Tekst
    readonly property color text: "#1d2329"
    readonly property color textMuted: "#5b6570"
    readonly property color textFaint: "#8b949d"
    readonly property color textOnAccent: "#ffffff"

    // Akcent i stany
    readonly property color accent: "#2a5d9f"
    readonly property color accentHover: "#224f88"
    readonly property color accentSoft: "#e5edf7"
    readonly property color accentSofter: "#f1f5fb"
    readonly property color hover: "#eceff2"
    readonly property color pressed: "#dfe3e8"
    readonly property color selected: "#dbe6f4"
    readonly property color focusRing: "#2a5d9f"
    readonly property color danger: "#b3261e"
    readonly property color dangerSoft: "#fbe9e7"
    readonly property color success: "#2e7d4f"
    readonly property color warning: "#9a6700"
    readonly property color warningSoft: "#fff4d6"
    readonly property color selectionText: "#b9d3f2"

    // Typografia interfejsu
    readonly property string uiFont: "Segoe UI"
    readonly property real fontSmall: 8.5
    readonly property real fontNormal: 9.5
    readonly property real fontLarge: 11
    readonly property real fontTitle: 12

    // Odstępy i rozmiary
    readonly property int spacingXs: 2
    readonly property int spacingS: 4
    readonly property int spacingM: 8
    readonly property int spacingL: 12
    readonly property int spacingXl: 16
    readonly property int radius: 4
    readonly property int controlHeight: 28
    readonly property int iconSize: 16
    readonly property int headerHeight: 46
    readonly property int toolbarHeight: 40
    readonly property int statusHeight: 26
    readonly property int navWidth: 270
    readonly property int propsWidth: 290

    // Strona: 96 px na cal
    readonly property real pxPerMm: 96 / 25.4
    readonly property real pxPerPt: 96 / 72
    readonly property real indentStep: 12.5 * pxPerMm

    readonly property var textColors: ["#1d2329", "#5b6570", "#b3261e", "#c2410c", "#a16207", "#2e7d4f",
        "#0f766e", "#2a5d9f", "#4338ca", "#7e22ce", "#be185d", "#000000"]
    readonly property var highlightColors: ["#fff3a3", "#ffd8a8", "#ffc9c9", "#d3f9d8", "#c5f6fa",
        "#d0ebff", "#e5dbff", "#f3d9fa", "#e9ecef"]
}
