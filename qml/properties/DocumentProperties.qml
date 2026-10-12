import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QmlWord.Backend
import ".."
import "../controls"

// Właściwości całego dokumentu: metadane, czcionka bazowa, strona, statystyki.
ColumnLayout {
    id: props

    property DocumentModel doc
    property OutlineModel outline
    signal pageSetupRequested()

    readonly property var meta: doc ? doc.meta : ({})
    readonly property var page: doc ? doc.page : ({})

    spacing: 10

    PropertyGroup {
        title: "Dokument"

        FieldLabel { text: "Tytuł (metadane, także w PDF)" }
        TextField {
            Layout.fillWidth: true
            text: props.meta.title || ""
            placeholderText: "Bez tytułu"
            selectByMouse: true
            onEditingFinished: if (text !== (props.meta.title || "")) props.doc.setMeta({ title: text })
        }
        FieldLabel { text: "Autor" }
        TextField {
            Layout.fillWidth: true
            text: props.meta.author || ""
            placeholderText: "Nie podano"
            selectByMouse: true
            onEditingFinished: if (text !== (props.meta.author || "")) props.doc.setMeta({ author: text })
        }
    }

    PropertyGroup {
        title: "Czcionka dokumentu"
        FieldLabel { text: "Krój tekstu i nagłówków" }
        ComboBox {
            Layout.fillWidth: true
            model: AppUtils.fontFamilies
            displayText: props.meta.fontFamily || ""
            onActivated: function(index) { props.doc.setMeta({ fontFamily: AppUtils.fontFamilies[index] }) }
        }
        RowLayout {
            FieldLabel { text: "Rozmiar tekstu podstawowego" }
            NumberField {
                realValue: props.meta.fontSize || 11
                realFrom: 6; realTo: 36; realStep: 0.5; decimals: 1; suffix: "pt"
                onEdited: function(v) { props.doc.setMeta({ fontSize: v }) }
            }
        }
    }

    PropertyGroup {
        title: "Strona"
        Text {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            font.pointSize: Theme.fontSmall
            color: Theme.textMuted
            text: (props.page.size || "A4") + ", " + (props.page.landscape ? "pozioma" : "pionowa")
                  + " · marginesy " + [props.page.marginTop, props.page.marginRight, props.page.marginBottom, props.page.marginLeft]
                     .map(function(v) { return Math.round(v) }).join(" / ") + " mm"
        }
        Button {
            text: "Ustawienia strony…"
            onClicked: props.pageSetupRequested()
        }
    }

    PropertyGroup {
        title: "Statystyki"
        Text {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            font.pointSize: Theme.fontSmall
            color: Theme.textMuted
            text: "Słowa: " + (props.doc ? props.doc.wordCount : 0)
                  + "\nBloki: " + (props.doc ? props.doc.blockCount : 0)
                  + "\nSekcje: " + (props.outline ? props.outline.totalCount : 0)
                  + (props.doc && props.doc.filePath ? "\nPlik: " + props.doc.filePath : "\nPlik: jeszcze nie zapisano")
                  + (props.meta.modified ? "\nOstatni zapis: " + props.meta.modified.replace("T", " ").substring(0, 16) : "")
        }
    }
}
