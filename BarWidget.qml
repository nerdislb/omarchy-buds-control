import QtQuick
import QtQuick.Controls as Controls
import Quickshell
import qs.Commons
import qs.Commons as Commons
import qs.Ui as Ui
import "backend" as Backend

// Reference: Omarchy 4.0.4 audio/Bluetooth Panel + KeyboardPanel composition.
Ui.Panel {
    id: root
    moduleName: "io.github.nerdislb.buds-control"
    ipcTarget: "io.github.nerdislb.buds-control"
    manageIpc: false
    readonly property string screenName: root.QsWindow.window && root.QsWindow.window.screen ? root.QsWindow.window.screen.name : ""
    property var buds: Backend.BudsService
    property int cursor: -1
    readonly property var device: buds.device
    readonly property var modes: device && buds.controlsAvailable ? device.modes : []
    readonly property var batteries: [battery(1, "Left bud"), battery(2, "Right bud"), battery(3, "Case")]
    readonly property color foreground: bar ? bar.foreground : Commons.Color.foreground
    readonly property string family: bar ? bar.fontFamily : Style.font.family
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight

    function battery(index, label) {
        const state = device ? device.state : {};
        const status = String(state["battery" + index + "Status"] || "not-reported");
        const level = Number(state["battery" + index + "Level"]);
        return {label: label, level: level, status: status,
            available: Number.isFinite(level) && level >= 0 && level <= 100 && status !== "not-reported" && status !== "disconnected"};
    }
    function batteryDetail(b) {
        if (!b.available) return "Not reported";
        if (b.status === "charging") return "Charging";
        if (b.status === "full") return "Full";
        if (b.status === "discharging") return "In use";
        return "Reported";
    }
    function shortMode(label) { return label === "Noise Cancellation" ? "ANC" : String(label).slice(0, 20); }
    function targets() {
        let result = [];
        for (let i = 0; i < modeRepeater.count; i++) {
            const item = modeRepeater.itemAt(i);
            if (item && item.visible && item.enabled) result.push(item);
        }
        for (const item of [refreshButton, bluetoothButton, nextButton, settingsButton, setupButton])
            if (item.visible && item.enabled) result.push(item);
        return result;
    }
    function isCursor(item) { return targets()[cursor] === item; }
    function hover(item) { cursor = targets().indexOf(item); }
    function move(delta) {
        const list = targets();
        if (!list.length) return;
        cursor = cursor < 0 ? (delta > 0 ? 0 : list.length - 1) : (cursor + delta + list.length) % list.length;
        const target = list[cursor];
        const y = target.mapToItem(body, 0, 0).y;
        if (y < scroller.contentY) scroller.contentY = y;
        else if (y + target.height > scroller.contentY + scroller.height)
            scroller.contentY = Math.min(y + target.height - scroller.height, Math.max(0, scroller.contentHeight - scroller.height));
    }
    function activate() {
        const item = targets()[cursor];
        if (item && item.enabled) item.clicked();
    }
    function openBluetooth() {
        close();
        Quickshell.execDetached(["omarchy-shell", "omarchy.bluetooth", "open"]);
    }
    function openSettings() {
        Quickshell.execDetached(["sh", "-c", "if command -v budslink >/dev/null 2>&1; then exec budslink; else exec flatpak run io.github.maniacx.BudsLink; fi"]);
    }
    Component.onCompleted: buds.attach(root)
    Component.onDestruction: {
        if (opened) buds.panelClosed();
        buds.detach(root);
    }
    onOpenedChanged: {
        cursor = -1;
        if (opened) buds.panelOpened();
        else buds.panelClosed();
    }

    Ui.BarIconButton {
        id: button
        anchors.fill: parent
        bar: root.bar
        text: "󰋋"
        dimmed: !root.buds.connected
        tooltipText: root.device ? String(root.device.alias) + " · " + root.buds.modeLabel(root.buds.currentMode) : "Buds Control · Disconnected"
        Accessible.role: Accessible.Button
        Accessible.name: tooltipText
        Accessible.onPressAction: root.toggle()
        onPressed: b => { if (b === Qt.RightButton && root.buds.backend === "budslink") root.openSettings(); else root.toggle(); }
    }

    Ui.KeyboardPanel {
        id: panel
        anchorItem: button
        owner: root
        bar: root.bar
        open: root.opened
        focusTarget: keyCatcher
        contentWidth: fittedContentWidth(Style.space(360))
        contentHeight: fittedContentHeight(body.implicitHeight, Style.space(540))

        Ui.PanelKeyCatcher {
            id: keyCatcher
            anchors.fill: parent
            onCloseRequested: root.close()
            onMoveRequested: (dx, dy) => root.move(dy !== 0 ? dy : dx)
            onTabRequested: direction => root.move(direction)
            onActivateRequested: root.activate()
            onTextKey: t => { if (t === "r" || t === "R") root.buds.refresh(); }

            Flickable {
                id: scroller
                anchors.fill: parent
                contentWidth: width
                contentHeight: body.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                interactive: contentHeight > height
                Controls.ScrollBar.vertical: Controls.ScrollBar { policy: Controls.ScrollBar.AsNeeded }

                Column {
                    id: body
                    width: scroller.width
                    spacing: Style.space(14)
                    Ui.PanelHero {
                        title: root.device ? String(root.device.alias) : "Buds Control"
                        meta: root.buds.busy ? "Refreshing…" : (root.buds.connected ? root.buds.modeLabel(root.buds.currentMode) : "Disconnected")
                        foreground: root.foreground
                        fontFamily: root.family
                        iconComponent: Component {
                            Text {
                                text: "󰋋"
                                textFormat: Text.PlainText
                                font.family: root.family
                                font.pixelSize: Style.font.display
                                color: root.foreground
                            }
                        }
                    }
                    Ui.PanelSeparator { foreground: root.foreground }
                    Column {
                        width: parent.width
                        visible: root.buds.connected
                        spacing: Style.space(10)
                        Ui.PanelSectionHeader { text: "BATTERY"; foreground: root.foreground; fontFamily: root.family }
                        Row {
                            width: parent.width
                            spacing: Style.space(10)
                            Repeater {
                                model: root.batteries
                                Column {
                                    id: batteryColumn
                                    required property var modelData
                                    width: (parent.width - Style.space(20)) / 3
                                    spacing: Style.space(4)
                                    Accessible.role: Accessible.StaticText
                                    Accessible.name: modelData.label + ": " + (modelData.available ? Math.round(modelData.level) + " percent, " + root.batteryDetail(modelData) : "Not reported")
                                    Text {
                                        width: parent.width
                                        text: batteryColumn.modelData.label
                                        textFormat: Text.PlainText
                                        font.family: root.family
                                        font.pixelSize: Style.font.bodySmall
                                        color: root.foreground
                                        elide: Text.ElideRight
                                    }
                                    Text {
                                        width: parent.width
                                        text: batteryColumn.modelData.available ? Math.round(batteryColumn.modelData.level) + "%" : "—"
                                        textFormat: Text.PlainText
                                        font.family: root.family
                                        font.pixelSize: Style.font.title
                                        font.bold: true
                                        color: batteryColumn.modelData.available && batteryColumn.modelData.level <= 20 ? Commons.Color.urgent : root.foreground
                                    }
                                    Caption { text: root.batteryDetail(batteryColumn.modelData); width: parent.width }
                                }
                            }
                        }
                        Caption {
                            width: parent.width
                            text: "Case charge is reported only when the earbuds relay it."
                        }
                    }
                    Ui.PanelSeparator { visible: root.buds.connected; foreground: root.foreground }
                    Column {
                        width: parent.width
                        visible: root.modes.length > 0
                        spacing: Style.space(10)
                        Ui.PanelSectionHeader { text: "NOISE CONTROL"; foreground: root.foreground; fontFamily: root.family }
                        Flow {
                            id: modeFlow
                            width: parent.width
                            spacing: Style.spacing.md
                            Repeater {
                                id: modeRepeater
                                model: root.modes
                                Ui.Button {
                                    id: modeButton
                                    required property var modelData
                                    text: root.shortMode(String(modelData.label))
                                    tooltipText: String(modelData.label)
                                    selected: Number(modelData.value) === root.buds.currentMode
                                    enabled: !root.buds.busy
                                    opacity: enabled ? 1 : 0.55
                                    bordered: true
                                    foreground: root.foreground
                                    fontFamily: root.family
                                    hasCursor: root.isCursor(modeButton)
                                    Accessible.role: Accessible.RadioButton
                                    Accessible.name: String(modelData.label)
                                    Accessible.checked: selected
                                    Accessible.onPressAction: { if (enabled) root.buds.setMode(modelData.value); }
                                    onHovered: h => { if (h) root.hover(modeButton); }
                                    onClicked: root.buds.setMode(modelData.value)
                                }
                            }
                        }
                    }
                    Caption {
                        visible: root.buds.connected && !root.buds.controlsAvailable
                        text: "This headset does not expose noise-control modes."
                        width: parent.width
                    }
                    Caption {
                        visible: root.buds.actionText !== ""
                        text: root.buds.actionText
                        color: root.buds.actionFailed ? Commons.Color.urgent : root.foreground
                        opacity: 1
                        width: parent.width
                    }
                    Caption {
                        visible: root.buds.message !== "" && !root.buds.connected
                        text: root.buds.message
                        width: parent.width
                    }
                    Caption {
                        visible: root.buds.errorText !== ""
                        text: root.buds.errorText
                        color: Commons.Color.urgent
                        opacity: 1
                        width: parent.width
                    }
                    Ui.PanelSeparator { foreground: root.foreground }
                    Flow {
                        width: parent.width
                        spacing: Style.spacing.md
                        Action {
                            id: refreshButton
                            text: root.buds.busy ? "Refreshing…" : "Refresh"
                            enabled: !root.buds.busy
                            onClicked: root.buds.refresh()
                        }
                        Action { id: bluetoothButton; text: "Bluetooth"; onClicked: root.openBluetooth() }
                        Action {
                            id: nextButton
                            text: "Next headset"
                            visible: root.buds.devices.length > 1
                            enabled: !root.buds.busy
                            onClicked: root.buds.selectNext()
                        }
                        Action {
                            id: settingsButton
                            text: "Full settings"
                            visible: root.buds.backend === "budslink"
                            onClicked: root.openSettings()
                        }
                        Action {
                            id: setupButton
                            text: "Get pbpctrl"
                            visible: !root.buds.backendAvailable
                            onClicked: Quickshell.execDetached(["xdg-open", "https://github.com/qzed/pbpctrl#installation"])
                        }
                    }
                    Caption {
                        width: parent.width
                        text: (root.buds.backend || "No backend") + (root.buds.version ? " " + root.buds.version : "") + " · R to refresh · Esc to close"
                    }
                }
            }
        }
    }
    component Caption: Text {
        textFormat: Text.PlainText
        font.family: root.family
        font.pixelSize: Style.font.caption
        color: root.foreground
        opacity: 0.75
        wrapMode: Text.Wrap
    }
    component Action: Ui.Button {
        id: action
        bordered: true
        foreground: root.foreground
        fontFamily: root.family
        hasCursor: root.isCursor(action)
        opacity: enabled ? 1 : 0.55
        Accessible.role: Accessible.Button
        Accessible.name: text
        Accessible.onPressAction: { if (enabled) clicked(); }
        onHovered: h => { if (h) root.hover(action); }
    }
}
