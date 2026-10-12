import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import QtCore
import QmlWord.Backend
import "panels"
import "dialogs"
import "menus"
import "controls"

ApplicationWindow {
    id: window

    property string startupFile: ""
    property string screenshotPath: ""

    property bool navOpen: true
    property bool propsOpen: true
    property bool previewMode: false
    property real zoom: 1.0
    property bool allowClose: false
    property var pendingAction: null
    property var afterSaveAction: null
    property string imageTarget: ""
    property double dirtySince: 0
    property double reminderSnoozedUntil: 0
    property bool reminderVisible: false
    property int reminderMinutes: 0
    property string draftTime: ""
    property real lastWidth: width
    property bool findBarOpen: false

    width: 1440
    height: 900
    minimumWidth: 640
    minimumHeight: 420
    visible: true
    title: doc ? (doc.modified ? "• " : "") + doc.fileName + " — QmlWord" : "QmlWord"
    color: Theme.window
    font.family: Theme.uiFont
    font.pointSize: Theme.fontNormal

    palette.highlight: Theme.accent
    palette.highlightedText: "#ffffff"
    palette.window: Theme.window
    palette.base: Theme.paper
    palette.alternateBase: Theme.panel
    palette.button: "#f3f4f6"
    palette.buttonText: Theme.text
    palette.text: Theme.text
    palette.windowText: Theme.text
    palette.placeholderText: Theme.textFaint
    palette.mid: Theme.border

    // --- backend ------------------------------------------------------------------------
    DocumentModel {
        id: doc
        objectName: "documentModel"
        onErrorOccurred: function(t, m) { messageDialog.showError(t, m) }
        onWarningsOccurred: function(t, items) { messageDialog.showWarnings(t, items) }
        onNotice: function(m) { toast.show(m) }
        onModifiedChanged: {
            if (modified && window.dirtySince === 0) {
                window.dirtySince = Date.now()
            } else if (!modified) {
                window.dirtySince = 0
                window.reminderVisible = false
            }
        }
        onDocumentLoaded: {
            editor.select("")
            Qt.callLater(documentView.focusFirstBlock)
        }
    }
    OutlineModel { id: outline; objectName: "outlineModel"; document: doc }
    SearchController { id: search; objectName: "searchController"; document: doc }
    PageLayout { id: pageLayout; document: doc; active: window.previewMode }
    AutosaveManager {
        id: autosave
        document: doc
        onSavedDraft: function(t) { window.draftTime = t }
    }
    DragController { id: dragCtl; objectName: "dragController" }

    EditorController {
        id: editor
        objectName: "editorController"
        doc: doc
        onContextMenuRequested: function(kind, payload) { window.openContextMenu(kind, payload) }
        onInsertTableRequested: tableDialog.open()
        onLinkRequested: window.openLinkDialog()
        onImageRequested: function(target) {
            window.imageTarget = target
            imageDialog.open()
        }
        onConfirmRequested: function(options) { confirmDialog.ask(options) }
        onPasteSpecialRequested: pasteSpecialDialog.open()
        onSymbolsRequested: symbolDialog.open()
        onFormulaRequested: function(blockId, row, col) { formulaDialog.openFor(blockId, row, col) }
        onConvertRequested: function(kind, blockId) {
            window.convertBlockId = blockId
            convertDialog.openFor(kind)
        }
    }
    property string convertBlockId: ""

    function openFindBar(replace) {
        findBarOpen = true
        findBar.replaceMode = replace
        var ed = editor.activeEditor
        if (ed && ed.selectionStart !== ed.selectionEnd && ed.selectedText.length < 80)
            search.query = ed.selectedText
        Qt.callLater(function() { findBar.findField.forceActiveFocus(); findBar.findField.selectAll() })
    }

    Settings {
        id: settings
        category: "window"
        property alias navOpen: window.navOpen
        property alias propsOpen: window.propsOpen
        property alias zoom: window.zoom
        property alias width: window.width
        property alias height: window.height
        property url lastFolder: StandardPaths.writableLocation(StandardPaths.DocumentsLocation)
    }

    // --- akcje plikowe ---------------------------------------------------------------------
    function guard(action) {
        doc.flush()
        if (!doc.modified) {
            action()
            return
        }
        pendingAction = action
        unsavedDialog.documentName = doc.fileName
        unsavedDialog.open()
    }

    function newDocument() {
        guard(function() {
            doc.newDocument()
            window.previewMode = false
        })
    }

    function openDocument() {
        guard(function() { openDialog.open() })
    }

    function save() {
        doc.flush()
        if (doc.filePath)
            return doc.save()
        saveAs()
        return false
    }

    function saveAs() {
        saveDialog.currentFolder = doc.filePath ? doc.folderUrl : settings.lastFolder
        saveDialog.selectedFile = AppUtils.fromLocalFile(AppUtils.toLocalFile(saveDialog.currentFolder) + "/" + doc.suggestedName + "." + doc.nativeExtension)
        saveDialog.open()
    }

    function saveThen(action) {
        if (doc.filePath) {
            if (doc.save())
                action()
        } else {
            afterSaveAction = action
            saveAs()
        }
    }

    function exportPdf() {
        doc.flush()
        pdfDialog.currentFolder = doc.filePath ? doc.folderUrl : settings.lastFolder
        pdfDialog.selectedFile = AppUtils.fromLocalFile(AppUtils.toLocalFile(pdfDialog.currentFolder) + "/" + doc.suggestedName + ".pdf")
        pdfDialog.open()
    }

    function openLinkDialog() {
        var ed = editor.activeEditor
        if (!ed || !editor.hasTextEditor) {
            toast.show("Umieść kursor w tekście, aby wstawić link.")
            return
        }
        linkDialog.openFor(ed.selectionStart !== ed.selectionEnd, ed.linkUnderCursor())
    }

    function openContextMenu(kind, payload) {
        var menu = kind === "text" ? textMenu
                 : kind === "table" || kind === "tableBlock" ? tableMenu
                 : kind === "image" ? imageMenu
                 : kind === "section" ? sectionMenu : blockMenu
        menu.payload = payload
        menu.popup()
    }

    function setZoom(value) {
        zoom = Math.max(0.5, Math.min(2.0, Math.round(value * 20) / 20))
    }

    function isInside(item, ancestor) {
        while (item) {
            if (item === ancestor)
                return true
            item = item.parent
        }
        return false
    }

    function cycleFocus(backwards) {
        var f = window.activeFocusItem
        var zones = []
        if (navOpen && !previewMode) zones.push("nav")
        zones.push("doc")
        if (propsOpen && !previewMode) zones.push("props")
        zones.push("toolbar")
        var current = isInside(f, navPanel) ? "nav" : isInside(f, propsPanel) ? "props"
                    : isInside(f, header) || isInside(f, toolbar) ? "toolbar" : "doc"
        var i = zones.indexOf(current)
        var next = zones[(i + (backwards ? zones.length - 1 : 1)) % zones.length]
        if (next === "nav") {
            navPanel.focusOutline()
        } else if (next === "doc") {
            if (previewMode) previewView.forceActiveFocus()
            else if (editor.activeEditor) editor.activeEditor.focusEditor()
            else documentView.focusFirstBlock()
        } else if (next === "props") {
            var it = propsPanel.nextItemInFocusChain(true)
            if (it) it.forceActiveFocus()
        } else {
            header.searchField.forceActiveFocus()
        }
    }

    onClosing: function(close) {
        if (allowClose) {
            autosave.shutdown()
            return
        }
        close.accepted = false
        guard(function() {
            window.allowClose = true
            autosave.shutdown()
            Qt.callLater(window.close)
        })
    }

    onWidthChanged: {
        if (width < 1150 && lastWidth >= 1150) propsOpen = false
        if (width >= 1150 && lastWidth < 1150) propsOpen = true
        if (width < 860 && lastWidth >= 860) navOpen = false
        if (width >= 860 && lastWidth < 860) navOpen = true
        lastWidth = width
    }

    Component.onCompleted: {
        if (startupFile)
            doc.openFile(startupFile)
        var items = autosave.findRecoverable()
        if (items.length > 0)
            recoveryDialog.offer(items)
        else
            Qt.callLater(documentView.focusFirstBlock)
    }

    // Przypomnienie o niezapisanych zmianach po 10 minutach pracy bez zapisu.
    Timer {
        interval: 30000
        repeat: true
        running: true
        onTriggered: {
            var now = Date.now()
            if (doc.modified && window.dirtySince > 0 && now - window.dirtySince > 10 * 60000
                    && now > window.reminderSnoozedUntil) {
                window.reminderMinutes = Math.round((now - window.dirtySince) / 60000)
                window.reminderVisible = true
            }
        }
    }

    // Zrzut okna do diagnostyki (python main.py --screenshot plik.png)
    Timer {
        running: window.screenshotPath !== ""
        interval: 1800
        onTriggered: root.grabToImage(function(result) {
            result.saveToFile(window.screenshotPath)
            window.allowClose = true
            Qt.quit()
        })
    }

    // --- układ -------------------------------------------------------------------------
    Item {
        id: root
        anchors.fill: parent

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            AppHeader {
                id: header
                Layout.fillWidth: true
                doc: doc
                search: search
                navOpen: window.navOpen
                propsOpen: window.propsOpen
                previewMode: window.previewMode
                onToggleNav: window.navOpen = !window.navOpen
                onToggleProps: window.propsOpen = !window.propsOpen
                onNewRequested: window.newDocument()
                onOpenRequested: window.openDocument()
                onSaveRequested: window.save()
                onSaveAsRequested: window.saveAs()
                onExportRequested: window.exportPdf()
                onPageSetupRequested: pageSetupDialog.open()
                onPreviewToggled: { doc.flush(); window.previewMode = !window.previewMode }
                onHelpRequested: shortcutsDialog.open()
            }

            ReminderBanner {
                Layout.fillWidth: true
                visible: window.reminderVisible
                minutes: window.reminderMinutes
                onSaveRequested: window.save()
                onDismissed: {
                    window.reminderVisible = false
                    window.reminderSnoozedUntil = Date.now() + 10 * 60000
                }
            }

            FormatToolbar {
                id: toolbar
                Layout.fillWidth: true
                visible: !window.previewMode
                doc: doc
                editor: editor
                onLinkRequested: window.openLinkDialog()
                onTableRequested: tableDialog.open()
                onImageRequested: { window.imageTarget = ""; imageDialog.open() }
            }

            FindReplaceBar {
                id: findBar
                Layout.fillWidth: true
                visible: window.findBarOpen && !window.previewMode
                search: search
                onCloseRequested: {
                    window.findBarOpen = false
                    editor.restoreFocus()
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                NavigationPanel {
                    id: navPanel
                    Layout.preferredWidth: Theme.navWidth
                    Layout.fillHeight: true
                    visible: window.navOpen && !window.previewMode
                    doc: doc
                    editor: editor
                    dragCtl: dragCtl
                    outline: outline
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumWidth: 280

                    DocumentView {
                        id: documentView
                        anchors.fill: parent
                        visible: !window.previewMode
                        doc: doc
                        editor: editor
                        dragCtl: dragCtl
                        zoom: window.zoom
                        onZoomRequested: function(v) { window.setZoom(v) }
                    }
                    PagePreviewView {
                        id: previewView
                        anchors.fill: parent
                        visible: window.previewMode
                        doc: doc
                        pageLayout: pageLayout
                        zoom: window.zoom
                        onExportRequested: window.exportPdf()
                        onCloseRequested: window.previewMode = false
                    }
                }

                PropertiesPanel {
                    id: propsPanel
                    Layout.preferredWidth: Theme.propsWidth
                    Layout.fillHeight: true
                    visible: window.propsOpen && !window.previewMode
                    doc: doc
                    editor: editor
                    outline: outline
                    onPageSetupRequested: pageSetupDialog.open()
                }
            }

            StatusBar {
                Layout.fillWidth: true
                doc: doc
                editor: editor
                zoom: window.zoom
                draftTime: window.draftTime
                previewMode: window.previewMode
                pageCount: pageLayout.pageCount
                onZoomRequested: function(v) { window.setZoom(v) }
            }
        }

        DragGhost {
            drag: dragCtl
        }

        Toast {
            id: toast
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: Theme.statusHeight + 16
            z: 900
        }
    }

    // Esc: anuluje przeciąganie, malarza formatów, zaznaczenie wielu bloków, zamyka podgląd i wyszukiwanie
    Shortcut {
        sequence: "Escape"
        enabled: dragCtl.active || window.previewMode || editor.painterActive || editor.rangeActive || window.findBarOpen
        onActivated: {
            if (dragCtl.active) dragCtl.finish(true)
            else if (editor.painterActive) editor.cancelPainter()
            else if (editor.rangeActive) editor.clearRange()
            else if (window.findBarOpen) { window.findBarOpen = false; editor.restoreFocus() }
            else window.previewMode = false
        }
    }

    // --- skróty --------------------------------------------------------------------------
    Shortcut { sequences: [StandardKey.New]; onActivated: window.newDocument() }
    Shortcut { sequences: [StandardKey.Open]; onActivated: window.openDocument() }
    Shortcut { sequences: [StandardKey.Save]; onActivated: window.save() }
    Shortcut { sequence: "Ctrl+Shift+S"; onActivated: window.saveAs() }
    Shortcut { sequence: "Ctrl+Shift+E"; onActivated: window.exportPdf() }
    Shortcut { sequence: "Ctrl+Shift+P"; onActivated: { doc.flush(); window.previewMode = !window.previewMode } }
    Shortcut { sequences: ["Ctrl+Z"]; onActivated: doc.undo() }
    Shortcut { sequences: ["Ctrl+Y", "Ctrl+Shift+Z"]; onActivated: doc.redo() }
    Shortcut { sequence: "Ctrl+F"; onActivated: window.openFindBar(false) }
    Shortcut { sequence: "Ctrl+H"; onActivated: window.openFindBar(true) }
    Shortcut { sequences: [StandardKey.Paste]; onActivated: editor.paste("source") }
    Shortcut { sequences: [StandardKey.Copy]; onActivated: editor.copy() }
    Shortcut { sequences: [StandardKey.Cut]; onActivated: editor.cut() }
    Shortcut { sequence: "Ctrl+Shift+V"; onActivated: editor.paste("plain") }
    Shortcut { sequence: "Ctrl+Alt+V"; onActivated: pasteSpecialDialog.open() }
    Shortcut { sequences: ["Ctrl+Shift+=", "Ctrl++"]; onActivated: editor.toggleVertical("super") }
    Shortcut { sequence: "Ctrl+="; onActivated: editor.toggleVertical("sub") }
    Shortcut { sequence: "Ctrl+Shift+K"; onActivated: editor.toggle("smallCaps") }
    Shortcut { sequences: ["Ctrl+Shift+8", "Ctrl+*"]; onActivated: editor.showMarks = !editor.showMarks }
    Shortcut { sequence: "Ctrl+Shift+Space"; onActivated: editor.insertSymbol("\u00a0") }
    Shortcut { sequence: "F3"; onActivated: search.next() }
    Shortcut { sequence: "Shift+F3"; onActivated: search.previous() }
    Shortcut { sequence: "Ctrl+B"; onActivated: editor.toggle("bold") }
    Shortcut { sequence: "Ctrl+I"; onActivated: editor.toggle("italic") }
    Shortcut { sequence: "Ctrl+U"; onActivated: editor.toggle("underline") }
    Shortcut { sequence: "Ctrl+Shift+X"; onActivated: editor.toggle("strike") }
    Shortcut {
        sequence: "Ctrl+Space"
        onActivated: editor.applyChar({ bold: null, italic: null, underline: null, strike: null,
                                        color: "", highlight: "", fontFamily: "", fontSize: 0,
                                        vertical: "", smallCaps: null })
    }
    Shortcut { sequence: "Ctrl+K"; onActivated: window.openLinkDialog() }
    Shortcut { sequence: "Ctrl+L"; onActivated: editor.setAlign("left") }
    Shortcut { sequence: "Ctrl+E"; onActivated: editor.setAlign("center") }
    Shortcut { sequence: "Ctrl+R"; onActivated: editor.setAlign("right") }
    Shortcut { sequence: "Ctrl+J"; onActivated: editor.setAlign("justify") }
    Shortcut { sequence: "Ctrl+Alt+0"; onActivated: editor.setStyle("body") }
    Shortcut { sequence: "Ctrl+Alt+1"; onActivated: editor.setStyle("h1") }
    Shortcut { sequence: "Ctrl+Alt+2"; onActivated: editor.setStyle("h2") }
    Shortcut { sequence: "Ctrl+Alt+3"; onActivated: editor.setStyle("h3") }
    Shortcut { sequence: "Ctrl+Shift+L"; onActivated: editor.toggleList("bullet") }
    Shortcut { sequence: "Ctrl+Alt+T"; onActivated: tableDialog.open() }
    Shortcut { sequences: ["Ctrl+Return", "Ctrl+Enter"]; onActivated: editor.insert("pageBreak", {}) }
    Shortcut { sequence: "Ctrl+Shift+N"; onActivated: doc.addSection(editor.currentSectionId, false) }
    Shortcut {
        sequence: "Alt+Shift+Up"
        onActivated: if (editor.currentBlockId) { doc.moveBlockBy(editor.currentBlockId, -1); editor.restoreFocus() }
    }
    Shortcut {
        sequence: "Alt+Shift+Down"
        onActivated: if (editor.currentBlockId) { doc.moveBlockBy(editor.currentBlockId, 1); editor.restoreFocus() }
    }
    Shortcut { sequence: "F6"; onActivated: window.cycleFocus(false) }
    Shortcut { sequence: "Shift+F6"; onActivated: window.cycleFocus(true) }
    Shortcut { sequence: "F1"; onActivated: shortcutsDialog.open() }
    Shortcut { sequence: "Ctrl+Shift+1"; onActivated: window.navOpen = !window.navOpen }
    Shortcut { sequence: "Ctrl+Shift+2"; onActivated: window.propsOpen = !window.propsOpen }
    Shortcut { sequence: "Ctrl+Alt+="; onActivated: window.setZoom(window.zoom + 0.1) }
    Shortcut { sequence: "Ctrl+-"; onActivated: window.setZoom(window.zoom - 0.1) }
    Shortcut { sequence: "Ctrl+0"; onActivated: window.setZoom(1.0) }

    // --- okna plików -----------------------------------------------------------------------
    FileDialog {
        id: openDialog
        title: "Otwórz dokument"
        fileMode: FileDialog.OpenFile
        nameFilters: doc ? doc.openFilters : []
        currentFolder: settings.lastFolder
        onAccepted: {
            settings.lastFolder = currentFolder
            if (doc.openFile(selectedFile))
                window.previewMode = false
        }
    }
    FileDialog {
        id: saveDialog
        title: "Zapisz dokument jako"
        fileMode: FileDialog.SaveFile
        nameFilters: doc ? doc.saveFilters : []
        onAccepted: {
            settings.lastFolder = currentFolder
            if (doc.saveAs(selectedFile)) {
                toast.show("Zapisano: " + doc.fileName)
                var a = window.afterSaveAction
                window.afterSaveAction = null
                if (a) a()
            }
        }
        onRejected: window.afterSaveAction = null
    }
    FileDialog {
        id: pdfDialog
        title: "Eksportuj do PDF"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Dokument PDF (*.pdf)"]
        defaultSuffix: "pdf"
        onAccepted: doc.exportPdf(selectedFile)
    }
    FileDialog {
        id: imageDialog
        title: "Wybierz obraz"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Obrazy (*.png *.jpg *.jpeg *.gif *.bmp *.svg *.webp)", "Wszystkie pliki (*)"]
        currentFolder: settings.lastFolder
        onAccepted: {
            if (window.imageTarget)
                doc.setImage(window.imageTarget, { path: selectedFile })
            else
                editor.insert("image", { path: selectedFile })
            window.imageTarget = ""
        }
        onRejected: {
            window.imageTarget = ""
            editor.pendingInsertIndex = -1
        }
    }

    // --- dialogi ----------------------------------------------------------------------------
    InsertTableDialog {
        id: tableDialog
        onTableChosen: function(rows, cols, headerRow, caption, captionText) {
            editor.insert("table", { rows: rows, cols: cols, headerRow: headerRow, caption: caption, captionText: captionText })
        }
        onRejected: editor.pendingInsertIndex = -1
    }
    LinkDialog {
        id: linkDialog
        onLinkChosen: function(text, url) {
            if (editor.activeEditor) {
                editor.activeEditor.insertLink(text, url)
                editor.restoreFocus()
            }
        }
        onLinkRemoved: if (editor.activeEditor) editor.activeEditor.removeLink()
    }
    PageSetupDialog { id: pageSetupDialog; doc: doc }
    UnsavedChangesDialog {
        id: unsavedDialog
        onSaveChosen: {
            var a = window.pendingAction
            window.pendingAction = null
            window.saveThen(a)
        }
        onDiscardChosen: {
            var a = window.pendingAction
            window.pendingAction = null
            if (a) a()
        }
        onRejected: window.pendingAction = null
    }
    ConfirmDialog { id: confirmDialog }
    MessageDialog { id: messageDialog }
    RecoveryDialog { id: recoveryDialog; autosave: autosave }
    ShortcutsDialog { id: shortcutsDialog }
    PasteSpecialDialog {
        id: pasteSpecialDialog
        onModeChosen: function(mode) { editor.paste(mode) }
    }
    SymbolDialog {
        id: symbolDialog
        onSymbolChosen: function(text) { editor.insertSymbol(text) }
    }
    FormulaDialog { id: formulaDialog; doc: doc }
    ConvertTableDialog {
        id: convertDialog
        onSeparatorChosen: function(kind, separator) {
            if (kind === "tableToText") {
                doc.tableToText(window.convertBlockId, separator)
            } else if (editor.rangeActive) {
                var a = editor.rangeArgs()
                editor.clearRange()
                doc.textToTable(a[0], a[1], a[2], a[3], separator)
            } else {
                doc.textToTable(window.convertBlockId, 0, window.convertBlockId, 0, separator)
            }
        }
    }

    // --- menu kontekstowe ----------------------------------------------------------------------
    TextContextMenu {
        id: textMenu
        doc: doc
        editor: editor
        onLinkRequested: window.openLinkDialog()
        onDescriptionRequested: function(id) { documentView.startDescription(id) }
    }
    TableContextMenu { id: tableMenu; doc: doc; editor: editor }
    ImageContextMenu { id: imageMenu; doc: doc; editor: editor }
    SectionContextMenu {
        id: sectionMenu
        doc: doc
        editor: editor
        outline: outline
        onDescriptionRequested: function(id) { documentView.startDescription(id) }
    }
    BlockContextMenu { id: blockMenu; doc: doc; editor: editor }
}
