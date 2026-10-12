import QtQuick
import QtQuick.Controls
import ".."

// Pole liczbowe z ułamkami (SpinBox operuje na liczbach całkowitych × scale).
SpinBox {
    id: field

    property real realValue: 0
    property real realFrom: 0
    property real realTo: 100
    property real realStep: 1
    property int decimals: 1
    property string suffix: ""
    readonly property int scale: Math.pow(10, decimals)
    signal edited(real value)

    from: Math.round(realFrom * scale)
    to: Math.round(realTo * scale)
    stepSize: Math.max(1, Math.round(realStep * scale))
    value: Math.round(realValue * scale)
    editable: true
    implicitWidth: 110
    implicitHeight: Theme.controlHeight
    font.pointSize: Theme.fontNormal

    validator: DoubleValidator {
        bottom: field.realFrom
        top: field.realTo
        decimals: field.decimals
        notation: DoubleValidator.StandardNotation
    }

    textFromValue: function(v, locale) {
        return Number(v / field.scale).toLocaleString(locale, 'f', field.decimals) + (field.suffix ? " " + field.suffix : "")
    }
    valueFromText: function(text, locale) {
        var clean = text.replace(field.suffix, "").trim()
        var n = Number.fromLocaleString(locale, clean)
        if (isNaN(n))
            n = parseFloat(clean.replace(",", "."))
        return Math.round((isNaN(n) ? field.realValue : n) * field.scale)
    }

    onValueModified: edited(value / scale)
}
