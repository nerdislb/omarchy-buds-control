"""Protocol/guard regression tests; no Bluetooth hardware or network access."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import budsctl as b

ADDRESS = "00:11:22:33:44:55"
PATH = "pixel:" + ADDRESS
BL_PATH = "/io/github/maniacx/BudsLink/Devices/pixel/test"
HELP = "VALUE [possible values: off, active, aware]"
BATTERY = "case: unknown\nleft bud: 77% (not charging)\nright bud: 0% (charging)"


class BackendTests(unittest.TestCase):
    @patch.object(b, "run_text", return_value="")
    def test_void_dbus_methods_are_successful(self, run):
        self.assertEqual(b.busctl("call", "test", "/test", "test", "Void"), {})

    def test_budslink_read_through_raw_busctl_replies(self):
        def response(command, **kwargs):
            if "NameHasOwner" in command: return json.dumps({"data": [True]})
            if "HoldService" in command or "ReleaseService" in command: return ""
            if "ServiceVersion" in command: return json.dumps({"data": ["1.0"]})
            if "ListDevices" in command: return json.dumps({"data": [[BL_PATH]]})
            if command[-1] == "Config": return json.dumps({"data": json.dumps({"toggle1Button1Name": "Off"})})
            if command[-1] == "State": return json.dumps({"data": json.dumps({"toggle1Visible": True, "toggle1State": 1})})
            if command[-1] == "Alias": return json.dumps({"data": "Test earbuds"})
            self.fail(str(command))
        with patch.object(b, "run_text", side_effect=response):
            result = b.read_budslink_status()
        self.assertEqual(result["devices"][0]["alias"], "Test earbuds")
        self.assertEqual(result["devices"][0]["modes"], [{"label": "Off", "value": 1}])

    def test_real_pbpctrl_battery_format(self):
        values = b.parse_pbp_battery(BATTERY)
        self.assertEqual(values["battery1"], (77, "discharging"))
        self.assertEqual(values["battery2"], (0, "charging"))
        self.assertEqual(values["battery3"], (0, "not-reported"))

    def test_bad_and_missing_batteries_not_fabricated(self):
        self.assertEqual(b.parse_pbp_battery("left bud: 101% (charging)\nright bud: -1% (charging)\ngarbage"), {})

    def test_charge_unknown_is_not_assumed_discharging(self):
        self.assertEqual(b.parse_pbp_battery("left bud: 50% (unknown)")["battery1"], (50, "unknown"))

    @patch.object(b, "run_text", return_value=HELP)
    def test_stable_modes_no_adaptive(self, run):
        self.assertEqual([m["value"] for m in b.pbp_mode_options()], [1, 2, 3])

    @patch.object(b, "run_text", return_value=HELP.replace("aware]", "aware, adaptive]"))
    def test_adaptive_only_if_cli_exposes_it(self, run):
        self.assertEqual([m["value"] for m in b.pbp_mode_options()], [1, 2, 3, 4])

    @patch.object(b, "run_text", return_value="unexpected help")
    def test_incompatible_cli_fails_closed(self, run):
        with self.assertRaises(RuntimeError): b.pbp_mode_options()

    @patch.object(b, "run_text", return_value=f"Device {ADDRESS} Pixel Buds Pro 2")
    def test_bare_device_name_detected(self, run):
        self.assertEqual(b.connected_pixel_buds(), (ADDRESS, "Pixel Buds Pro 2"))

    @patch.object(b, "run_text", side_effect=[f"Device {ADDRESS.lower()} My headphones", "Name: Pixel Buds Pro 2\nAlias: My headphones"])
    def test_renamed_device_detected_by_name(self, run):
        self.assertEqual(b.connected_pixel_buds(), (ADDRESS, "My headphones"))

    @patch.object(b, "run_text", side_effect=[f"Device {ADDRESS} Speaker", "Name: Speaker"])
    def test_unrelated_headset_not_touched(self, run):
        self.assertIsNone(b.connected_pixel_buds())

    @patch.object(b, "budslink_has_owner", return_value=False)
    @patch.object(b, "connected_pixel_buds", return_value=None)
    @patch.object(b.shutil, "which", return_value="/usr/bin/pbpctrl")
    def test_disconnected_is_normal_state(self, *_):
        state = b.read_status()
        self.assertTrue(state["ok"])
        self.assertTrue(state["available"])
        self.assertEqual(state["devices"], [])

    @patch.object(b, "budslink_has_owner", return_value=False)
    @patch.object(b, "connected_pixel_buds", return_value=(ADDRESS, "Pixel Buds Pro"))
    @patch.object(b.shutil, "which", return_value=None)
    def test_missing_backend_reported(self, *_):
        self.assertFalse(b.read_status()["available"])

    @patch.object(b, "budslink_has_owner", return_value=True)
    @patch.object(b, "read_budslink_status", return_value={"devices": []})
    @patch.object(b, "connected_pixel_buds")
    def test_running_budslink_has_exclusive_precedence(self, pixel, *_):
        self.assertIn("Close BudsLink", b.read_status()["message"])
        pixel.assert_not_called()

    @patch.object(b, "run_text", side_effect=[HELP, "aware", "case: 5% (not charging)\nleft bud: 77% (not charging)\nright bud: 80% (charging)", "pbpctrl 0.1.8"])
    def test_summary_uses_buds_not_case(self, run):
        state = b.read_pbp_status(ADDRESS, "Test")["devices"][0]["state"]
        self.assertEqual(state["computedBatteryLevel"], 77)
        self.assertEqual(state["toggle1State"], 2)

    @patch.object(b, "run_text", side_effect=[HELP, "new-mode", BATTERY, "pbpctrl 0.1.8"])
    def test_unknown_mode_keeps_batteries(self, run):
        self.assertEqual(b.read_pbp_status(ADDRESS, "Test")["devices"][0]["state"]["toggle1State"], 0)

    def test_invalid_targets_rejected_without_commands(self):
        with patch.object(b, "run_text") as run:
            for path in ["pixel:$(touch /tmp/nope)", "pixel:00:11", "/bad", "../test"]:
                with self.assertRaises(ValueError): b.set_mode(path, 2)
            run.assert_not_called()

    @patch.object(b, "budslink_has_owner", return_value=True)
    @patch.object(b, "run_text")
    def test_action_does_not_terminate_competing_backend(self, run, owner):
        with self.assertRaises(RuntimeError): b.set_pbp_mode(PATH, 2)
        run.assert_not_called()

    @patch.object(b, "budslink_has_owner", return_value=False)
    @patch.object(b, "connected_pixel_buds", return_value=None)
    @patch.object(b, "run_text")
    def test_stale_device_action_rejected(self, run, *_):
        with self.assertRaises(RuntimeError): b.set_pbp_mode(PATH, 2)
        run.assert_not_called()

    def action(self, actual, value=2):
        with patch.object(b, "budslink_has_owner", return_value=False), \
             patch.object(b, "connected_pixel_buds", return_value=(ADDRESS, "Test")), \
             patch.object(b, "run_text", side_effect=[HELP, "", actual]) as run:
            result = b.set_pbp_mode(PATH, value)
            self.assertEqual(run.call_args_list[-1].args[0], ["pbpctrl", "-d", ADDRESS, "get", "anc"])
            return result

    def test_write_requires_readback(self):
        self.assertTrue(self.action("aware")["confirmed"])

    def test_readback_mismatch_is_failure(self):
        with self.assertRaises(RuntimeError): self.action("active")

    def test_unsupported_mode_is_not_sent(self):
        with self.assertRaises(ValueError): self.action("adaptive", value=4)

    @patch.object(b, "budslink_has_owner", return_value=True)
    @patch.object(b, "call")
    def test_hold_released_even_on_failure(self, call, owner):
        with self.assertRaises(ValueError):
            with b.held_budslink(): raise ValueError("bad response")
        self.assertEqual([x.args[0] for x in call.call_args_list], ["HoldService", "ReleaseService"])

    @patch.object(b, "budslink_has_owner", return_value=False)
    @patch.object(b, "call")
    def test_budslink_never_autostarts(self, call, owner):
        with self.assertRaises(RuntimeError):
            with b.held_budslink(): pass
        call.assert_not_called()

    def test_invalid_dbus_json_rejected(self):
        for value in ["null", "[]", "42", "not-json"]:
            with self.assertRaises(ValueError): b.json_object(value)

    @patch.object(b, "read_status", side_effect=RuntimeError("Connection failed"))
    @patch.object(b.shutil, "which", return_value="/usr/bin/pbpctrl")
    def test_temporary_error_does_not_report_missing_package(self, *_):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, XDG_RUNTIME_DIR=temp), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(b.main(["status"]), 1)
        self.assertTrue(json.loads(out.getvalue())["available"])

    def test_lock_blocks_parallel_protocol_operations(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, XDG_RUNTIME_DIR=temp):
            with b.device_lock():
                with self.assertRaises(BlockingIOError):
                    with b.device_lock(): pass
            with b.device_lock(): pass

    def test_lock_does_not_follow_symlink(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, XDG_RUNTIME_DIR=temp):
            victim = Path(temp)/"victim"
            victim.write_text("keep")
            (Path(temp)/"omarchy-buds-control.lock").symlink_to(victim)
            with self.assertRaises(OSError):
                with b.device_lock(): pass
            self.assertEqual(victim.read_text(), "keep")

    @patch.object(b, "read_status", side_effect=subprocess.CalledProcessError(1, ["pbpctrl"], stderr="private protocol dump"))
    def test_cli_error_is_valid_json_without_backend_dump(self, read):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, XDG_RUNTIME_DIR=temp), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(b.main(["status"]), 1)
        result = json.loads(out.getvalue())
        self.assertFalse(result["ok"])
        self.assertNotIn("private protocol", result["error"])


if __name__ == "__main__": unittest.main()
