import QtQuick
import QmlWord.Backend
import ".."

// Tabela: komórki rozmieszczone wg szerokości kolumn i wyliczonych wysokości wierszy,
// uchwyty zmiany rozmiaru, zaznaczenie zakresu komórek i nawigacja klawiaturą.
Item {
    id: tableBlock

    property DocumentModel doc
    property EditorController editor
    property string blockId: ""
    property var blockData: ({})
    property real contentWidth: 600

    readonly property var table: blockData.table || ({ cells: [[{}]], colWidths: [1], rowHeights: [0], rows: 1, cols: 1 })
    readonly property int rows: table.cells ? table.cells.length : 0
    readonly property int cols: rows > 0 ? table.cells[0].length : 0
    readonly property string structureKey: buildKey()

    property var anchorList: []
    // Wygląd komórek wg stylu tabeli (tło, krawędzie, pogrubienie) – liczony w modelu.
    readonly property var appearance: doc && blockId && doc.revision >= 0 ? doc.tableAppearance(blockId) : []
    property var liveWidths: null
    readonly property var widths: liveWidths || table.colWidths || []
    readonly property var colX: {
        var xs = [0]
        var acc = 0
        for (var i = 0; i < widths.length; ++i) {
            acc += widths[i] * contentWidth
            xs.push(acc)
        }
        return xs
    }
    property var rowTops: [0]
    property int liveRow: -1
    property real liveRowHeight: 0
    readonly property real tableHeight: rowTops.length ? rowTops[rowTops.length - 1] : 0
    readonly property var selection: editor && editor.tableSelection && editor.tableSelection.blockId === blockId
                                      ? editor.tableSelection : null

    implicitHeight: tableHeight + 12

    function buildKey() {
        var parts = [rows + "x" + cols]
        for (var r = 0; r < rows; ++r)
            for (var c = 0; c < cols; ++c) {
                var cell = table.cells[r][c]
                if ((cell.rowSpan || 1) > 1 || (cell.colSpan || 1) > 1)
                    parts.push(r + "," + c + "," + (cell.rowSpan || 1) + "," + (cell.colSpan || 1))
            }
        parts.push(table.headerRow ? "h" : "-")
        return parts.join(";")
    }

    function buildAnchors() {
        var covered = {}
        var list = []
        for (var r = 0; r < rows; ++r) {
            for (var c = 0; c < cols; ++c) {
                if (covered[r + ":" + c])
                    continue
                var cell = table.cells[r][c]
                var rs = cell.rowSpan || 1, cs = cell.colSpan || 1
                for (var rr = r; rr < r + rs; ++rr)
                    for (var cc = c; cc < c + cs; ++cc)
                        covered[rr + ":" + cc] = true
                list.push({ row: r, col: c, rowSpan: rs, colSpan: cs })
            }
        }
        return list
    }

    onStructureKeyChanged: {
        anchorList = buildAnchors()
        Qt.callLater(layoutRows)
    }
    Component.onCompleted: {
        anchorList = buildAnchors()
        Qt.callLater(layoutRows)
    }
    onWidthChanged: Qt.callLater(layoutRows)
    onTableChanged: Qt.callLater(layoutRows)
    onWidthsChanged: Qt.callLater(layoutRows)

    function minHeight(r) {
        if (r === liveRow)
            return liveRowHeight
        var h = table.rowHeights ? table.rowHeights[r] || 0 : 0
        return Math.max(26, h)
    }

    function layoutRows() {
        var heights = []
        for (var r = 0; r < rows; ++r)
            heights.push(minHeight(r))
        var spanning = []
        for (var i = 0; i < cellRepeater.count; ++i) {
            var item = cellRepeater.itemAt(i)
            if (!item)
                continue
            if (item.rowSpan === 1)
                heights[item.row] = Math.max(heights[item.row], item.naturalHeight)
            else
                spanning.push(item)
        }
        for (var k = 0; k < spanning.length; ++k) {
            var it = spanning[k]
            var sum = 0
            for (var rr = it.row; rr < it.row + it.rowSpan && rr < rows; ++rr)
                sum += heights[rr]
            if (it.naturalHeight > sum)
                heights[Math.min(rows - 1, it.row + it.rowSpan - 1)] += it.naturalHeight - sum
        }
        var tops = [0]
        for (var j = 0; j < heights.length; ++j)
            tops.push(tops[j] + heights[j])
        rowTops = tops
    }

    function cellItem(row, col) {
        for (var i = 0; i < cellRepeater.count; ++i) {
            var it = cellRepeater.itemAt(i)
            if (it && row >= it.row && row < it.row + it.rowSpan && col >= it.col && col < it.col + it.colSpan)
                return it
        }
        return null
    }

    function focusCell(row, col, start, end) {
        var it = cellItem(Math.max(0, Math.min(rows - 1, row)), Math.max(0, Math.min(cols - 1, col)))
        if (it)
            it.focusAt(start, end)
    }
    function focusAt(start, end) { focusCell(0, 0, start, end) }
    function focusFromAbove(x) { focusCell(0, columnAt(x), 0, 0) }
    function focusFromBelow(x) { focusCell(rows - 1, columnAt(x), 0, 0) }

    function columnAt(x) {
        for (var c = 0; c < cols; ++c)
            if (x < colX[c + 1])
                return c
        return cols - 1
    }

    function anchorIndex(row, col) {
        for (var i = 0; i < anchorList.length; ++i)
            if (anchorList[i].row === row && anchorList[i].col === col)
                return i
        return -1
    }

    function moveByTab(row, col, backwards) {
        var i = anchorIndex(row, col)
        if (backwards) {
            if (i > 0)
                focusCell(anchorList[i - 1].row, anchorList[i - 1].col, 0, -1)
            return
        }
        if (i >= 0 && i + 1 < anchorList.length) {
            focusCell(anchorList[i + 1].row, anchorList[i + 1].col, 0, -1)
        } else {
            // Tab w ostatniej komórce dodaje wiersz (jak w typowych edytorach).
            var newRow = rows
            if (doc.tableInsertRow(blockId, newRow))
                doc.requestFocus(blockId, 0, 0, newRow, 0)
        }
    }

    function inSelection(row, col, rowSpan, colSpan) {
        if (!selection)
            return false
        var r1 = Math.min(selection.r1, selection.r2), r2 = Math.max(selection.r1, selection.r2)
        var c1 = Math.min(selection.c1, selection.c2), c2 = Math.max(selection.c1, selection.c2)
        return row + rowSpan - 1 >= r1 && row <= r2 && col + colSpan - 1 >= c1 && col <= c2
    }

    signal navigateUp(real x)
    signal navigateDown(real x)

    Connections {
        target: tableBlock.doc
        function onBlockReset(id) {
            if (id !== tableBlock.blockId)
                return
            var t = tableBlock.doc.blockData(tableBlock.blockId).table
            for (var i = 0; i < cellRepeater.count; ++i) {
                var it = cellRepeater.itemAt(i)
                if (it && t.cells[it.row] && t.cells[it.row][it.col])
                    it.reload(t.cells[it.row][it.col])
            }
            Qt.callLater(tableBlock.layoutRows)
        }
    }

    Item {
        id: grid
        y: 6
        width: tableBlock.contentWidth
        height: tableBlock.tableHeight


        Repeater {
            id: cellRepeater
            model: tableBlock.anchorList
            delegate: TableCell {
                required property var modelData
                doc: tableBlock.doc
                editor: tableBlock.editor
                blockId: tableBlock.blockId
                row: modelData.row
                col: modelData.col
                rowSpan: modelData.rowSpan
                colSpan: modelData.colSpan
                look: tableBlock.appearance[modelData.row] ? tableBlock.appearance[modelData.row][modelData.col] : null
                x: tableBlock.colX[col] || 0
                y: tableBlock.rowTops[row] || 0
                width: (tableBlock.colX[Math.min(col + colSpan, tableBlock.colX.length - 1)] || 0) - x
                height: (tableBlock.rowTops[Math.min(row + rowSpan, tableBlock.rowTops.length - 1)] || 0) - y
                selectedCell: tableBlock.inSelection(row, col, rowSpan, colSpan)
                Component.onCompleted: load(tableBlock.table.cells[row][col])
                onNaturalHeightChanged: Qt.callLater(tableBlock.layoutRows)
                onTabPressed: function(backwards) { tableBlock.moveByTab(row, col, backwards) }
                onNavigateUp: function(x) {
                    if (row === 0) tableBlock.navigateUp(x + tableBlock.colX[col])
                    else tableBlock.focusCell(row - 1, col, 0, 0)
                }
                onNavigateDown: function(x) {
                    if (row + rowSpan >= tableBlock.rows) tableBlock.navigateDown(x + tableBlock.colX[col])
                    else tableBlock.focusCell(row + rowSpan, col, 0, 0)
                }
                onShiftClicked: {
                    var ed = tableBlock.editor
                    var startRow = ed.currentBlockId === tableBlock.blockId && ed.activeRow >= 0 ? ed.activeRow : row
                    var startCol = ed.currentBlockId === tableBlock.blockId && ed.activeCol >= 0 ? ed.activeCol : col
                    if (ed.tableSelection && ed.tableSelection.blockId === tableBlock.blockId) {
                        startRow = ed.tableSelection.r1
                        startCol = ed.tableSelection.c1
                    }
                    ed.tableSelection = { blockId: tableBlock.blockId, r1: startRow, c1: startCol,
                                          r2: row + rowSpan - 1, c2: col + colSpan - 1 }
                }
            }
        }

        // Uchwyty szerokości kolumn
        Repeater {
            model: Math.max(0, tableBlock.cols - 1)
            delegate: MouseArea {
                required property int index
                readonly property int boundary: index + 1
                x: (tableBlock.colX[boundary] || 0) - 3
                width: 7
                height: grid.height
                z: 10
                hoverEnabled: true
                cursorShape: Qt.SplitHCursor
                preventStealing: true
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 2
                    height: parent.height
                    color: Theme.accent
                    visible: parent.containsMouse || parent.pressed
                }
                onPressed: tableBlock.liveWidths = tableBlock.table.colWidths.slice()
                onPositionChanged: function(mouse) {
                    if (!pressed)
                        return
                    var w = tableBlock.liveWidths.slice()
                    var pos = mapToItem(grid, mouse.x, 0).x / tableBlock.contentWidth
                    var left = 0
                    for (var i = 0; i < index; ++i)
                        left += w[i]
                    var pair = w[index] + w[index + 1]
                    var minW = 0.04
                    var newLeft = Math.max(minW, Math.min(pair - minW, pos - left))
                    w[index] = newLeft
                    w[index + 1] = pair - newLeft
                    tableBlock.liveWidths = w
                }
                onReleased: {
                    var w = tableBlock.liveWidths
                    tableBlock.doc.tableSetColumnWidths(tableBlock.blockId, w)
                    tableBlock.liveWidths = null
                }
            }
        }

        // Uchwyty wysokości wierszy (podwójne kliknięcie = wysokość automatyczna)
        Repeater {
            model: tableBlock.rows
            delegate: MouseArea {
                required property int index
                y: (tableBlock.rowTops[index + 1] || 0) - 3
                width: grid.width
                height: 7
                z: 9
                hoverEnabled: true
                cursorShape: Qt.SplitVCursor
                preventStealing: true
                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width
                    height: 2
                    color: Theme.accent
                    visible: parent.containsMouse || parent.pressed
                }
                onPressed: {
                    tableBlock.liveRow = index
                    tableBlock.liveRowHeight = tableBlock.rowTops[index + 1] - tableBlock.rowTops[index]
                }
                onPositionChanged: function(mouse) {
                    if (!pressed)
                        return
                    var yy = mapToItem(grid, 0, mouse.y).y
                    tableBlock.liveRowHeight = Math.max(20, yy - tableBlock.rowTops[index])
                    tableBlock.layoutRows()
                }
                onReleased: {
                    var h = tableBlock.liveRowHeight
                    tableBlock.liveRow = -1
                    tableBlock.doc.tableSetRowHeight(tableBlock.blockId, index, Math.round(h))
                    Qt.callLater(tableBlock.layoutRows)
                }
                onDoubleClicked: {
                    tableBlock.liveRow = -1
                    tableBlock.doc.tableSetRowHeight(tableBlock.blockId, index, 0)
                }
            }
        }
    }
}
