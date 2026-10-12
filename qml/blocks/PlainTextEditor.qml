import QtQuick
import QmlWord.Backend
import ".."

// Prosty edytor bez formatowania: opis sekcji i treść podpisu.
TextEdit {
    id: edit

    property DocumentModel doc
    property string placeholderText: ""
    property bool loading: false
    property bool dirty: false

    signal committed(string value)
    signal navigateUp(real x)
    signal navigateDown(real x)
    signal enterPressed()

    textFormat: TextEdit.PlainText
    wrapMode: TextEdit.Wrap
    selectByMouse: true
    activeFocusOnTab: true
    selectionColor: Theme.selectionText
    selectedTextColor: color
    Accessible.role: Accessible.EditableText
    Accessible.name: placeholderText

    function setTextSilently(value) {
        if (value === text)
            return
        loading = true
        text = value
        loading = false
        dirty = false
    }

    function commit() {
        timer.stop()
        if (!dirty)
            return
        dirty = false
        committed(text)
    }

    function focusAt(start, end) {
        forceActiveFocus()
        if (end < 0) end = length
        if (start === end) cursorPosition = Math.min(start, length)
        else select(Math.min(start, length), Math.min(end, length))
    }

    onTextChanged: {
        if (!loading) {
            dirty = true
            timer.restart()
        }
    }
    onActiveFocusChanged: if (!activeFocus) commit()

    Timer {
        id: timer
        interval: 500
        onTriggered: edit.commit()
    }

    Connections {
        target: edit.doc
        function onFlushRequested() { edit.commit() }
    }

    Component.onDestruction: commit()

    Keys.onPressed: function(event) {
        var ctrl = (event.modifiers & Qt.ControlModifier) !== 0
        if (ctrl && event.key === Qt.Key_Z) {
            commit()
            if (event.modifiers & Qt.ShiftModifier) doc.redo(); else doc.undo()
            event.accepted = true
        } else if (ctrl && event.key === Qt.Key_Y) {
            commit()
            doc.redo()
            event.accepted = true
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            commit()
            enterPressed()
            event.accepted = true
        } else if (event.key === Qt.Key_Up && cursorRectangle.y <= positionToRectangle(0).y + 1) {
            navigateUp(cursorRectangle.x)
            event.accepted = true
        } else if (event.key === Qt.Key_Down && cursorRectangle.y >= positionToRectangle(length).y - 1) {
            navigateDown(cursorRectangle.x)
            event.accepted = true
        }
    }

    HoverHandler {
        cursorShape: Qt.IBeamCursor
    }

    Text {
        visible: edit.length === 0 && edit.placeholderText !== ""
        text: edit.placeholderText
        font: edit.font
        color: Theme.textFaint
        width: edit.width
        horizontalAlignment: edit.horizontalAlignment
        elide: Text.ElideRight
    }
}
