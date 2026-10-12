import QtQuick
import QmlWord.Backend

// Stan edycji współdzielony przez paski narzędzi, panele i bloki dokumentu:
// bieżący blok i edytor, zaznaczenie obejmujące wiele bloków, malarz formatów, schowek.
QtObject {
    id: ctl

    property DocumentModel doc

    // Zaznaczony blok i aktywny edytor tekstu (akapit, nagłówek albo komórka tabeli).
    property string currentBlockId: ""
    property Item activeEditor: null
    property int activeRow: -1
    property int activeCol: -1
    // Zaznaczenie prostokąta komórek: { blockId, r1, c1, r2, c2 } albo null
    property var tableSelection: null
    // Efektywny format znaków pod kursorem.
    property var format: ({})

    // Zaznaczenie przez wiele bloków: kotwica i fokus { blockId, pos }.
    property var rangeAnchor: null
    property var rangeFocus: null
    readonly property bool rangeActive: rangeAnchor !== null && rangeFocus !== null
                                        && rangeAnchor.blockId !== rangeFocus.blockId
    // Indeksy zaznaczenia w kolejności dokumentu (przeliczane przy każdej zmianie dokumentu).
    readonly property var range: {
        if (!rangeActive || !doc || doc.revision < 0)
            return null
        var a = doc.indexOf(rangeAnchor.blockId), f = doc.indexOf(rangeFocus.blockId)
        if (a < 0 || f < 0)
            return null
        var forward = a < f
        return {
            first: forward ? a : f, last: forward ? f : a,
            firstId: forward ? rangeAnchor.blockId : rangeFocus.blockId,
            lastId: forward ? rangeFocus.blockId : rangeAnchor.blockId,
            firstPos: forward ? rangeAnchor.pos : rangeFocus.pos,
            lastPos: forward ? rangeFocus.pos : rangeAnchor.pos
        }
    }

    // Malarz formatów: { char: {...}, para: {...} } albo null; sticky = zostaje włączony.
    property var painter: null
    property bool painterSticky: false
    readonly property bool painterActive: painter !== null

    // Znaki niedrukowalne (¶, kropki spacji).
    property bool showMarks: false

    readonly property var currentData: (doc && doc.revision >= 0 && currentBlockId) ? doc.blockData(currentBlockId) : ({})
    readonly property string currentType: currentData.type || ""
    readonly property bool currentIsText: currentType === "paragraph" || currentType === "heading"
    readonly property bool inTableCell: currentType === "table" && activeRow >= 0
    readonly property bool hasTextEditor: rangeActive || (activeEditor !== null && (currentIsText || inTableCell || currentType === "placeholder"))
    readonly property string currentStyle: currentType === "heading" ? "h" + currentData.level
                                         : currentType === "paragraph" ? (currentData.style || "body") : ""
    readonly property var currentPara: currentData.para || ({})
    readonly property string currentSectionId: (doc && currentBlockId && doc.revision >= 0) ? doc.sectionOf(currentBlockId) : ""
    readonly property bool currentFormulaCell: inTableCell && doc && doc.revision >= 0
                                               && doc.cellFormula(currentBlockId, activeRow, activeCol) !== ""

    signal contextMenuRequested(string kind, var payload)
    signal ensureVisibleRequested(Item item, rect area)
    signal insertTableRequested()
    signal linkRequested()
    signal imageRequested(string targetBlockId)
    // options: { title, message, acceptText, secondaryText?, action(choice) }
    signal confirmRequested(var options)
    signal pasteSpecialRequested()
    signal symbolsRequested()
    signal formulaRequested(string blockId, int row, int col)
    // kind: "textToTable" | "tableToText"
    signal convertRequested(string kind, string blockId)
    signal rangeApplied()

    function ensureVisible(item, area) {
        ensureVisibleRequested(item, area)
    }

    // Edytor może być w trakcie niszczenia (np. blok zmienił typ) – wtedy po prostu go pomijamy.
    function safeDeselect(ed) {
        try { ed.clearSelection() } catch (e) {}
    }

    function release(editorItem) {
        if (activeEditor === editorItem)
            activeEditor = null
    }

    function select(blockId) {
        if (activeEditor && activeEditor.blockId !== blockId) {
            safeDeselect(activeEditor)
            activeEditor = null
        }
        currentBlockId = blockId
        activeRow = -1
        activeCol = -1
        if (tableSelection && tableSelection.blockId !== blockId)
            tableSelection = null
    }

    // Pozycja kursora w poprzednio aktywnym edytorze (kotwica dla Shift+klik w innym bloku).
    property var previousCaret: null
    property var recentAnchor: null
    property double recentAnchorTime: 0

    function caretOf(ed) {
        try {
            return { blockId: ed.blockId, pos: ed.cursorPosition === ed.selectionEnd ? ed.selectionStart : ed.selectionEnd }
        } catch (e) {
            return null
        }
    }

    function activate(editor) {
        if (activeEditor && activeEditor !== editor) {
            if (activeEditor.cellRow < 0)
                previousCaret = caretOf(activeEditor)
            if (!rangeActive)
                safeDeselect(activeEditor)
        }
        activeEditor = editor
        currentBlockId = editor.blockId
        activeRow = editor.cellRow
        activeCol = editor.cellCol
        if (tableSelection && (tableSelection.blockId !== editor.blockId || editor.cellRow < 0))
            tableSelection = null
        refreshFormat()
    }

    function refreshFormat() {
        format = activeEditor ? activeEditor.currentFormat() : ({})
    }

    function restoreFocus() {
        if (activeEditor)
            Qt.callLater(function() { if (activeEditor) activeEditor.focusEditor() })
    }

    // --- zaznaczenie wielu bloków ------------------------------------------------------
    function setRange(anchor, focus) {
        rangeAnchor = anchor
        rangeFocus = focus
        if (anchor && focus && anchor.blockId === focus.blockId) {
            rangeAnchor = null
            rangeFocus = null
        }
        rangeApplied()
    }

    function clearRange() {
        if (rangeAnchor === null && rangeFocus === null)
            return
        recentAnchor = rangeAnchor
        recentAnchorTime = Date.now()
        rangeAnchor = null
        rangeFocus = null
        rangeApplied()
    }

    function updateRangeFocus(blockId, pos) {
        if (rangeActive && rangeFocus.blockId === blockId && rangeFocus.pos !== pos) {
            rangeFocus = { blockId: blockId, pos: pos }
        }
    }

    function rangeArgs() {
        return [rangeAnchor.blockId, rangeAnchor.pos, rangeFocus.blockId, rangeFocus.pos]
    }

    // "inner" – blok cały w zaznaczeniu, "first"/"last" – krawędzie, "" – poza.
    function rangeRole(index) {
        var r = range
        if (!r || index < r.first || index > r.last)
            return ""
        if (index === r.first)
            return "first"
        if (index === r.last)
            return "last"
        return "inner"
    }

    // Shift+↑/↓ na granicy bloku: zaznaczenie przechodzi do sąsiedniego bloku.
    function extendRange(editorItem, direction) {
        var i = doc.indexOf(editorItem.blockId)
        var target = i + direction
        if (target < 0 || target >= doc.blockCount)
            return false
        var anchor = rangeActive ? rangeAnchor : {
            blockId: editorItem.blockId,
            pos: editorItem.cursorPosition === editorItem.selectionEnd ? editorItem.selectionStart : editorItem.selectionEnd
        }
        var targetId = doc.blockIdAt(target)
        // W dół – do końca następnego bloku, w górę – do początku poprzedniego.
        var pos = direction > 0 ? doc.blockLength(targetId) : 0
        if (targetId === anchor.blockId) {
            // Powrót do bloku kotwicy – zwykłe zaznaczenie w jednym bloku.
            clearRange()
            doc.requestFocus(targetId, anchor.pos, pos, -1, -1)
            return true
        }
        setRange(anchor, { blockId: targetId, pos: pos })
        doc.requestFocus(targetId, pos, pos, -1, -1)
        rangeApplied()
        return true
    }

    // Shift+klik w innym bloku: zaznaczenie od poprzedniej pozycji kursora (albo kotwicy zaznaczenia).
    function extendRangeTo(blockId, pos) {
        var anchor = rangeActive ? rangeAnchor
                   : (recentAnchor && Date.now() - recentAnchorTime < 1500) ? recentAnchor : previousCaret
        if (!anchor || anchor.blockId === blockId)
            return
        setRange(anchor, { blockId: blockId, pos: pos })
    }

    function selectAllDocument() {
        if (!doc || doc.blockCount === 0)
            return
        var first = doc.blockIdAt(0), last = doc.blockIdAt(doc.blockCount - 1)
        if (first === last) {
            if (activeEditor) activeEditor.selectAll()
            return
        }
        setRange({ blockId: first, pos: 0 }, { blockId: last, pos: doc.blockLength(last) })
    }

    function deleteRange() {
        if (!rangeActive) return false
        var a = rangeArgs()
        clearRange()
        return doc.deleteRange(a[0], a[1], a[2], a[3])
    }

    function typeOverRange(text) {
        if (!rangeActive) return false
        var a = rangeArgs()
        clearRange()
        return doc.replaceRange(a[0], a[1], a[2], a[3], text)
    }

    // --- schowek ------------------------------------------------------------------------
    function copy() {
        if (rangeActive) {
            var a = rangeArgs()
            doc.copyRange(a[0], a[1], a[2], a[3])
        } else if (activeEditor) {
            activeEditor.copy()
        } else if (currentBlockId) {
            doc.copyBlock(currentBlockId)
        }
    }

    function cut() {
        if (rangeActive) {
            var a = rangeArgs()
            clearRange()
            doc.cutRange(a[0], a[1], a[2], a[3])
        } else if (activeEditor) {
            activeEditor.cut()
        } else if (currentBlockId) {
            doc.cutBlock(currentBlockId)
        }
    }

    // mode: "source" (z formatowaniem), "merge" (dopasuj do dokumentu), "plain" (tylko tekst)
    function paste(mode) {
        mode = mode || "source"
        if (rangeActive) {
            var a = rangeArgs()
            clearRange()
            doc.pasteRange(a[0], a[1], a[2], a[3], mode)
            return
        }
        var ed = activeEditor
        if (ed && ed.blockId === currentBlockId) {
            ed.commit()
            doc.paste(ed.blockId, ed.selectionStart, ed.selectionEnd, ed.cellRow, ed.cellCol, mode)
        } else if (currentBlockId) {
            doc.paste(currentBlockId, 0, 0, -1, -1, mode)
        }
    }

    function insertSymbol(text) {
        var ed = activeEditor
        if (!ed) {
            doc.notice("Umieść kursor w tekście, aby wstawić znak.")
            return
        }
        if (rangeActive) {
            typeOverRange(text)
            return
        }
        if (ed.selectionStart !== ed.selectionEnd)
            ed.remove(ed.selectionStart, ed.selectionEnd)
        var pos = ed.cursorPosition
        RichText.insertPlainText(ed.textDocument, pos, text)
        ed.cursorPosition = pos + text.length
        ed.dirty = true
        ed.commit()
        restoreFocus()
    }

    // --- formatowanie znaków --------------------------------------------------------------
    function toggle(key) {
        if (rangeActive) {
            var a = rangeArgs()
            doc.formatRange(a[0], a[1], a[2], a[3], (function() { var p = {}; p[key] = !format[key]; return p })())
            rangeApplied()
        } else if (activeEditor) {
            activeEditor.toggleFormat(key)
        }
    }

    function toggleVertical(value) {
        applyChar({ vertical: format.vertical === value ? "" : value })
    }

    function applyChar(props) {
        if (rangeActive) {
            var a = rangeArgs()
            doc.formatRange(a[0], a[1], a[2], a[3], props)
            rangeApplied()
        } else if (activeEditor) {
            activeEditor.applyFormat(props)
            restoreFocus()
        }
    }

    function changeCase(mode) {
        if (rangeActive) {
            var a = rangeArgs()
            doc.caseRange(a[0], a[1], a[2], a[3], mode)
            rangeApplied()
            return
        }
        var ed = activeEditor
        if (!ed || ed.selectionStart === ed.selectionEnd) {
            doc.notice("Zaznacz tekst, którego wielkość liter chcesz zmienić.")
            return
        }
        ed.commit()
        doc.changeCase(ed.blockId, ed.cellRow, ed.cellCol, ed.selectionStart, ed.selectionEnd, mode)
    }

    // --- malarz formatów -----------------------------------------------------------------
    function startPainter(sticky) {
        if (painterActive) {
            cancelPainter()
            return
        }
        var f = activeEditor ? activeEditor.currentFormat() : format
        painter = {
            char: { bold: !!f.bold, italic: !!f.italic, underline: !!f.underline, strike: !!f.strike,
                    color: f.color || "", highlight: f.highlight || "", fontFamily: f.fontFamily || "",
                    fontSize: f.fontSize || 0, vertical: f.vertical || "", smallCaps: !!f.smallCaps },
            para: currentIsText ? { align: currentPara.align || "left", lineHeight: currentPara.lineHeight,
                                    spaceBefore: currentPara.spaceBefore, spaceAfter: currentPara.spaceAfter } : null
        }
        painterSticky = !!sticky
        doc.notice(sticky ? "Malarz formatów włączony – zaznaczaj kolejne fragmenty (Esc kończy)."
                          : "Zaznacz tekst, który ma dostać skopiowane formatowanie.")
    }

    function cancelPainter() {
        painter = null
        painterSticky = false
    }

    // Wywoływane po zwolnieniu myszy w edytorze (lub po zaznaczeniu wielu bloków).
    function applyPainter(editorItem) {
        if (!painterActive)
            return
        var p = painter
        if (rangeActive) {
            var a = rangeArgs()
            doc.formatRange(a[0], a[1], a[2], a[3], p.char)
            if (p.para) doc.paragraphRange(a[0], a[1], a[2], a[3], p.para)
        } else if (editorItem && editorItem.selectionStart !== editorItem.selectionEnd) {
            editorItem.applyFormat(p.char)
            if (p.para && editorItem.cellRow < 0) doc.setParagraph(editorItem.blockId, p.para)
        } else {
            return
        }
        if (!painterSticky)
            cancelPainter()
    }

    // --- formatowanie akapitu ---------------------------------------------------------------
    function setStyle(style) {
        if (rangeActive) {
            var a = rangeArgs()
            doc.styleRange(a[0], a[1], a[2], a[3], style)
            rangeApplied()
            return
        }
        if (currentBlockId && (currentIsText || currentType === "placeholder")) {
            doc.setStyle(currentBlockId, style)
            restoreFocus()
        }
    }

    function selectionRect() {
        if (tableSelection && tableSelection.blockId === currentBlockId)
            return tableSelection
        return { blockId: currentBlockId, r1: activeRow, c1: activeCol, r2: activeRow, c2: activeCol }
    }

    function setParagraph(values) {
        if (rangeActive) {
            var a = rangeArgs()
            doc.paragraphRange(a[0], a[1], a[2], a[3], values)
            rangeApplied()
        } else if (currentIsText) {
            doc.setParagraph(currentBlockId, values)
            restoreFocus()
        }
    }

    function setAlign(align) {
        if (rangeActive) {
            setParagraph({ align: align })
        } else if (inTableCell) {
            var r = selectionRect()
            doc.tableSetAlign(currentBlockId, r.r1, r.c1, r.r2, r.c2, align)
        } else if (currentIsText) {
            doc.setParagraph(currentBlockId, { align: align })
        } else if (currentType === "image" && align !== "justify") {
            doc.setImage(currentBlockId, { align: align })
        }
        restoreFocus()
    }

    function currentAlign() {
        if (inTableCell) {
            var row = currentData.table && currentData.table.cells[activeRow]
            return row && row[activeCol] ? (row[activeCol].align || "left") : "left"
        }
        if (currentType === "image")
            return currentData.image ? currentData.image.align : "center"
        return currentPara.align || "left"
    }

    function toggleList(kind) {
        if (rangeActive) {
            setParagraph({ list: currentPara.list === kind ? "none" : kind })
            return
        }
        if (currentType !== "paragraph")
            return
        doc.setParagraph(currentBlockId, { list: currentPara.list === kind ? "none" : kind })
        restoreFocus()
    }

    function setListStyle(kind, style) {
        setParagraph({ list: kind, listStyle: style })
    }

    function indent(delta) {
        if (rangeActive) {
            setParagraph({ indent: Math.max(0, Math.min(8, (currentPara.indent || 0) + delta)) })
            return
        }
        if (currentType === "paragraph") {
            doc.changeIndent(currentBlockId, delta)
            restoreFocus()
        }
    }

    // --- wstawianie ------------------------------------------------------------------
    // Pozycja z przeciągnięcia elementu z listy wstawiania (-1 = przy kursorze).
    property int pendingInsertIndex: -1

    function insert(kind, options) {
        options = options || {}
        var id
        if (pendingInsertIndex >= 0) {
            id = doc.insertBlock(pendingInsertIndex, kind, options)
            pendingInsertIndex = -1
        } else if (currentType === "placeholder")
            id = doc.replacePlaceholder(currentBlockId, kind, options)
        else if (currentBlockId && doc.indexOf(currentBlockId) >= 0)
            id = doc.insertAfter(currentBlockId, kind, options)
        else
            id = doc.insertBlock(-1, kind, options)
        if (id)
            currentBlockId = id
        return id
    }

    function insertCaption() {
        var target = currentBlockId
        if (currentType === "caption")
            return
        if (currentType !== "table" && currentType !== "image") {
            // Szukamy najbliższej tabeli/obrazu powyżej kursora.
            var i = doc.indexOf(currentBlockId)
            target = ""
            for (var k = i; k >= 0 && k > i - 4; --k) {
                var t = doc.blockType(doc.blockIdAt(k))
                if (t === "table" || t === "image") { target = doc.blockIdAt(k); break }
            }
        }
        if (!target) {
            doc.notice("Zaznacz tabelę lub obraz, aby dodać podpis.")
            return
        }
        doc.addCaption(target)
    }

    function canAddCaption() {
        return (currentType === "table" || currentType === "image") && doc && !doc.captionOf(currentBlockId)
    }

    // --- usuwanie z potwierdzeniem dla większej ilości treści -------------------------
    function removeBlock(blockId) {
        var data = doc.blockData(blockId)
        if (data.type === "heading") {
            var info = doc.sectionInfo(blockId)
            if (info.blockCount > 2) {
                confirmRequested({
                    title: "Usunąć sekcję?",
                    message: "Sekcja „" + info.title + "” zawiera " + (info.blockCount - 1)
                             + " elementów (wraz z podsekcjami). Usunąć cały jej zakres?\n\n"
                             + "„Tylko nagłówek” usuwa sam nagłówek i zostawia treść.",
                    acceptText: "Usuń sekcję",
                    secondaryText: "Tylko nagłówek",
                    action: function(choice) {
                        if (choice === "secondary") doc.removeBlock(blockId)
                        else doc.removeSection(blockId)
                    }
                })
                return
            }
        }
        if (data.type === "table" && doc.plainTextLength(blockId) > 0) {
            confirmRequested({ title: "Usunąć tabelę?", message: "Tabela zawiera tekst. Usunąć ją razem z podpisem?",
                               acceptText: "Usuń tabelę", action: function() { doc.removeBlock(blockId) } })
            return
        }
        doc.removeBlock(blockId)
    }

    function removeSection(sectionId) {
        var info = doc.sectionInfo(sectionId)
        confirmRequested({ title: "Usunąć sekcję?",
                           message: "Sekcja „" + info.title + "” i cała jej zawartość (" + info.blockCount
                                    + " elementów, z podsekcjami) zostaną usunięte. Operację można cofnąć (Ctrl+Z).",
                           acceptText: "Usuń sekcję", action: function() { doc.removeSection(sectionId) } })
    }
}
