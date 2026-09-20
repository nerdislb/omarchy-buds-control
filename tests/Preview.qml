// Synthetic UI fixture. Never accesses Bluetooth or the real controller.
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons
import "Plugin" as Plugin

ShellRoot {
    id: harness
    property var popup: null
    QtObject {
        id: fixture
        property int users: 0
        property int openPanels: 0
        property string state: "connected"
        property int currentMode: 3
        property bool connected: state !== "disconnected" && state !== "error"
        property bool controlsAvailable: connected
        property bool backendAvailable: state !== "error"
        property bool busy: state === "loading"
        property string backend: "pbpctrl"
        property string version: "0.1.8"
        property string errorText: state === "error" ? "The headset did not respond in time. Check the connection and refresh." : ""
        property string message: state === "disconnected" ? "Connect your Pixel Buds in Bluetooth, then refresh." : ""
        property string actionText: ""
        property bool actionFailed: false
        property var device: connected ? ({path: "pixel:00:11:22:33:44:55", alias: "Pixel Buds Pro 2 · Preview", modes: [
            {label: "Off", value: 1}, {label: "Transparency", value: 2}, {label: "Noise Cancellation", value: 3}],
            state: {toggle1Visible: true, toggle1State: currentMode, battery1Level: 82, battery1Status: "discharging",
                battery2Level: 76, battery2Status: "charging", battery3Level: 45, battery3Status: "discharging"}}) : null
        property var devices: device ? [device] : []
        function attach(view) { users++; }
        function detach(view) { users--; }
        function panelOpened() { openPanels++; }
        function panelClosed() { openPanels--; }
        function refresh() {}
        function selectNext() {}
        function setMode(mode) { currentMode = Number(mode); actionText = "Preview only — no device was changed."; }
        function modeLabel(mode) { return ["Unknown", "Off", "Transparency", "Noise Cancellation"][mode]; }
    }
    QtObject {
        id: fakeBar
        property color foreground: Color.foreground
        property color barForeground: Color.foreground
        property color background: Color.background
        property color urgent: Color.urgent
        property string fontFamily: Style.font.family
        property int barSize: Style.bar.sizeHorizontal
        property bool vertical: false
        property bool foregroundAnimationEnabled: false
        property string position: "top"
        property var activePopout: null
        property var clickTargets: []
        function hideTooltip(item) {}
        function showTooltip(item, text) {}
        function registerClickTarget(item) {}
        function unregisterClickTarget(item) {}
        function requestPopout(item) { activePopout = item; }
        function releasePopout(item) { activePopout = null; }
    }
    PanelWindow {
        id: anchor
        screen: Quickshell.screens.find(s => s.name === Quickshell.env("BUDS_PREVIEW_SCREEN")) || Quickshell.screens[0]
        anchors { top: true; left: true; right: true }
        implicitHeight: Style.bar.sizeHorizontal
        color: "transparent"
        exclusionMode: ExclusionMode.Ignore
        WlrLayershell.namespace: "buds-control-preview"
        Plugin.BarWidget { id: widget; x: parent.width / 2; bar: fakeBar; buds: fixture }
    }
    Timer {
        interval: 400
        running: true
        onTriggered: {
            for (const item of widget.data)
                if (item && item.cardOrigin !== undefined) harness.popup = item;
            if (Quickshell.env("BUDS_PREVIEW_COLORS")) {
                Color.loadColors(Quickshell.env("BUDS_PREVIEW_COLORS"));
                Color.shellValues = ({});
            }
            widget.open();
        }
    }
    IpcHandler {
        target: "buds-preview"
        function state(value: string): void { fixture.state = value; }
        function size(width: int, height: int): void { harness.popup.contentWidth = width; harness.popup.contentHeight = height; }
        function open(): void { widget.open(); }
        function status(): string {
            return JSON.stringify({mode: fixture.currentMode, cursor: widget.cursor, open: widget.opened,
                x: anchor.screen.x + harness.popup.cardOrigin.x, y: anchor.screen.y + harness.popup.cardOrigin.y,
                width: harness.popup.contentWidth, height: harness.popup.contentHeight});
        }
        function quit(): void { Qt.quit(); }
    }
}
