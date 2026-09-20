pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland

// One engine-wide controller, including replacement bars whose scoped shell API
// deliberately cannot retrieve a plugin's service. Lifetime follows widget users.
Item {
    id: root
    property int users: 0
    property var views: []
    property int openPanels: 0
    property var devices: []
    property string selectedPath: ""
    property string backend: ""
    property string version: ""
    property bool backendAvailable: false
    property string message: ""
    property string errorText: ""
    property string actionText: ""
    property bool actionFailed: false
    property bool refreshQueued: false
    property string operation: ""
    property var reply: null
    property bool inFlight: false
    readonly property bool busy: inFlight
    readonly property var device: devices.find(d => d.path === selectedPath) || devices[0] || null
    readonly property bool connected: device !== null
    readonly property bool controlsAvailable: connected && device.state.toggle1Visible === true && device.modes.length > 0
    readonly property int currentMode: controlsAvailable ? Number(device.state.toggle1State || 0) : 0
    readonly property string helper: Qt.resolvedUrl("../budsctl.py").toString().replace(/^file:\/\//, "")

    function attach(view) {
        if (views.indexOf(view) >= 0) return;
        views = views.concat([view]);
        users = views.length;
        if (users === 1) refresh();
    }
    function detach(view) {
        views = views.filter(v => v !== view);
        users = views.length;
        if (users === 0) { refreshQueued = false; worker.running = false; inFlight = false; debounce.stop(); }
    }
    function panelOpened() { openPanels++; refresh(); }
    function panelClosed() { openPanels = Math.max(0, openPanels - 1); }
    function focusedView() {
        const name = Hyprland.focusedMonitor ? Hyprland.focusedMonitor.name : "";
        return views.find(v => v && v.screenName === name) || views[0] || null;
    }
    function showView(toggle) {
        const view = focusedView();
        if (!view) return;
        for (const other of views) if (other && other !== view) other.close();
        if (toggle) view.toggle(); else view.open();
    }
    IpcHandler {
        target: "io.github.nerdislb.buds-control"
        enabled: root.users > 0
        function open(): void { root.showView(false); }
        function show(): void { root.showView(false); }
        function toggle(): void { root.showView(true); }
        function close(): void { for (const view of root.views) if (view) view.close(); }
        function hide(): void { for (const view of root.views) if (view) view.close(); }
        function refresh(): void { root.refresh(); }
        function status(): string {
            return JSON.stringify({instances: root.users, openPanels: root.openPanels,
                busy: root.busy, connected: root.connected, backend: root.backend, mode: root.currentMode});
        }
    }
    function modeLabel(value) {
        const option = device ? device.modes.find(m => Number(m.value) === Number(value)) : null;
        return option ? String(option.label) : (connected ? "Unknown mode" : "Disconnected");
    }
    function selectNext() {
        if (!busy && devices.length > 1) {
            selectedPath = devices[(devices.indexOf(device) + 1) % devices.length].path;
            actionText = "";
        }
    }
    function start(args, kind) {
        inFlight = true;
        operation = kind;
        reply = null;
        worker.command = ["python3", decodeURIComponent(helper)].concat(args);
        worker.running = true;
    }
    function refresh() {
        if (users < 1) return;
        if (inFlight) { refreshQueued = true; return; }
        refreshQueued = false;
        start(["status"], "status");
    }
    function setMode(value) {
        if (inFlight || !controlsAvailable || !device.modes.some(m => Number(m.value) === Number(value)) || Number(value) === currentMode) return;
        actionFailed = false;
        actionText = "Applying " + modeLabel(value) + "…";
        actionClear.stop();
        start(["mode", String(device.path), String(value)], "mode");
    }
    function parseReply(text) {
        try { reply = JSON.parse(text); }
        catch (e) { reply = {ok: false, error: "The headset backend returned unreadable data."}; }
    }
    function finish(code) {
        inFlight = false;
        const result = reply || {ok: false, error: "The headset backend stopped without a response."};
        const ok = code === 0 && result.ok === true;
        if (operation === "status") {
            devices = ok && Array.isArray(result.devices) ? result.devices.filter(d => d && typeof d.path === "string" && d.state && Array.isArray(d.modes)) : [];
            backendAvailable = result.available === true;
            backend = String(result.backend || "");
            version = String(result.version || "");
            message = String(result.message || "");
            errorText = ok ? "" : String(result.error || "Unable to read headset status.");
        } else {
            actionFailed = !ok;
            actionText = ok ? (result.confirmed === true ? "Noise control confirmed." : "Request sent; waiting for the headset to report its mode.") : String(result.error || "The mode could not be changed.");
            actionClear.restart();
            refreshQueued = true;
        }
        if (refreshQueued && users > 0) Qt.callLater(refresh);
    }
    Process {
        id: worker
        stdout: StdioCollector { waitForEnd: true; onStreamFinished: root.parseReply(text) }
        onExited: code => root.finish(code)
    }
    Timer {
        interval: 45000
        running: root.inFlight
        onTriggered: {
            root.reply = {ok: false, error: "The headset operation timed out. Refresh to retry."};
            worker.running = false;
        }
    }
    Timer {
        interval: root.openPanels > 0 || !root.connected ? 15000 : 60000
        running: root.users > 0
        repeat: true
        onTriggered: root.refresh()
    }
    Timer { id: actionClear; interval: 8000; onTriggered: root.actionText = "" }
    Timer { id: debounce; interval: 500; onTriggered: root.refresh() }
    Process {
        running: root.users > 0
        command: ["dbus-monitor", "--system", "type='signal',sender='org.bluez',interface='org.freedesktop.DBus.Properties',path_namespace='/org/bluez'"]
        stdout: SplitParser { onRead: data => { if (data.includes("Connected")) debounce.restart(); } }
    }
    Process {
        running: root.users > 0 && root.backend === "budslink"
        command: ["dbus-monitor", "--session", "type='signal',path_namespace='/io/github/maniacx/BudsLink'"]
        stdout: SplitParser { onRead: debounce.restart() }
    }
}
