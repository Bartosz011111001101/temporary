import QtQuick

// Wspólny stan przeciągania: bloki dokumentu, sekcje w nawigacji i elementy z listy wstawiania.
QtObject {
    id: drag

    property bool active: false
    property string kind: ""          // "block" | "section" | "insert"
    property string sourceId: ""
    property string insertKind: ""
    property var insertOptions: ({})
    property string label: ""
    property point scenePos: Qt.point(0, 0)
    // Wynik oceny miejsca upuszczenia (ustawiany przez cel pod kursorem).
    property bool overTarget: false
    property bool dropAllowed: false
    property string problem: ""

    signal released(bool cancelled)

    function begin(k, id, text, insKind, options) {
        kind = k
        sourceId = id || ""
        insertKind = insKind || ""
        insertOptions = options || {}
        label = text
        overTarget = false
        dropAllowed = false
        problem = ""
        active = true
    }

    function move(p) {
        if (active)
            scenePos = p
    }

    function finish(cancelled) {
        if (!active)
            return
        released(cancelled === true)
        active = false
        kind = ""
        sourceId = ""
        insertKind = ""
        overTarget = false
        dropAllowed = false
        problem = ""
    }
}
