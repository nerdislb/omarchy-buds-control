#!/usr/bin/env python3
"""Test real QML singleton attach/detach with a mocked helper, without device I/O."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[1]
omarchy = Path(os.environ.get('OMARCHY_PATH', '/usr/share/omarchy'))
with tempfile.TemporaryDirectory(prefix='buds-qml-test-') as directory:
    root = Path(directory)
    for name in ('Commons', 'Ui'):
        (root/name).symlink_to(omarchy/'shell'/name)
    plugin = root/'Plugin'
    plugin.mkdir()
    shutil.copy2(repo/'BarWidget.qml', plugin/'BarWidget.qml')
    shutil.copytree(repo/'backend', plugin/'backend')
    (plugin/'budsctl.py').write_text('''import json,sys,time
time.sleep(0.15)
print(json.dumps({"ok":True,"available":True,"backend":"mock","devices":[]}))
''')
    # Use the preview's complete bar facade, but no windows or synthetic service.
    preview = (repo/'tests/Preview.qml').read_text()
    facade = preview[preview.index('    QtObject {\n        id: fakeBar'):preview.index('    PanelWindow {')]
    qml = '''import QtQuick
import Quickshell
import qs.Commons
import "Plugin" as Plugin
import "Plugin/backend" as Backend
ShellRoot {
    id: test
    property int phase: 0
    function check(condition, message) {
        if (!condition) { console.error("BUDS_SMOKE_FAIL", message); Qt.quit(); }
    }
''' + facade + '''
    Loader { id: first; sourceComponent: Component { Plugin.BarWidget { bar: fakeBar } } }
    Loader { id: second; sourceComponent: Component { Plugin.BarWidget { bar: fakeBar } } }
    Timer {
        running: true; repeat: true; interval: 700
        onTriggered: {
            const service = Backend.BudsService;
            if (test.phase === 0) {
                test.check(service.users === 2, "controller not shared");
                test.check(service.backend === "mock", "mock helper response not received");
                service.refresh(); service.refresh();
                test.check(service.busy && service.refreshQueued, "refresh not serialized");
            } else if (test.phase === 1) {
                test.check(!service.busy, "queued refresh did not settle");
                first.active = false;
            } else if (test.phase === 2) {
                test.check(service.users === 1, "first detach stopped shared controller");
                service.refresh();
                second.active = false;
            } else {
                test.check(service.users === 0 && !service.busy, "last detach did not stop worker");
                console.log("BUDS_SMOKE_OK: shared controller, serialization, last-user shutdown");
                Qt.quit();
            }
            test.phase++;
        }
    }
}
'''
    (root/'shell.qml').write_text(qml)
    result = subprocess.run(['quickshell', '-p', str(root), '--no-color'], capture_output=True, text=True, timeout=12)
    output = result.stdout + result.stderr
    print(output)
    if result.returncode or 'BUDS_SMOKE_OK' not in output or 'BUDS_SMOKE_FAIL' in output or 'TypeError' in output or 'ReferenceError' in output:
        raise SystemExit(1)
