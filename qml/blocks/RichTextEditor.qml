import QtQuick
import QtQuick.Controls
import QmlWord.Backend
import ".."

// Edytor tekstu sformatowanego jednego bloku (akapit, nagłówek, komórka tabeli).
// Treść wczytuje i zatwierdza przez RichText (przebiegi modelu), nie przez HTML.
TextEdit {
    id: edit
    objectName: inCell ? "" : "editor:" + blockId

    property DocumentModel doc
    property EditorController editor
    property string blockId: ""
    property int cellRow: -1
    property int cellCol: -1
    readonly property bool inCell: cellRow >= 0
    property bool listItem: false
    property string placeholderText: ""
    property bool placeholderAlways: false
    property var styleFont: ({})
    property bool loading: false
    property bool dirty: false
    // Komórka z formułą: tekst jest wynikiem, edycja przez okno formuły.
    property bool formulaCell: false
    // Tabulatory akapitu [{ position (mm), align, leader }] – do rysowania wypełnienia kropkami.
    property var tabStops: []
    property var leaderSpans: []
    readonly property bool showMarks: editor ? editor.showMarks : false

    signal navigateUp(real x)
    signal navigateDown(real x)
    signal tabPressed(bool backwards)
    signal escapePressed()

    textFormat: TextEdit.RichText
    wrapMode: TextEdit.Wrap
    selectByMouse: true
    persistentSelection: true
    activeFocusOnTab: true
    readOnly: formulaCell
    textMargin: 0
    selectionColor: Theme.selectionText
    selectedTextColor: color
    font.family: styleFont.family || "Calibri"
    font.pointSize: styleFont.pointSize || 11
    font.bold: !!styleFont.bold
    font.italic: !!styleFont.italic
    color: styleFont.color || Theme.text
    Accessible.role: Accessible.EditableText
    Accessible.name: placeholderText

    // --- wczytywanie i zatwierdzanie --------------------------------------------
    function load(runs, para) {
        loading = true
        RichText.load(textDocument, runs || [], para || {})
        if (showMarks)
            RichText.setShowMarks(textDocument, true)
        loading = false
        dirty = false
        Qt.callLater(updateLeaders)
    }

    function reload(runs, para) {
        var s = selectionStart, e = selectionEnd
        commitTimer.stop()
        load(runs, para)
        if (activeFocus || s !== e) {
            var len = length
            select(Math.min(s, len), Math.min(e, len))
        }
    }

    function commit() {
        commitTimer.stop()
        if (!dirty || !doc || !blockId || formulaCell)
            return
        dirty = false
        if (inCell)
            doc.setCellRuns(blockId, cellRow, cellCol, RichText.runs(textDocument))
        else if (RichText.blockCount(textDocument) > 1)
            doc.setBlockParagraphs(blockId, RichText.paragraphs(textDocument))
        else
            doc.setBlockRuns(blockId, RichText.runs(textDocument))
    }

    onTextChanged: {
        if (loading)
            return
        dirty = true
        if (!inCell && RichText.blockCount(textDocument) > 1)
            Qt.callLater(commit)   // wklejono kilka akapitów – od razu rozbij na bloki
        else
            commitTimer.restart()
        if (tabStops.length)
            Qt.callLater(updateLeaders)
    }
    onWidthChanged: if (tabStops.length) Qt.callLater(updateLeaders)
    onTabStopsChanged: Qt.callLater(updateLeaders)
    onShowMarksChanged: RichText.setShowMarks(textDocument, showMarks)

    Timer {
        id: commitTimer
        interval: 450
        onTriggered: edit.commit()
    }

    Connections {
        target: edit.doc
        function onFlushRequested() { edit.commit() }
    }

    Component.onDestruction: {
        commit()
        if (editor)
            editor.release(edit)
    }

    // --- wypełnienie tabulatorów (kropki, kreski, linia) ---------------------------------
    function updateLeaders() {
        var stops = tabStops || []
        if (!stops.some(function(t) { return t.leader && t.leader !== "none" })) {
            if (leaderSpans.length) leaderSpans = []
            return
        }
        var out = []
        var positions = RichText.tabPositions(textDocument)
        for (var i = 0; i < positions.length; ++i) {
            var p = positions[i]
            var r1 = positionToRectangle(p), r2 = positionToRectangle(p + 1)
            if (Math.abs(r1.y - r2.y) > 1 || r2.x - r1.x < 8)
                continue
            var leader = "none"
            for (var k = 0; k < stops.length; ++k) {
                if (stops[k].position * Theme.pxPerMm >= r2.x - 1) { leader = stops[k].leader; break }
            }
            if (leader !== "none")
                out.push({ x: r1.x + 2, w: r2.x - r1.x - 4, y: r1.y + r1.height * 0.8, leader: leader })
        }
        leaderSpans = out
    }

    Repeater {
        model: edit.leaderSpans
        delegate: Canvas {
            required property var modelData
            x: modelData.x
            y: modelData.y - 2
            width: modelData.w
            height: 4
            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                ctx.strokeStyle = edit.color
                ctx.fillStyle = edit.color
                if (modelData.leader === "dot") {
                    for (var x = 1; x < width; x += 4)
                        ctx.fillRect(x, 1, 1.2, 1.2)
                } else {
                    ctx.lineWidth = 0.8
                    if (modelData.leader === "dash") ctx.setLineDash([4, 3])
                    ctx.beginPath()
                    ctx.moveTo(0, 2)
                    ctx.lineTo(width, 2)
                    ctx.stroke()
                }
            }
        }
    }

    // Znak końca akapitu (¶) przy włączonych znakach niedrukowalnych.
    Text {
        visible: edit.showMarks && !edit.inCell
        readonly property rect endRect: edit.positionToRectangle(edit.length)
        x: endRect.x + 2
        y: endRect.y
        text: "¶"
        font.family: edit.font.family
        font.pointSize: edit.font.pointSize
        color: Theme.accent
        opacity: 0.55
    }

    // --- fokus i stan formatowania ------------------------------------------------
    function focusEditor() {
        forceActiveFocus()
    }

    function focusAt(start, end) {
        forceActiveFocus()
        var len = length
        start = Math.max(0, Math.min(start, len))
        end = end < 0 ? len : Math.max(0, Math.min(end, len))
        if (start === end)
            cursorPosition = start
        else
            select(start, end)
    }

    function focusAtX(x, fromBottom) {
        forceActiveFocus()
        var y = fromBottom ? Math.max(0, contentHeight - 2) : 1
        cursorPosition = positionAt(x, y)
    }

    function clearSelection() {
        deselect()
    }

    function currentFormat() {
        return RichText.formatAt(textDocument, selectionStart, selectionEnd)
    }

    function toggleFormat(key) {
        var f = currentFormat()
        var props = {}
        props[key] = !f[key]
        applyFormat(props)
    }

    function applyFormat(props) {
        if (formulaCell)
            return
        var s = selectionStart, e = selectionEnd
        RichText.mergeFormat(textDocument, s, e, props)
        dirty = true
        commit()
        if (s !== e)
            select(s, e)
        if (editor)
            editor.refreshFormat()
    }

    function insertLink(text, url) {
        if (selectionStart !== selectionEnd) {
            applyFormat({ link: url })
            return
        }
        var pos = RichText.insertLink(textDocument, cursorPosition, text || url, url)
        cursorPosition = pos
        dirty = true
        commit()
    }

    function removeLink() {
        var l = RichText.linkAt(textDocument, cursorPosition)
        if (l.start >= 0) {
            RichText.mergeFormat(textDocument, l.start, l.end, { link: "" })
            dirty = true
            commit()
        }
    }

    function linkUnderCursor() {
        return RichText.linkAt(textDocument, cursorPosition).url
    }

    function insertLineBreak() {
        if (selectionStart !== selectionEnd)
            remove(selectionStart, selectionEnd)
        var pos = cursorPosition
        RichText.insertPlainText(textDocument, pos, "\n")
        cursorPosition = pos + 1
    }

    function isFirstLine() {
        return cursorRectangle.y <= positionToRectangle(0).y + 1
    }

    function isLastLine() {
        return cursorRectangle.y >= positionToRectangle(length).y - 1
    }

    function splitHere() {
        if (listItem && length === 0) {
            doc.setParagraph(blockId, { list: "none" })   // Enter na pustym punkcie kończy listę
            return
        }
        var s = selectionStart, e = selectionEnd
        var before = RichText.runsInRange(textDocument, 0, s)
        var after = RichText.runsInRange(textDocument, e, length)
        dirty = false
        commitTimer.stop()
        doc.splitBlock(blockId, before, after)
    }

    function mergeUp() {
        var runs = RichText.runs(textDocument)
        dirty = false
        commitTimer.stop()
        if (!doc.mergeWithPrevious(blockId, runs)) {
            dirty = true
            navigateUp(0)
        }
    }

    onActiveFocusChanged: {
        if (activeFocus) {
            if (editor)
                editor.activate(edit)
        } else {
            commit()
        }
    }
    onCursorRectangleChanged: {
        if (activeFocus && editor) {
            editor.ensureVisible(edit, cursorRectangle)
            Qt.callLater(editor.refreshFormat)
        }
    }
    onCursorPositionChanged: if (editor && editor.rangeActive && !inCell) editor.updateRangeFocus(blockId, cursorPosition)
    onSelectionStartChanged: if (activeFocus && editor) Qt.callLater(editor.refreshFormat)
    onSelectionEndChanged: if (activeFocus && editor) Qt.callLater(editor.refreshFormat)

    // --- klawiatura -----------------------------------------------------------------------
    Keys.onPressed: function(event) {
        var ctrl = (event.modifiers & Qt.ControlModifier) !== 0
        var shift = (event.modifiers & Qt.ShiftModifier) !== 0
        var alt = (event.modifiers & Qt.AltModifier) !== 0
        var ranged = editor && editor.rangeActive

        // Zaznaczenie obejmujące wiele bloków
        if (ranged) {
            if (ctrl && !alt && event.key === Qt.Key_C) { editor.copy(); event.accepted = true; return }
            if (ctrl && !alt && event.key === Qt.Key_X) { editor.cut(); event.accepted = true; return }
            if (ctrl && !alt && event.key === Qt.Key_V) { editor.paste(shift ? "plain" : "source"); event.accepted = true; return }
            if (event.key === Qt.Key_Delete || event.key === Qt.Key_Backspace) {
                editor.deleteRange()
                event.accepted = true
                return
            }
            if (!ctrl && !alt && event.text.length > 0 && event.text.charCodeAt(0) >= 32) {
                editor.typeOverRange(event.text)
                event.accepted = true
                return
            }
            if (!shift && [Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down, Qt.Key_Home, Qt.Key_End,
                           Qt.Key_PageUp, Qt.Key_PageDown].indexOf(event.key) >= 0) {
                editor.clearRange()   // zwykła nawigacja kończy zaznaczenie
            }
        }

        if (ctrl && event.key === Qt.Key_Z) {
            commit()
            if (shift) doc.redo(); else doc.undo()
            event.accepted = true
        } else if (ctrl && event.key === Qt.Key_Y) {
            commit()
            doc.redo()
            event.accepted = true
        } else if (ctrl && alt && event.key === Qt.Key_V) {
            editor.pasteSpecialRequested()
            event.accepted = true
        } else if (ctrl && event.key === Qt.Key_V) {
            editor.paste(shift ? "plain" : "source")
            event.accepted = true
        } else if (ctrl && event.key === Qt.Key_A && !inCell && length > 0
                   && selectionStart === 0 && selectionEnd === length) {
            editor.selectAllDocument()   // drugie Ctrl+A zaznacza cały dokument
            event.accepted = true
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            if (formulaCell) {
                editor.formulaRequested(blockId, cellRow, cellCol)
            } else if (ctrl) {
                commit()
                editor.insert("pageBreak", {})
            } else if (shift) {
                insertLineBreak()
            } else if (inCell) {
                insertLineBreak()
            } else {
                splitHere()
            }
            event.accepted = true
        } else if (event.key === Qt.Key_Backspace && !ctrl && !inCell
                   && selectionStart === selectionEnd && cursorPosition === 0) {
            mergeUp()
            event.accepted = true
        } else if (event.key === Qt.Key_Delete && !inCell && length === 0) {
            dirty = false
            doc.removeEmptyAndFocusNext(blockId)
            event.accepted = true
        } else if (event.key === Qt.Key_Up && shift && !alt && !ctrl && !inCell && isFirstLine()) {
            editor.extendRange(edit, -1)
            event.accepted = true
        } else if (event.key === Qt.Key_Down && shift && !alt && !ctrl && !inCell && isLastLine()) {
            editor.extendRange(edit, 1)
            event.accepted = true
        } else if (event.key === Qt.Key_Up && !shift && !alt && !ctrl && isFirstLine()) {
            navigateUp(cursorRectangle.x)
            event.accepted = true
        } else if (event.key === Qt.Key_Down && !shift && !alt && !ctrl && isLastLine()) {
            navigateDown(cursorRectangle.x)
            event.accepted = true
        } else if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) {
            tabPressed(shift || event.key === Qt.Key_Backtab)
            event.accepted = true
        } else if (event.key === Qt.Key_Escape) {
            escapePressed()
            event.accepted = false
        }
    }

    // --- mysz: linki (Ctrl+klik), Shift+klik w innym bloku, malarz formatów, menu ---------
    TapHandler {
        acceptedButtons: Qt.LeftButton
        acceptedModifiers: Qt.ControlModifier
        onTapped: function(eventPoint) {
            var url = edit.linkAt(eventPoint.position.x, eventPoint.position.y)
            if (url)
                AppUtils.openExternal(url)
        }
    }

    TapHandler {
        acceptedButtons: Qt.LeftButton
        acceptedModifiers: Qt.ShiftModifier
        onTapped: function(eventPoint) {
            if (edit.editor && !edit.inCell)
                edit.editor.extendRangeTo(edit.blockId, edit.positionAt(eventPoint.position.x, eventPoint.position.y))
        }
    }

    PointHandler {
        acceptedButtons: Qt.LeftButton
        onActiveChanged: {
            if (!active && edit.editor && edit.editor.painterActive)
                Qt.callLater(function() { edit.editor.applyPainter(edit) })
        }
    }

    TapHandler {
        acceptedButtons: Qt.RightButton
        onTapped: function(eventPoint) {
            if (edit.editor && edit.editor.rangeActive) {
                edit.editor.contextMenuRequested("text", { blockId: edit.blockId, row: -1, col: -1, editorItem: edit })
                return
            }
            var pos = edit.positionAt(eventPoint.position.x, eventPoint.position.y)
            if (pos < edit.selectionStart || pos > edit.selectionEnd || edit.selectionStart === edit.selectionEnd)
                edit.cursorPosition = pos
            edit.forceActiveFocus()
            if (edit.editor)
                edit.editor.contextMenuRequested(edit.inCell ? "table" : "text",
                                                 { blockId: edit.blockId, row: edit.cellRow, col: edit.cellCol, editorItem: edit })
        }
        onDoubleTapped: {}
    }

    TapHandler {
        acceptedButtons: Qt.LeftButton
        enabled: edit.formulaCell
        onDoubleTapped: edit.editor.formulaRequested(edit.blockId, edit.cellRow, edit.cellCol)
    }

    HoverHandler {
        cursorShape: edit.editor && edit.editor.painterActive ? Qt.CrossCursor : Qt.IBeamCursor
    }

    Text {
        visible: edit.length === 0 && edit.placeholderText !== "" && (edit.activeFocus || edit.placeholderAlways)
        text: edit.placeholderText
        font: edit.font
        color: Theme.textFaint
        width: edit.width
        elide: Text.ElideRight
    }
}
